"""
Query logging service factory.

This module provides a factory function to get the query logger instance,
which uses SQLite database for persistent storage of query logs.
"""

from typing import Any, Optional

# Global instance
_query_logger_instance: Optional[Any] = None


def get_query_logger() -> Any:
    """Return a singleton Postgres query logger (RLS-aware)."""
    global _query_logger_instance
    if _query_logger_instance is None:
        from .pg_query_logger import PostgresQueryLogger

        _query_logger_instance = PostgresQueryLogger()
    return _query_logger_instance
