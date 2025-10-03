"""
Performance analytics API routes for admin dashboard.

Provides detailed performance metrics including:
- Response time metrics and percentiles
- Query throughput analysis
- Timeline data for charts
- Error rate tracking
"""

import logging
from datetime import timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..core.config_v2 import AppConfig
from ..core.date_utils import parse_time_range

logger = logging.getLogger(__name__)
router = APIRouter()


class PerformanceMetrics(BaseModel):
    """Model for performance metrics response."""

    response_time: dict
    throughput: dict
    error_rate: dict
    cache_hit_rate: dict


class TimelinePoint(BaseModel):
    """Model for timeline data point."""

    timestamp: str
    avg_response_time: float
    query_count: int
    error_rate: float
    cache_hit_rate: float


class PerformanceTimeline(BaseModel):
    """Model for performance timeline response."""

    timeline: List[TimelinePoint]


class PercentileMetrics(BaseModel):
    """Model for response time percentiles."""

    p50: float
    p95: float
    p99: float


# Database connection utility imported from shared module
from ..core.db_session import get_db_session


@router.get("/performance/metrics", response_model=PerformanceMetrics)
async def get_performance_metrics(
    request: Request,
    time_range: str = Query("24h", description="Time range for metrics (1h, 6h, 24h, 7d, 30d)"),
    pg_session: Session | None = Depends(get_db_session),
):
    """Get performance metrics with current and previous period comparison (Postgres + RLS only)."""
    try:
        # Get tenant context from middleware
        tenant_id = getattr(request.state, "tenant_id", None)
        tenant_slug = getattr(request.state, "tenant_slug", None)

        logger.info(f"Fetching performance metrics for tenant: {tenant_slug} (ID: {tenant_id})")

        if pg_session is None:
            raise HTTPException(status_code=503, detail="Postgres session unavailable")

        # Build tenant filter
        tenant_filter = "AND tenant_id = :tenant_id" if tenant_id else ""
        base_params = {"tenant_id": tenant_id} if tenant_id else {}

        # Check available data and get actual latest timestamp
        min_max_sql = f"SELECT MIN(timestamp), MAX(timestamp) FROM query_logs WHERE 1=1 {tenant_filter}"
        result = pg_session.execute(text(min_max_sql), base_params).first()
        earliest_data, latest_data = (result[0], result[1]) if result else (None, None)
        if not earliest_data or not latest_data:
            return PerformanceMetrics(
                response_time={"current": 0, "previous": 0, "change": 0},
                throughput={"current": 0, "previous": 0, "change": 0},
                error_rate={"current": 0, "previous": 0, "change": 0},
                cache_hit_rate={
                    "current": 0,
                    "previous": 0,
                    "change": 0,
                },
            )

        # Use actual latest data timestamp for accurate time range calculation
        end_date = latest_data
        start_date, end_date = parse_time_range(time_range, end_date)

        # Determine previous period window
        period_duration = end_date - start_date
        previous_period_end = start_date
        previous_period_start = previous_period_end - period_duration

        current_period_start = start_date.isoformat()
        current_period_end = end_date.isoformat()
        previous_start = previous_period_start.isoformat()
        previous_end = previous_period_end.isoformat()

        # Build params for current and previous periods
        current_params = {**base_params, "s": current_period_start, "e": current_period_end}
        previous_params = {**base_params, "s": previous_start, "e": previous_end}

        # Current/previous response time
        current_response_time = (
            pg_session.execute(
                text(
                    f"SELECT AVG(response_time_ms) FROM query_logs WHERE timestamp >= :s AND timestamp <= :e AND response_time_ms IS NOT NULL {tenant_filter}"
                ),
                current_params,
            ).scalar()
            or 0.0
        )
        previous_response_time = (
            pg_session.execute(
                text(
                    f"SELECT AVG(response_time_ms) FROM query_logs WHERE timestamp >= :s AND timestamp <= :e AND response_time_ms IS NOT NULL {tenant_filter}"
                ),
                previous_params,
            ).scalar()
            or 0.0
        )
        response_time_change = 0.0
        if previous_response_time > 0:
            response_time_change = ((current_response_time - previous_response_time) / previous_response_time) * 100

        # Throughput (queries per hour)
        current_queries = (
            pg_session.execute(
                text(f"SELECT COUNT(*) FROM query_logs WHERE timestamp >= :s AND timestamp <= :e {tenant_filter}"),
                current_params,
            ).scalar()
            or 0
        )
        previous_queries = (
            pg_session.execute(
                text(f"SELECT COUNT(*) FROM query_logs WHERE timestamp >= :s AND timestamp <= :e {tenant_filter}"),
                previous_params,
            ).scalar()
            or 0
        )
        period_hours = (end_date - start_date).total_seconds() / 3600
        current_throughput = current_queries / period_hours if period_hours > 0 else 0
        previous_throughput = previous_queries / period_hours if period_hours > 0 else 0
        throughput_change = 0.0
        if previous_throughput > 0:
            throughput_change = ((current_throughput - previous_throughput) / previous_throughput) * 100

        # Error rate current/previous
        total_current = (
            pg_session.execute(
                text(f"SELECT COUNT(*) FROM query_logs WHERE timestamp >= :s AND timestamp <= :e {tenant_filter}"),
                current_params,
            ).scalar()
            or 0
        )
        errors_current = (
            pg_session.execute(
                text(
                    f"SELECT COUNT(*) FROM query_logs WHERE timestamp >= :s AND timestamp <= :e AND error_occurred = true {tenant_filter}"
                ),
                current_params,
            ).scalar()
            or 0
        )
        current_error_rate = (errors_current / total_current) if total_current > 0 else 0.0

        total_previous = (
            pg_session.execute(
                text(f"SELECT COUNT(*) FROM query_logs WHERE timestamp >= :s AND timestamp <= :e {tenant_filter}"),
                previous_params,
            ).scalar()
            or 0
        )
        errors_previous = (
            pg_session.execute(
                text(
                    f"SELECT COUNT(*) FROM query_logs WHERE timestamp >= :s AND timestamp <= :e AND error_occurred = true {tenant_filter}"
                ),
                previous_params,
            ).scalar()
            or 0
        )
        previous_error_rate = (errors_previous / total_previous) if total_previous > 0 else 0.0
        error_rate_change = 0.0
        if previous_error_rate > 0:
            error_rate_change = ((current_error_rate - previous_error_rate) / previous_error_rate) * 100

        return PerformanceMetrics(
            response_time={
                "current": round(current_response_time, 1),
                "previous": round(previous_response_time, 1),
                "change": round(response_time_change, 2),
            },
            throughput={
                "current": round(current_throughput, 2),
                "previous": round(previous_throughput, 2),
                "change": round(throughput_change, 2),
            },
            error_rate={
                "current": round(current_error_rate * 100, 2),
                "previous": round(previous_error_rate * 100, 2),
                "change": round(error_rate_change, 2),
            },
            cache_hit_rate={
                "current": AppConfig.DEFAULT_CACHE_HIT_RATE * 100,
                "previous": AppConfig.DEFAULT_CACHE_HIT_RATE * 100,
                "change": 0,
            },
        )

    except Exception as e:
        logger.error(f"Error in get_performance_metrics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/performance/timeline", response_model=PerformanceTimeline)
