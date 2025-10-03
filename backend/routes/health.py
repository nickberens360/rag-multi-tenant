"""
Health check endpoints for monitoring application status.

This module contains health-related endpoints:
- Root endpoint for basic status
- Status endpoint with detailed information
- Health check endpoint with service validation
- Rate limits endpoint for LLM status monitoring
"""

import logging
import os
import time

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..core.config_v2 import AppConfig
from ..core.db_session import get_db_session
from ..dependencies import get_app_state, get_tenant_context

router = APIRouter()
logger = logging.getLogger(__name__)


def _get_current_primary_llm() -> str:
    """Get the current primary LLM from database settings with fallback."""
    try:
        from ..core.settings_manager import get_settings_manager

        settings_manager = get_settings_manager()
        system_config = settings_manager.get_system_config_settings()
        return system_config.primary_llm
    except Exception:
        # Fallback to configured default via config_v2
        return AppConfig.get_primary_llm()


@router.get(
    "/",
    tags=["Health"],
    summary="Root Status Check",
    description="Quick health check endpoint. Returns basic application status.",
    responses={
        200: {
            "description": "Application status",
            "content": {
                "application/json": {
                    "examples": {
                        "healthy": {"summary": "Application running", "value": {"status": "healthy"}},
                        "degraded": {"summary": "Application starting", "value": {"status": "degraded"}},
                    }
                }
            },
        }
    },
)
async def root(state: dict = Depends(get_app_state)):
    return {"status": "healthy" if state["app_initialized"] else "degraded"}


@router.get(
    "/status",
    tags=["Health"],
    summary="Detailed System Status",
    description="""
           **Comprehensive system status with AI service information.**
           
           Returns detailed information about:
           - Application initialization status
           - AI model availability and rate limits
           - Primary LLM configuration
           - Timestamp for monitoring
           
           **Rate Limits:** This endpoint helps you monitor which AI models are currently available vs rate-limited.
           """,
    responses={
        200: {
            "description": "Detailed system status",
            "content": {
                "application/json": {
                    "example": {
                        "status": "online",
                        "timestamp": 1694123456.789,
                        "primary_llm": "claude",
                        "app_initialized": True,
                        "rate_limits": {"claude": False, "gemini": False},
                    }
                }
            },
        }
    },
)
async def status(state: dict = Depends(get_app_state)):
    """Status check with rate limit information."""
    try:
        # Import here to avoid circular imports
        from ..core.llm_chain import get_rate_limit_status

        rate_limits = get_rate_limit_status()
    except Exception:
        # Fallback if rate limit checking fails
        rate_limits = {"claude": False, "gemini": False}
        logger.exception("Error getting rate limits")

    return {
        "status": "online",
        "timestamp": time.time(),
        "primary_llm": _get_current_primary_llm(),
        "app_initialized": state["app_initialized"],
        "rate_limits": rate_limits,
    }


@router.get(
    "/health",
    tags=["Health"],
    summary="Health Check with Service Validation",
    description="""
           **Health check endpoint for monitoring and load balancers.**
           
           Validates:
           - Application initialization status
           - Illustration service availability 
           - Knowledge base readiness
           
           Use this endpoint for:
           - Load balancer health checks
           - Monitoring system alerts
           - Container orchestration readiness probes
           """,
    responses={
        200: {
            "description": "Application health status",
            "content": {
                "application/json": {
                    "examples": {
                        "healthy": {
                            "summary": "Fully operational",
                            "value": {"status": "healthy", "illustration_count": 15},
                        },
                        "initializing": {
                            "summary": "Still starting up",
                            "value": {"status": "initializing", "illustration_count": 0},
                        },
                    }
                }
            },
        }
    },
)
async def health_check(state: dict = Depends(get_app_state)):
    illustration_count = 0
    try:
        if state["illustration_service"]:
            count = state["illustration_service"].get_all()
            illustration_count = len(count)
    except Exception:
        # During startup, illustration service may not be ready
        illustration_count = 0

    return {
        "status": "healthy" if state["app_initialized"] else "initializing",
        "illustration_count": illustration_count,
    }


