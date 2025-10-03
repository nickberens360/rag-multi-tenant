"""
Query logs endpoint for viewing logged queries and responses.

This module provides a protected endpoint to:
- View query logs with filtering options
- Get log statistics
- Clear logs (admin function)
"""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi import Query as FastAPIQuery
from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..core.admin_auth import require_admin_auth
from ..core.db_session import get_db_session

# Initialize router and security
router = APIRouter()

# Check if we're in testing environment to disable rate limiting
import os

_is_testing = os.getenv("TESTING", "false").lower() == "true" or "pytest" in os.environ.get("_", "")

if _is_testing:
    # Use memory storage during testing to avoid rate limiting issues
    limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")
else:
    limiter = Limiter(key_func=get_remote_address)

# Initialize logger
logger = logging.getLogger(__name__)

# Initialize templates
template_dir = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(template_dir))


@router.get("/query-logs")
@limiter.limit("60/minute")  # Reasonable rate limit for log viewing
async def get_query_logs(
    request: Request,
    session: dict = Depends(require_admin_auth),
    pg_session: Session | None = Depends(get_db_session),
    limit: Optional[int] = FastAPIQuery(default=100, ge=1, le=1000, description="Maximum number of logs to return"),
    start_date: Optional[str] = FastAPIQuery(default=None, description="Start date filter (YYYY-MM-DD format)"),
    end_date: Optional[str] = FastAPIQuery(default=None, description="End date filter (YYYY-MM-DD format)"),
    query_type: Optional[str] = FastAPIQuery(default=None, description="Filter by query type (text/image)"),
    exclude_ips: Optional[str] = FastAPIQuery(
        default=None, description="Comma-separated list of IP addresses to exclude (anonymized hashes)"
    ),
) -> Dict[str, Any]:
    """
    Retrieve query logs with optional filtering.

    Requires admin session authentication.

    Query Parameters:
    - limit: Maximum number of logs to return (1-1000, default: 100)
    - start_date: Start date filter in YYYY-MM-DD format
    - end_date: End date filter in YYYY-MM-DD format
    - query_type: Filter by query type (text/image)
    - exclude_ips: Comma-separated list of IP addresses to exclude (anonymized hashes)
    """
    if pg_session is None:
        raise HTTPException(status_code=503, detail="Postgres session unavailable")

    # Validate date formats if provided
    if start_date:
        try:
            _sd = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            start_date = _sd.isoformat()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date format. Use YYYY-MM-DD format.")

    if end_date:
        try:
            # Add time component to include the entire end date
            _ed = datetime.strptime(end_date + " 23:59:59", "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            end_date = _ed.isoformat()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_date format. Use YYYY-MM-DD format.")

    # Validate query type
    if query_type and query_type not in ["text", "image"]:
        raise HTTPException(status_code=400, detail="Invalid query_type. Must be 'text' or 'image'.")

    # Build where clause
    where = []
    params: Dict[str, Any] = {}
    if start_date:
        where.append("timestamp >= :start")
        params["start"] = start_date
    if end_date:
        where.append("timestamp <= :end")
        params["end"] = end_date
    if query_type:
        where.append("query_type = :qt")
        params["qt"] = query_type

    where_clause = f" WHERE {' AND '.join(where)}" if where else ""

    rows = pg_session.execute(
        text(
            f"""
            SELECT id, user_query, system_response, query_type, response_time_ms,
                   llm_model, error_occurred, error_message, user_feedback,
                   timestamp, client_ip
            FROM query_logs
            {where_clause}
            ORDER BY timestamp DESC
            LIMIT :limit
            """
        ),
        {**params, "limit": limit},
    ).fetchall()

    logs = []
    for r in rows:
        logs.append(
            {
                "id": str(r[0]),
                "user_query": r[1],
                "system_response": r[2],
                "query_type": r[3],
                "response_time_ms": r[4],
                "llm_model": r[5],
                "error_occurred": r[6],
                "error_message": r[7],
                "user_feedback": r[8],
                "timestamp": r[9].isoformat() if r[9] else None,
                "client_ip": r[10],
            }
        )

    return {
        "logs": logs,
        "count": len(logs),
        "filters": {
            "limit": limit,
            "start_date": start_date,
            "end_date": end_date,
            "query_type": query_type,
            "exclude_ips": exclude_ips,
        },
    }