async def get_performance_timeline(
    request: Request,
    days: float = Query(7, ge=0.1, le=30, description="Number of days for timeline"),
    interval: str = Query("hour", description="Interval for timeline (hour, day)"),
    pg_session: Session | None = Depends(get_db_session),
):
    """Get performance timeline data for charts (Postgres + RLS only)."""
    try:
        # Get tenant context from middleware
        tenant_id = getattr(request.state, "tenant_id", None)
        tenant_slug = getattr(request.state, "tenant_slug", None)

        logger.info(f"Fetching performance timeline for tenant: {tenant_slug} (ID: {tenant_id})")

        if pg_session is None:
            raise HTTPException(status_code=503, detail="Postgres session unavailable")

        # Build tenant filter
        tenant_filter = "AND tenant_id = :tenant_id" if tenant_id else ""

        # Check if we have any data and get actual latest timestamp
        max_time_sql = f"SELECT MAX(timestamp) FROM query_logs WHERE 1=1 {tenant_filter}"
        params = {"tenant_id": tenant_id} if tenant_id else {}
        result = pg_session.execute(text(max_time_sql), params).first()
        if not result or not result[0]:
            # No data available
            return PerformanceTimeline(timeline=[])

        # Use actual latest data timestamp for accurate time range
        end_date = result[0]
        start_date = end_date - timedelta(days=days)

        # Add start/end to params
        params["start"] = start_date
        params["end"] = end_date

        if interval == "hour":
            sql = text(
                f"""
                SELECT to_char(date_trunc('hour', timestamp), 'YYYY-MM-DD HH24:00:00') AS time_bucket,
                       AVG(response_time_ms) AS avg_response_time,
                       COUNT(*) AS query_count,
                       AVG(CASE WHEN error_occurred THEN 1 ELSE 0 END) AS error_rate
                FROM query_logs
                WHERE timestamp >= :start AND timestamp <= :end {tenant_filter}
                GROUP BY 1
                ORDER BY 1
                """
            )
        else:
            sql = text(
                f"""
                SELECT to_char(date_trunc('day', timestamp), 'YYYY-MM-DD') AS time_bucket,
                       AVG(response_time_ms) AS avg_response_time,
                       COUNT(*) AS query_count,
                       AVG(CASE WHEN error_occurred THEN 1 ELSE 0 END) AS error_rate
                FROM query_logs
                WHERE timestamp >= :start AND timestamp <= :end {tenant_filter}
                GROUP BY 1
                ORDER BY 1
                """
            )

        rows = pg_session.execute(sql, params).fetchall()
        timeline_points = [
            TimelinePoint(
                timestamp=row[0],
                avg_response_time=row[1] or 0.0,
                query_count=row[2] or 0,
                error_rate=(row[3] or 0.0) * 100,
                cache_hit_rate=AppConfig.DEFAULT_CACHE_HIT_RATE * 100,
            )
            for row in rows
        ]
        return PerformanceTimeline(timeline=timeline_points)
    except Exception as e:
        logger.error(f"Error in get_performance_timeline: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/performance/percentiles", response_model=PercentileMetrics)
