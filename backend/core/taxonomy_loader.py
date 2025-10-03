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
    """Load and cache the topic taxonomy configuration.

    Priority:
      1) DB value from admin_settings (key: 'taxonomy_settings') if available
      2) Fallback to bundled file backend/core/topic_taxonomy.json

    Returns None if neither source is available/valid. Callers should handle fallbacks.
    """
    global _CACHED_TAXONOMY
    global _CACHE_SOURCE

    if _CACHED_TAXONOMY is not None and not force_reload:
        return _CACHED_TAXONOMY

    # 1) Try database-backed taxonomy first when available
    try:
        settings_mgr = get_settings_manager()
        json_str = settings_mgr._get_setting_from_db("taxonomy_settings")  # internal use
        if json_str:
            data = json.loads(json_str)
            if isinstance(data, dict) and isinstance(data.get("categories"), dict):
                _CACHED_TAXONOMY = data
                _CACHE_SOURCE = "db"
                logger.info("Topic taxonomy loaded from DB (admin_settings)")
                return _CACHED_TAXONOMY
            else:
                logger.warning("Invalid taxonomy format from DB; expected top-level 'categories' object")
    except Exception as e:
        logger.warning(f"Failed to load taxonomy from DB: {e}")

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
