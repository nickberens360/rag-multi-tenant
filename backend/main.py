"""
FastAPI application entry point.

This is the main entry point for the FastAPI application that:
- Initializes application state
- Creates the configured FastAPI app
- Sets up global state for routes
"""

import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from fastapi import FastAPI
from langchain_core.language_models import BaseLanguageModel

# Disable ChromaDB telemetry early to avoid noisy PostHog errors in some environments
# Set several known flags to be safe across versions
os.environ.setdefault("CHROMADB_TELEMETRY", "false")
os.environ.setdefault("CHROMA_TELEMETRY", "false")
os.environ.setdefault("ANONYMIZED_TELEMETRY", "false")
os.environ.setdefault("POSTHOG_DISABLED", "1")

from .core.app_factory import create_app
from .core.app_initializer_v2 import initialize_app_state
from .core.config_v2 import AppConfig
from .core.followup_service import FollowUpService
from .core.query_logger import get_query_logger
from .core.query_router import QueryRouter
from .core.response_cache_warmer import start_cache_warming
from .core.response_service import ResponseService
from .core.settings_manager import get_settings_manager
from .core.smart_illustration_service import SmartIllustrationService

project_root = Path(__file__).resolve().parent.parent

load_dotenv(project_root / ".env")


# Configure logging to send DEBUG/INFO to stdout and WARNING+ to stderr.
# This prevents platforms like Railway from labeling INFO logs as errors.
def _configure_logging(level_name: str = "INFO") -> None:
    level = getattr(logging, level_name, logging.INFO)

    root = logging.getLogger()
    # Clear existing handlers installed by basicConfig/uvicorn
    root.handlers.clear()
    root.setLevel(level)

    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    class _MaxLevelFilter(logging.Filter):
        def __init__(self, max_level: int) -> None:
            super().__init__()
            self.max_level = max_level

        def filter(self, record: logging.LogRecord) -> bool:  # type: ignore[override]
            return record.levelno <= self.max_level

    # Send DEBUG/INFO (and lower) to stdout
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(logging.DEBUG)
    stdout_handler.addFilter(_MaxLevelFilter(logging.INFO))
    stdout_handler.setFormatter(formatter)

    # Send WARNING/ERROR/CRITICAL to stderr
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(logging.WARNING)
    stderr_handler.setFormatter(formatter)

    root.addHandler(stdout_handler)
    root.addHandler(stderr_handler)

    # Harmonize common third-party loggers with the root configuration (best-effort)
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        try:
            lg = logging.getLogger(name)
            lg.setLevel(level)
            lg.propagate = True  # let messages flow to root handlers
            # Avoid duplicate emission if uvicorn preconfigured handlers
            lg.handlers.clear()
        except Exception:
            # Never fail startup on logging adjustments
            pass


_configure_logging(AppConfig.LOG_LEVEL)
logger = logging.getLogger(__name__)
# Initialize application state
retrievers: Optional[Dict[str, Any]] = None
illustration_service: Optional[SmartIllustrationService] = None
llm: Optional[BaseLanguageModel] = None

# Allow tests/CI to skip heavy app initialization (LLMs, embeddings, indexing)
if os.getenv("SKIP_APP_INIT", "false").lower() in {"1", "true", "yes"}:
    logger.info("⏭️  SKIP_APP_INIT=true — skipping heavy application initialization")
    app_initialized = False
else:
    try:
        retrievers, illustration_service, llm = initialize_app_state()
        app_initialized = True
    except Exception as e:
        logger.critical(f"❌ Application startup failed: {e}", exc_info=True)
        retrievers = None
        illustration_service = None
        llm = None
        app_initialized = False

query_router = QueryRouter()
response_service = ResponseService()

followup_service = FollowUpService()

