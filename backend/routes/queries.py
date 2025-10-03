"""
Admin dashboard queries API routes.

Provides endpoints for:
- Query listing and management
- Individual query details
- Query insights and analytics
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)
router = APIRouter()


class QueryItem(BaseModel):
    """Model for individual query data."""

    id: str
    user_query: str
    response: str
    timestamp: str
    response_time_ms: Optional[float] = None
    model_used: Optional[str] = None
    error_occurred: Optional[bool] = None
    error_message: Optional[str] = None
    session_id: Optional[str] = None
    user_feedback: Optional[str] = None
    vector_search_score: Optional[float] = None
    sources_used: Optional[str] = None
    client_ip: Optional[str] = None
    location_city: Optional[str] = None
    location_region: Optional[str] = None
    location_country: Optional[str] = None
    location_country_code: Optional[str] = None


class QueryResponse(BaseModel):
    """Model for query listing response."""

    queries: List[QueryItem]
    total: int
    has_more: bool


class QueryInsights(BaseModel):
    """Model for query insights and analytics."""

    total_queries: int = 0
    avg_response_time: float = 0.0
    error_rate: float = 0.0
    popular_topics: List[str] = []
    feedback_summary: dict = {}


from ..core.db_session import get_db_session


@router.get("/queries", response_model=QueryResponse)
async def get_queries(
    request: Request,
    limit: int = Query(50, ge=1, le=1000, description="Number of queries to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    search: Optional[str] = Query(None, description="Search term for filtering queries"),
    start_date: Optional[str] = Query(None, description="Start date for filtering (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date for filtering (ISO format)"),
    errors_only: Optional[bool] = Query(False, description="Show only queries with errors"),
    min_relevance: Optional[float] = Query(None, description="Minimum relevance score"),
    sort_by: Optional[str] = Query("timestamp", description="Field to sort by"),
    sort_order: Optional[str] = Query("desc", description="Sort order (asc/desc)"),
    pg_session: Session | None = Depends(get_db_session),
):
    """
    Get list of queries with filtering and pagination.
    """
    # Get tenant context from request state
    tenant_id = getattr(request.state, "tenant_id", None)
    tenant_slug = getattr(request.state, "tenant_slug", None)

    logger.info(f"[QueriesEndpoint] Path: {request.url.path} | tenant_id: {tenant_id} | tenant_slug: {tenant_slug}")
    logger.info(
        f"get_queries called for tenant '{tenant_slug}' with sort_by='{sort_by}', sort_order='{sort_order}', search='{search}'"
    )
    try:
        if pg_session is None:
            raise HTTPException(status_code=503, detail="Postgres session unavailable")

        # Build WHERE clause
        where_conditions = []
        params: dict = {}

        # IMPORTANT: Filter by tenant_id for multi-tenant isolation
        if tenant_id:
            where_conditions.append("tenant_id = :tenant_id")
            params["tenant_id"] = tenant_id

        if search:
            where_conditions.append("(user_query ILIKE :search OR system_response ILIKE :search)")
            params["search"] = f"%{search}%"

        if start_date:
            where_conditions.append("timestamp >= :start_date")
            params["start_date"] = start_date

        if end_date:
            where_conditions.append("timestamp <= :end_date")
            params["end_date"] = end_date

        if errors_only:
            where_conditions.append("error_occurred = true")

        if min_relevance is not None:
            where_conditions.append("vector_search_score >= :min_relevance")
            params["min_relevance"] = min_relevance

        where_clause = " WHERE " + " AND ".join(where_conditions) if where_conditions else ""

        # Get total count
        count_query = text(f"SELECT COUNT(*) FROM query_logs{where_clause}")
        total = pg_session.execute(count_query, params).scalar() or 0

        # Build main query with pagination
        order_direction = "DESC" if sort_order.lower() == "desc" else "ASC"
        valid_sort_fields = [
            "timestamp",
            "response_time_ms",
            "user_query",
            "llm_model",
            "error_occurred",
            "vector_search_score",
        ]
        sort_field = sort_by if sort_by in valid_sort_fields else "timestamp"

        query = text(
            f"""
            SELECT id, user_query, system_response, timestamp, response_time_ms,
                   llm_model, error_occurred, error_message, user_feedback,
                   vector_search_score, sources_used::text as sources_used_text, client_ip, location_city,
                   location_region, location_country, location_country_code
            FROM query_logs
            {where_clause}
            ORDER BY {sort_field} {order_direction}
            LIMIT :limit OFFSET :offset
            """
        )

        rows = pg_session.execute(query, {**params, "limit": limit, "offset": offset}).fetchall()

        queries = []
        for row in rows:
            queries.append(
                QueryItem(
                    id=str(row[0]),
                    user_query=row[1] or "",
                    response=row[2] or "",
                    timestamp=str(row[3]) if row[3] is not None else "",
                    response_time_ms=row[4],
                    model_used=row[5],
                    error_occurred=bool(row[6]) if row[6] is not None else None,
                    error_message=row[7],
                    session_id=None,
                    user_feedback=row[8],
                    vector_search_score=row[9],
                    sources_used=row[10],
                    client_ip=row[11],
                    location_city=row[12],
                    location_region=row[13],
                    location_country=row[14],
                    location_country_code=row[15],
                )
            )

        has_more = offset + limit < total

        return QueryResponse(queries=queries, total=total, has_more=has_more)

    except Exception as e:
        logger.error(f"Error in get_queries: {e}")
        return QueryResponse(queries=[], total=0, has_more=False)


@router.get("/queries/insights", response_model=QueryInsights)
async def get_query_insights(pg_session: Session | None = Depends(get_db_session)):
    """
    Get insights and analytics about queries.
    """
    try:
        if pg_session is None:
            raise HTTPException(status_code=503, detail="Postgres session unavailable")

        # Get basic stats
        stats = pg_session.execute(
            text(
                """
                SELECT COUNT(*) AS total_queries,
                       AVG(response_time_ms) AS avg_response_time,
                       COUNT(*) FILTER (WHERE error_occurred = true) AS error_count
                FROM query_logs
                """
            )
        ).first()

        total_queries = int(stats[0]) if stats and stats[0] is not None else 0
        avg_response_time = float(stats[1]) if stats and stats[1] is not None else 0.0
        error_rate = (float(stats[2]) / total_queries) if stats and total_queries > 0 else 0.0

        # Get feedback summary
        rows = pg_session.execute(
            text(
                """
                SELECT user_feedback, COUNT(*) AS count
                FROM query_logs
                WHERE user_feedback IS NOT NULL
                GROUP BY user_feedback
                """
            )
        ).fetchall()
        feedback_summary = {row[0]: row[1] for row in rows}

        # Popular topics (simplified - could be enhanced with real topic analysis)
        popular_topics = ["Development", "Experience", "Skills", "Projects"]

        return QueryInsights(
            total_queries=total_queries,
            avg_response_time=round(avg_response_time, 2),
            error_rate=round(error_rate, 3),
            popular_topics=popular_topics,
            feedback_summary=feedback_summary,
        )
    except Exception as e:
        logger.error(f"Error in get_query_insights: {e}")
        return QueryInsights()


@router.get("/queries/{query_id}", response_model=QueryItem)
async def get_query(query_id: str, pg_session: Session | None = Depends(get_db_session)):
    """
    Get details of a specific query by ID.
    """
    try:
        if pg_session is None:
            raise HTTPException(status_code=503, detail="Postgres session unavailable")

        row = pg_session.execute(
            text(
                """
                SELECT id, user_query, system_response, timestamp, response_time_ms,
                       llm_model, error_occurred, error_message, user_feedback,
                       vector_search_score, sources_used::text, client_ip, location_city,
                       location_region, location_country, location_country_code
                FROM query_logs
                WHERE id = :id
                """
            ),
            {"id": int(query_id)},
        ).first()

        if not row:
            raise HTTPException(status_code=404, detail="Query not found")

        return QueryItem(
            id=str(row[0]),
            user_query=row[1] or "",
            response=row[2] or "",
            timestamp=str(row[3]) if row[3] else "",
            response_time_ms=row[4],
            model_used=row[5],
            error_occurred=bool(row[6]) if row[6] is not None else None,
            error_message=row[7],
            session_id=None,
            user_feedback=row[8],
            vector_search_score=row[9],
            sources_used=row[10],
            client_ip=row[11],
            location_city=row[12],
            location_region=row[13],
            location_country=row[14],
            location_country_code=row[15],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_query: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/queries/{query_id}/feedback")
async def update_query_feedback(
    query_id: str, feedback_data: dict, pg_session: Session | None = Depends(get_db_session)
):
    """
    Update feedback for a specific query.
    """
    try:
        feedback = feedback_data.get("feedback")
        if not feedback:
            raise HTTPException(status_code=400, detail="Feedback is required")

        if pg_session is None:
            raise HTTPException(status_code=503, detail="Postgres session unavailable")

        exists = pg_session.execute(text("SELECT 1 FROM query_logs WHERE id = :id"), {"id": int(query_id)}).first()
        if not exists:
            raise HTTPException(status_code=404, detail="Query not found")
        pg_session.execute(
            text("UPDATE query_logs SET user_feedback = :fb WHERE id = :id"), {"fb": feedback, "id": int(query_id)}
        )

        return {"success": True, "message": "Feedback updated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in update_query_feedback: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
