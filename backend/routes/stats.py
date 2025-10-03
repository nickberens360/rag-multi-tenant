"""
Admin dashboard statistics API routes.

Provides endpoints for:
- Overview statistics for dashboard
- System performance metrics
- Query analytics
"""

import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.models.admin_models import OverviewStats  # reuse shared model

from ..core.config_v2 import AppConfig

logger = logging.getLogger(__name__)
router = APIRouter()

# NOTE: Using shared OverviewStats model from admin_models


# Database connection utility imported from shared module
from ..core.db_session import get_db_session


@router.get("/stats/overview", response_model=OverviewStats)
async def get_stats_overview(
    request: Request,
    days: float = Query(7, ge=0.1, le=90, description="Number of days for statistics"),
    pg_session: Session | None = Depends(get_db_session),
):
    """
    Get overview statistics for the admin dashboard.

    Args:
        request: FastAPI request object (for tenant context)
        days: Number of days to include in statistics
        tenant: Optional tenant slug to filter data by specific tenant
    """
    try:
        # Get tenant context from middleware
        tenant_id = getattr(request.state, "tenant_id", None)
        tenant_slug = getattr(request.state, "tenant_slug", None)

        # Log tenant filtering for debugging
        logger.info(f"Filtering admin stats for tenant: {tenant_slug} (ID: {tenant_id})")

        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=7)

        if pg_session is None:
            raise HTTPException(status_code=503, detail="Postgres session unavailable")

        # Build WHERE clause for tenant filtering
        tenant_filter = "AND tenant_id = :tenant_id" if tenant_id else ""
        params_base = {"start": start_date, "end": end_date}
        if tenant_id:
            params_base["tenant_id"] = tenant_id

        # Count total queries for the period (with tenant filtering)
        total_queries = (
            pg_session.execute(
                text(
                    f"SELECT COUNT(*) FROM query_logs WHERE timestamp >= :start AND timestamp <= :end {tenant_filter}"
                ),
                params_base,
            ).scalar()
            or 0
        )

        avg_response_time = (
            pg_session.execute(
                text(
                    f"SELECT AVG(response_time_ms) FROM query_logs WHERE timestamp >= :start AND timestamp <= :end AND response_time_ms IS NOT NULL {tenant_filter}"
                ),
                params_base,
            ).scalar()
            or 0.0
        )

        total = (
            pg_session.execute(
                text(
                    f"SELECT COUNT(*) FROM query_logs WHERE timestamp >= :start AND timestamp <= :end {tenant_filter}"
                ),
                params_base,
            ).scalar()
            or 0
        )
        errors = (
            pg_session.execute(
                text(
                    f"SELECT COUNT(*) FROM query_logs WHERE timestamp >= :start AND timestamp <= :end AND error_occurred = true {tenant_filter}"
                ),
                params_base,
            ).scalar()
            or 0
        )
        error_rate = (errors / total) if total > 0 else 0.0

        # session_id may not exist in Postgres migration; leave unique_sessions as 0
        unique_sessions = 0

        # Build params for time-based queries
        params_today = {"today": today_start}
        params_week = {"week": week_start}
        if tenant_id:
            params_today["tenant_id"] = tenant_id
            params_week["tenant_id"] = tenant_id

        queries_today = (
            pg_session.execute(
                text(f"SELECT COUNT(*) FROM query_logs WHERE timestamp >= :today {tenant_filter}"),
                params_today,
            ).scalar()
            or 0
        )

        queries_this_week = (
            pg_session.execute(
                text(f"SELECT COUNT(*) FROM query_logs WHERE timestamp >= :week {tenant_filter}"),
                params_week,
            ).scalar()
            or 0
        )

        helpful_total = (
            pg_session.execute(
                text(
                    f"SELECT COUNT(*) FROM query_logs WHERE timestamp >= :start AND timestamp <= :end AND user_feedback IS NOT NULL {tenant_filter}"
                ),
                params_base,
            ).scalar()
            or 0
        )
        helpful_count = (
            pg_session.execute(
                text(
                    f"SELECT COUNT(*) FROM query_logs WHERE timestamp >= :start AND timestamp <= :end AND user_feedback = 'helpful' {tenant_filter}"
                ),
                params_base,
            ).scalar()
            or 0
        )
        helpful_rate = (helpful_count / helpful_total) if helpful_total > 0 else 0.0

        # For cache hit rate and sources/topics, use configurable defaults
        # These could be enhanced with actual implementations later
        cache_hit_rate = AppConfig.DEFAULT_CACHE_HIT_RATE
        total_sources = AppConfig.DEFAULT_TOTAL_SOURCES
        total_topics = AppConfig.DEFAULT_TOTAL_TOPICS

        return OverviewStats(
            total_queries=total_queries,
            avg_response_time_ms=round(avg_response_time, 1),
            error_rate=round(error_rate, 3),
            cache_hit_rate=round(cache_hit_rate, 3),
            unique_sessions=unique_sessions,
            total_sources=total_sources,
            total_topics=total_topics,
            queries_today=queries_today,
            queries_this_week=queries_this_week,
            helpful_rate=round(helpful_rate, 3),
        )

    except Exception as e:
        logger.error(f"Error in get_stats_overview: {e}")
        # Return empty stats on any error
        return OverviewStats()