query_logger = get_query_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    logger = logging.getLogger(__name__)

    # Startup: Store state in app.state for dependency injection
    try:
        logger.info("🚀 Starting application initialization...")
        app.state.app_initialized = app_initialized
        app.state.retrievers = retrievers
        app.state.illustration_service = illustration_service
        app.state.llm = llm
        app.state.query_router = query_router
        app.state.response_service = response_service
        app.state.followup_service = followup_service
        app.state.query_logger = query_logger

        # Add unified retriever to app state for knowledge route
        if retrievers and "_unified_retriever" in retrievers:
            app.state.unified_retriever = retrievers["_unified_retriever"]
        else:
            app.state.unified_retriever = None

        # Start cache warming in the background (non-blocking)
        if app_initialized and retrievers:
            await start_cache_warming(retrievers, app.state)

        # Optional: start periodic knowledge validation/sync
        # Read background sync config from DB settings with env fallback
        try:
            kset = get_settings_manager().get_knowledge_settings()
            interval = int(getattr(kset, "background_sync_interval_seconds", 0))
            auto_reconcile = bool(getattr(kset, "auto_reindex_deltas", False))
        except Exception:
            try:
                interval = int(os.getenv("KNOWLEDGE_SYNC_INTERVAL_SECONDS", "0"))
            except Exception:
                interval = 0
            auto_reconcile = os.getenv("KNOWLEDGE_SYNC_AUTO_RECONCILE", "false").lower() in {"1", "true", "yes"}

        if interval > 0 and getattr(app.state, "unified_retriever", None) is not None:
            from .core.knowledge_state_sync import KnowledgeStateSync

            retr = app.state.unified_retriever
            try:
                persist_dir = getattr(
                    getattr(retr, "semantic_searcher", None), "persist_dir", "backend/.unified_chroma"
                )
            except Exception:
                persist_dir = "backend/.unified_chroma"
            index_dirs = AppConfig.get_rag_index_dirs() or ["backend/knowledge", "public"]

            async def _periodic_sync():
                sync = KnowledgeStateSync(retr, persist_dir=persist_dir, index_dirs=index_dirs)
                while True:
                    try:
                        if auto_reconcile:
                            res = sync.reconcile(dry_run=False, allow_deletes=False, limit=50)
                            logger.info(
                                "Knowledge sync ran: reindexed=%d, deleted=%d, errors=%d",
                                len(res.get("actions", {}).get("reindexed", [])),
                                len(res.get("actions", {}).get("deleted_orphans", [])),
                                len(res.get("actions", {}).get("errors", [])),
                            )
                        else:
                            summ, _ = sync.validate()
                            logger.debug(
                                "Knowledge validate: fs=%d vec=%d missing=%d changed=%d orphans=%d",
                                summ.filesystem_files,
                                summ.vector_docs,
                                summ.discovered_not_indexed,
                                summ.changed_files,
                                summ.vector_orphans,
                            )
                    except Exception as e:
                        logger.debug(f"Periodic knowledge sync error: {e}")
                    await asyncio.sleep(interval)

            app.state.knowledge_sync_task = asyncio.create_task(_periodic_sync())
            logger.info(
                "Started periodic knowledge %s every %ss",
                "reconcile" if auto_reconcile else "validate",
                interval,
            )

        logger.info("✅ Application startup completed successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize application: {e}")
        raise

    yield

    # Shutdown: Clean shutdown
    try:
        task = getattr(app.state, "knowledge_sync_task", None)
        if task:
            task.cancel()
    except Exception:
        pass
    logger.info("✅ Application shutdown completed successfully")


# Create the FastAPI app with lifespan context manager
app = create_app(lifespan=lifespan)

# Ensure app.state has expected attributes for tests that patch them
# These are set definitively during lifespan startup, but we predefine them here
# so patch.object(app.state, ...) works even before startup runs.
if not hasattr(app.state, "retrievers"):
    app.state.retrievers = None  # type: ignore[attr-defined]
if not hasattr(app.state, "illustration_service"):
    app.state.illustration_service = None  # type: ignore[attr-defined]
if not hasattr(app.state, "response_service"):
    app.state.response_service = None  # type: ignore[attr-defined]
if not hasattr(app.state, "followup_service"):
    app.state.followup_service = None  # type: ignore[attr-defined]
if not hasattr(app.state, "llm"):
    app.state.llm = None  # type: ignore[attr-defined]
if not hasattr(app.state, "query_router"):
    app.state.query_router = None  # type: ignore[attr-defined]
if not hasattr(app.state, "unified_retriever"):
    app.state.unified_retriever = None  # type: ignore[attr-defined]