@router.get("/query-logs/stats")
@limiter.limit("30/minute")  # Stats endpoint rate limit
async def get_query_log_stats(
    request: Request,
    session: dict = Depends(require_admin_auth),
    pg_session: Session | None = Depends(get_db_session),
    exclude_ips: Optional[str] = FastAPIQuery(
        default=None, description="Comma-separated list of IPs to exclude from stats"
    ),
) -> Dict[str, Any]:
    """
    Get statistics about query logs.

    Requires admin session authentication.

    Returns summary statistics including:
    - Total number of queries
    - Unique IP count
    - Query type breakdown
    - Model usage breakdown
    - Date range of logs

    Query Parameters:
    - exclude_ips: Comma-separated list of IPs to exclude from statistics
    """
    if pg_session is None:
        raise HTTPException(status_code=503, detail="Postgres session unavailable")

    total = pg_session.execute(text("SELECT COUNT(*) FROM query_logs")).scalar() or 0
    # Unique IPs (nullable)
    unique_ips = (
        pg_session.execute(
            text("SELECT COUNT(DISTINCT client_ip) FROM query_logs WHERE client_ip IS NOT NULL")
        ).scalar()
        or 0
    )
    # Type breakdown
    type_rows = pg_session.execute(text("SELECT query_type, COUNT(*) FROM query_logs GROUP BY query_type")).fetchall()
    type_breakdown = {row[0] or "unknown": row[1] for row in type_rows}
    # Model breakdown
    model_rows = pg_session.execute(text("SELECT llm_model, COUNT(*) FROM query_logs GROUP BY llm_model")).fetchall()
    model_breakdown = {row[0] or "unknown": row[1] for row in model_rows}
    # Range
    minmax = pg_session.execute(text("SELECT MIN(timestamp), MAX(timestamp) FROM query_logs")).first()
    earliest, latest = (minmax[0], minmax[1]) if minmax else (None, None)

    stats = {
        "total_queries": total,
        "unique_ips": unique_ips,
        "query_type_breakdown": type_breakdown,
        "model_usage": model_breakdown,
        "date_range": {
            "earliest": earliest.isoformat() if earliest else None,
            "latest": latest.isoformat() if latest else None,
        },
    }

    return {"stats": stats, "generated_at": datetime.now(timezone.utc).isoformat(), "excluded_ips": exclude_ips}


@router.delete("/query-logs")
@limiter.limit("5/minute")  # Restrictive rate limit for destructive operations
async def clear_query_logs(
    request: Request, session: dict = Depends(require_admin_auth), pg_session: Session | None = Depends(get_db_session)
) -> Dict[str, Any]:
    """
    Clear all query logs (use with caution).

    Requires admin session authentication.

    This action is irreversible and will delete all logged queries.
    """
    if pg_session is None:
        raise HTTPException(status_code=503, detail="Postgres session unavailable")
    # RLS ensures deletion is tenant-scoped
    result = pg_session.execute(text("DELETE FROM query_logs"))
    deleted = result.rowcount or 0
    return {
        "message": "Query logs cleared successfully",
        "deleted": deleted,
        "cleared_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/query-logs/download")
@limiter.limit("5/minute")
async def download_query_logs(
    request: Request, session: dict = Depends(require_admin_auth), pg_session: Session | None = Depends(get_db_session)
) -> Dict[str, Any]:
    """
    Export query logs from SQLite database as JSON.

    Requires admin session authentication.

    Returns all logs from SQLite database in JSON format.
    For large datasets, consider adding pagination or streaming.
    """
    if pg_session is None:
        raise HTTPException(status_code=503, detail="Postgres session unavailable")

    rows = pg_session.execute(
        text(
            """
            SELECT id, user_query, system_response, query_type, response_time_ms,
                   llm_model, error_occurred, error_message, user_feedback,
                   timestamp, client_ip
            FROM query_logs
            ORDER BY timestamp DESC
            """
        )
    ).fetchall()
    logs = [
        {
            "id": str(r[0]),
            "user_query": r[1],
            "system_response": r[2],
            "query_type": r[3],
            "response_time_ms": r[4],
            "llm_model": r[5],
            "error_occurred": r[6],
            "error_message": r[7],
            "user_feedback": r[8],
            "timestamp": r[9].isoformat() if r[9] else None,
            "client_ip": r[10],
        }
        for r in rows
    ]
    return {
        "logs": logs,
        "count": len(logs),
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "format": "json",
        "storage_type": "postgres",
    }


@router.get("/query-logs/health")
async def query_logs_health(pg_session: Session | None = Depends(get_db_session)) -> Dict[str, Any]:
    """
    Health check endpoint for query logging system.

    This endpoint does not require authentication and can be used to verify
    that the query logging system is operational.
    """
    try:
        if pg_session is None:
            return {"status": "unhealthy", "error": "Postgres session unavailable"}
        total = pg_session.execute(text("SELECT COUNT(*) FROM query_logs")).scalar() or 0
        return {
            "status": "healthy",
            "total_logs": total,
            "auth_method": "session-based",
            "storage_type": "postgres",
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


@router.get("/query-logs/admin", response_class=HTMLResponse)
async def query_logs_admin_page(request: Request) -> HTMLResponse:
    """
    Serve the query logs admin web interface.

    This endpoint serves a web interface for managing query logs.
    No authentication required for serving the page (auth happens via API calls).
    """
    # Get the client IP address
    client_ip = request.client.host if request.client else "127.0.0.1"

    # Minimal placeholders; IP anonymization moved out of SQLite logger
    my_ip_hash = client_ip
    my_local_ip_hash = "127.0.0.1"

    # Render template with dynamic values
    return templates.TemplateResponse(
        "query_logs_admin.html", {"request": request, "my_ip_hash": my_ip_hash, "my_local_ip_hash": my_local_ip_hash}
    )