@router.get(
    "/rate-limits",
    tags=["Health"],
    summary="AI Model Rate Limit Status",
    description="""
           **Monitor AI model availability and rate limiting status.**
           
           Returns the current rate limit status for all configured LLM providers:
           - `false`: Model is available and not rate limited
           - `true`: Model is currently rate limited
           
           **Use Cases:**
           - Monitor AI service health
           - Implement client-side fallback logic
           - Track service availability metrics
           
           **Rate Limit Details:**
           - Claude: Anthropic API rate limits
           - Gemini: Google AI rate limits
           """,
    responses={
        200: {
            "description": "Rate limit status for all LLM providers",
            "content": {
                "application/json": {
                    "examples": {
                        "all_available": {
                            "summary": "All models available",
                            "value": {"rate_limits": {"claude": False, "gemini": False}},
                        },
                        "claude_limited": {
                            "summary": "Claude rate limited",
                            "value": {"rate_limits": {"claude": True, "gemini": False}},
                        },
                    }
                }
            },
        },
        500: {
            "description": "Error retrieving rate limit status",
            "content": {
                "application/json": {
                    "example": {
                        "error": "Failed to get rate limit status",
                        "rate_limits": {"claude": False, "gemini": False},
                    }
                }
            },
        },
    },
)
async def get_rate_limits():
    """Get current rate limit status for all LLM providers."""
    try:
        # Import here to avoid circular imports
        from ..core.llm_chain import get_rate_limit_status

        rate_limits = get_rate_limit_status()

        return JSONResponse(content={"rate_limits": rate_limits})
    except Exception:
        logger.exception("Error getting rate limits")
        return JSONResponse(
            content={"error": "Failed to get rate limit status", "rate_limits": {"claude": False, "gemini": False}},
            status_code=500,
        )


@router.get(
    "/db-paths",
    tags=["Health"],
    summary="Database Path Status (Debug)",
    description="Debug endpoint to check which database paths are being used",
)
async def get_db_paths(db: Session = Depends(get_db_session)):
    """Debug endpoint to check Postgres connectivity and basic info."""
    try:
        # Basic connectivity and server version
        version_row = db.execute(text("SELECT version()"))
        version = version_row.scalar() if version_row else None
        # Tenant context check (if RLS enabled)
        try:
            tid_row = db.execute(text("SELECT current_setting('app.tenant_id', true)"))
            tenant_ctx = tid_row.scalar() if tid_row else None
        except Exception:
            tenant_ctx = None

        return {
            "database": "postgres",
            "server_version": version,
            "tenant_context": tenant_ctx,
        }
    except Exception as e:
        return {"database": "postgres", "error": str(e)}


@router.get(
    "/welcome-questions",
    tags=["Public API"],
    summary="Get Welcome Questions",
    description="""
           **Public endpoint for homepage welcome questions.**

           Returns active welcome questions configured in the admin panel.
           These are the suggested questions displayed to users on the homepage.

           **Public Access:** This endpoint does not require authentication.
           **Tenant Scoped:** Returns questions for the current tenant context.
           """,
    responses={
        200: {
            "description": "List of active welcome questions",
            "content": {
                "application/json": {
                    "example": {
                        "questions": [
                            {"id": 1, "question_text": "Tell me about yourself", "sort_order": 1},
                            {"id": 2, "question_text": "Show me your resume", "sort_order": 2},
                        ]
                    }
                }
            },
        }
    },
)
async def get_welcome_questions(
    request: Request,
    db: Session = Depends(get_db_session),
    tenant_context: dict = Depends(get_tenant_context),
):
    """Get active welcome questions for homepage display, scoped to current tenant."""
    try:
        # Extract tenant_id from context (already validated by dependency)
        tenant_id = (
            tenant_context.get("tenant_id") or os.getenv("DEFAULT_TENANT_ID") or "00000000-0000-0000-0000-000000000001"
        )

        # Set tenant context for RLS enforcement
        db.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": str(tenant_id)})

        # Explicit tenant filter as defense-in-depth alongside RLS
        tenant_filter = "tenant_id = COALESCE(NULLIF(current_setting('app.tenant_id', true), '')::uuid, CAST(:fallback_tid AS uuid))"
        query = (
            "SELECT id, question_text, COALESCE(sort_order, 0) AS sort_order\n"
            "FROM welcome_questions\n"
            "WHERE is_active = true AND " + tenant_filter + "\nORDER BY sort_order, id\n"
        )
        rows = db.execute(
            text(query),
            {"fallback_tid": str(tenant_id)},
        ).fetchall()

        logger.debug(f"Fetched {len(rows)} welcome questions for tenant {tenant_id}")
        return {"questions": [{"id": int(r[0]), "question_text": r[1], "sort_order": int(r[2] or 0)} for r in rows]}

    except Exception:
        # Fallback to default questions if database is unavailable
        logger.exception("Error getting welcome questions")
        return {
            "questions": [
                {"id": 1, "question_text": "Tell me about yourself", "sort_order": 1},
                {"id": 2, "question_text": "Show me your resume", "sort_order": 2},
                {"id": 3, "question_text": "Show me your illustrations", "sort_order": 3},
            ]
        }
