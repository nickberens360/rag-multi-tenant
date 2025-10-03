"""
FastAPI dependencies for accessing application state.

This module provides dependency functions that access application state
stored in app.state, following FastAPI best practices for dependency injection.
"""

from fastapi import Depends, HTTPException, Request

from .core.app_initializer_v2 import get_unified_retriever
from .core.smart_query_handler import SmartQueryHandler


def get_app_state(request: Request):
    """
    Dependency to get current app state.

    Args:
        request: FastAPI request object containing app state

    Returns:
        dict: Dictionary containing app initialization status and illustration service
    """
    return {
        "app_initialized": getattr(request.app.state, "app_initialized", False),
        "illustration_service": getattr(request.app.state, "illustration_service", None),
    }


def get_services(request: Request):
    """
    Dependency to get current services state.

    Args:
        request: FastAPI request object containing app state

    Returns:
        dict: Dictionary containing all services needed for query processing
    """
    return {
        "retrievers": getattr(request.app.state, "retrievers", None),
        "illustration_service": getattr(request.app.state, "illustration_service", None),
        "query_router": getattr(request.app.state, "query_router", None),
        "response_service": getattr(request.app.state, "response_service", None),
        "followup_service": getattr(request.app.state, "followup_service", None),
    }


def get_smart_handler(request: Request, services: dict = Depends(get_services)) -> SmartQueryHandler:
    """
    Dependency to get an initialized SmartQueryHandler with tenant context.
    """
    retrievers = services.get("retrievers")
    if not retrievers:
        raise HTTPException(status_code=500, detail="Retrievers not available")

    unified_retriever = get_unified_retriever(retrievers)
    if not unified_retriever:
        raise HTTPException(status_code=500, detail="Unified retriever not available")

    llm = getattr(request.app.state, "llm", None)
    if not llm:
        raise HTTPException(status_code=500, detail="LLM not initialized")

    return SmartQueryHandler(unified_retriever, llm, use_fast_classifier=True)


def get_tenant_context(request: Request) -> dict:
    """
    Dependency to get tenant context from request state.

    Returns:
        dict: Contains tenant_id and tenant_slug from middleware
    """
    return {
        "tenant_id": getattr(request.state, "tenant_id", None),
        "tenant_slug": getattr(request.state, "tenant_slug", None),
    }