async def get_response_time_percentiles(
    time_range: str = Query("24h", description="Time range for percentiles (1h, 6h, 24h, 7d, 30d)"),
    pg_session: Session | None = Depends(get_db_session),
):
    """Get response time percentiles (Postgres + RLS only)."""
    try:
        if pg_session is None:
            raise HTTPException(status_code=503, detail="Postgres session unavailable")

        # Get actual latest timestamp from data for accurate time range
        result = pg_session.execute(text("SELECT MAX(timestamp) FROM query_logs")).first()
        if not result or not result[0]:
            return PercentileMetrics(p50=0, p95=0, p99=0)

        end_date = result[0]
        start_date, end_date = parse_time_range(time_range, end_date)
        rows = pg_session.execute(
            text(
                """
                SELECT response_time_ms
                FROM query_logs
                WHERE timestamp >= :start AND timestamp <= :end
                  AND response_time_ms IS NOT NULL
                ORDER BY response_time_ms
                """
            ),
            {"start": start_date, "end": end_date},
        ).fetchall()
        response_times = [r[0] for r in rows]

        if not response_times:
            return PercentileMetrics(p50=0, p95=0, p99=0)

        # Calculate percentiles
        def get_percentile(data, percentile):
            if not data:
                return 0
            index = int((percentile / 100) * len(data)) - 1
            index = max(0, min(index, len(data) - 1))
            return data[index]

        p50 = get_percentile(response_times, 50)
        p95 = get_percentile(response_times, 95)
        p99 = get_percentile(response_times, 99)

        return PercentileMetrics(p50=round(p50, 1), p95=round(p95, 1), p99=round(p99, 1))

    except Exception as e:
        logger.error(f"Error in get_response_time_percentiles: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
