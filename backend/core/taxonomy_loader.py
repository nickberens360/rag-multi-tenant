"""
⚠️⚠️⚠️ FULLY DEPRECATED - DO NOT USE ⚠️⚠️⚠️

This module has been COMPLETELY REMOVED as of Phase 4 (Cleanup & Consolidation) on 2025-10-05.
All functions in this module will raise DeprecationWarning.

REPLACEMENT:
- OLD: from .taxonomy_loader import get_topic_taxonomy
- NEW: from .content_router import get_tenant_taxonomy

WHY THIS WAS REMOVED:
1. Dual taxonomy systems created confusion (file + DB)
2. No tenant isolation (global taxonomy shared across all tenants)
3. Legacy code path prevented full migration to unified system

MIGRATION GUIDE:
See: docs/multi_tenant/taxonomy-refactor/04-phase4-cleanup.md

If you see this module being imported anywhere, it's a BUG that should be fixed immediately.
This file exists only to throw helpful errors and will be deleted in the next release.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_CACHED_TAXONOMY: Optional[Dict[str, Any]] = None
_TAXONOMY_PATH = Path(__file__).parent / "topic_taxonomy.json"
_CACHE_SOURCE: str = "file"

from .settings_manager import get_settings_manager


def invalidate_cache() -> None:
    """Invalidate cached taxonomy so next call will reload from source."""
    global _CACHED_TAXONOMY
    global _CACHE_SOURCE
    _CACHED_TAXONOMY = None
    _CACHE_SOURCE = "file"


def get_topic_taxonomy(force_reload: bool = False) -> Optional[Dict[str, Any]]:
    """
    ⚠️ DEPRECATED: This function has been removed. Use content_router.get_tenant_taxonomy() instead.

    This function will raise DeprecationWarning to help identify legacy code paths.
    """
    logger.error(
        "⚠️ DEPRECATED FUNCTION CALLED: taxonomy_loader.get_topic_taxonomy() ⚠️\n"
        "This function has been removed as of Phase 4 (2025-10-05).\n"
        "REPLACE WITH: from backend.core.content_router import get_tenant_taxonomy\n"
        "See migration guide: docs/multi_tenant/taxonomy-refactor/04-phase4-cleanup.md"
    )
    raise DeprecationWarning(
        "taxonomy_loader.get_topic_taxonomy() is deprecated. "
        "Use content_router.get_tenant_taxonomy(tenant_id) instead. "
        "See: docs/multi_tenant/taxonomy-refactor/04-phase4-cleanup.md"
    )

    # 2) Fallback to file
    try:
        if not _TAXONOMY_PATH.exists():
            logger.info("Topic taxonomy file not found; using built-in fallbacks")
            _CACHED_TAXONOMY = None
            _CACHE_SOURCE = "file"
            return None

        with _TAXONOMY_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict) or "categories" not in data:
                logger.warning("Invalid taxonomy format; expected top-level 'categories'")
                _CACHED_TAXONOMY = None
                _CACHE_SOURCE = "file"
                return None
            _CACHED_TAXONOMY = data
            _CACHE_SOURCE = "file"
            logger.info("Topic taxonomy loaded from file")
            return _CACHED_TAXONOMY
    except Exception as e:
        logger.warning(f"Failed to load topic taxonomy from file: {e}")
        _CACHED_TAXONOMY = None
        _CACHE_SOURCE = "file"
        return None
