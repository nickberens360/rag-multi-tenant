import logging
import os
from contextlib import contextmanager
from typing import Generator, Optional

from fastapi import Request
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

logger = logging.getLogger(__name__)

# Create engine lazily to handle missing database gracefully
_engine = None
_SessionLocal = None


def get_engine():
    """Get or create the database engine."""
    global _engine, _SessionLocal

    if _engine is None:
        # Check if multi-tenant is enabled
        if os.getenv("ENABLE_MULTI_TENANT", "false").lower() != "true":
            # Multi-tenant disabled, return None
            logger.info("Multi-tenant disabled, skipping database engine creation")
            return None, None

        try:
            DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/db")
            _engine = create_engine(
                DATABASE_URL,
                pool_pre_ping=True,
                pool_size=10,
                max_overflow=20,
                echo=bool(os.getenv("SQL_ECHO", "false").lower() == "true"),
                # Add connect timeout to fail fast
                connect_args={"connect_timeout": 5},
            )
            # Test the connection
            with _engine.connect() as conn:
                conn.execute(text("SELECT 1"))

            _SessionLocal = sessionmaker(bind=_engine, autocommit=False, autoflush=False, expire_on_commit=False)
            logger.info("Database engine created successfully")
        except Exception as e:
            logger.warning(f"Failed to create database engine: {e}")
            _engine = None
            _SessionLocal = None

    return _engine, _SessionLocal


def get_db_session(request: Request) -> Generator[Optional[Session], None, None]:
    """FastAPI dependency for request-scoped session with tenant context."""
    engine, SessionLocal = get_engine()

    if SessionLocal is None:
        # No database available, yield None
        yield None
        return

    session = SessionLocal()
    try:
        # Always set tenant context so queries using current_setting('app.tenant_id') work reliably
        tenant_id = getattr(request.state, "tenant_id", None)
        if not tenant_id:
            # Treat empty env as unset and fall back to a stable default UUID
            tenant_id = os.getenv("DEFAULT_TENANT_ID") or "00000000-0000-0000-0000-000000000001"
        # Set at session level for robustness across statements in this session
        session.execute(text("SET app.tenant_id = :tid"), {"tid": str(tenant_id)})
        # Also set LOCAL for the current transaction scope explicitly
        session.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": str(tenant_id)})

        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        # Reset to avoid leaking to pooled connections
        try:
            session.execute(text("RESET app.tenant_id"))
        except Exception:
            pass
        session.close()


@contextmanager
def get_db_session_sync():
    """Context manager for sync operations."""
    engine, SessionLocal = get_engine()

    if SessionLocal is None:
        # No database available, yield None
        yield None
        return

    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
