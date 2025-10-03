"""
Smart query endpoint for testing the unified retriever system.

This endpoint uses only the smart retriever to demonstrate:
- Automatic content discovery and routing
- Intelligent query analysis
- Context selection without manual configuration
"""

import asyncio
import logging
from typing import Annotated, Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from ..core.app_initializer_v2 import get_unified_retriever
from ..core.smart_query_handler import SmartQueryHandler
from ..dependencies import get_services, get_smart_handler, get_tenant_context
from ..models.request_models import Query

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/smart-query")
async def smart_query(
    query: Query,
    smart_handler: Annotated[SmartQueryHandler, Depends(get_smart_handler)],
    tenant_context: Annotated[dict, Depends(get_tenant_context)],
) -> JSONResponse:
    """
    Test endpoint for the smart retriever system.

    This endpoint demonstrates the unified retriever without manual configuration:
    - Analyzes query intent automatically
    - Routes to relevant content intelligently
    - Returns structured response with metadata
    """
    try:
        # Analyze the query intent (run in threadpool to avoid blocking event loop)
        intent_analysis = await asyncio.to_thread(smart_handler.analyze_query_with_llm, query.question)

        # Get relevant context using smart routing with tenant context (run in threadpool for LLM reranking)
        tenant_id = tenant_context.get("tenant_id")
        relevant_docs = await asyncio.to_thread(
            smart_handler.get_relevant_context,
            query.question,
            chat_history=[msg.dict() for msg in query.chat_history],
            max_context_length=4000,
            tenant_id=tenant_id,
        )

        # Prepare response
        response_data: Dict[str, Any] = {
            "query": query.question,
            "intent_analysis": intent_analysis,
            "documents_found": len(relevant_docs),
            "contexts": [],
            "smart_routing_info": {
                "routing_method": "automatic",
                "content_types_detected": intent_analysis.get("topics", []),
                "query_complexity": intent_analysis.get("complexity", "unknown"),
            },
        }

        # Add document contexts with metadata
        for i, doc in enumerate(relevant_docs):
            context_info = {
                "index": i + 1,
                "content": doc.page_content[:500] + "..." if len(doc.page_content) > 500 else doc.page_content,
                "metadata": {
                    "file_name": doc.metadata.get("file_name", "unknown"),
                    "file_type": doc.metadata.get("file_type", "unknown"),
                    "content_types": doc.metadata.get("content_types", ""),
                    "content_length": doc.metadata.get("content_length", 0),
                    "has_code": doc.metadata.get("has_code", False),
                },
            }
            response_data["contexts"].append(context_info)

        return JSONResponse(content=response_data)

    except Exception as e:
        logger.error(f"Smart query failed: {e}")
        raise HTTPException(status_code=500, detail=f"Smart query failed: {str(e)}")


@router.get("/smart-query/status")
async def smart_query_status(
    services: Annotated[Dict[str, Any], Depends(get_services)],
) -> Dict[str, Any]:
    """Check the status of the smart retriever system."""
    try:
        all_retrievers = services.get("retrievers")
        if not all_retrievers or not isinstance(all_retrievers, dict):
            return {"status": "unavailable", "message": "Retrievers not available"}
        unified_retriever = get_unified_retriever(all_retrievers)

        if not unified_retriever:
            return {"status": "unavailable", "message": "Unified retriever not initialized"}

        # Get some basic stats
        return {
            "status": "available",
            "retriever_type": "unified",
            "available_retrievers": list(all_retrievers.keys()),
            "smart_features": [
                "automatic_content_discovery",
                "intelligent_query_routing",
                "intent_analysis",
                "context_optimization",
            ],
        }

    except Exception as e:
        logger.error(f"Smart query status check failed: {e}")
        return {"status": "error", "message": str(e)}


@router.post("/smart-query/analyze")
async def analyze_query(
    query: Query,
    smart_handler: Annotated[SmartQueryHandler, Depends(get_smart_handler)],
) -> Dict[str, Any]:
    """Analyze a query without retrieving documents (for testing intent detection)."""
    try:
        # Run LLM analysis in threadpool to avoid blocking the event loop
        intent_analysis = await asyncio.to_thread(smart_handler.analyze_query_with_llm, query.question)

        return {
            "query": query.question,
            "analysis": intent_analysis,
            "routing_suggestions": {
                "recommended_approach": intent_analysis.get("suggested_approach"),
                "detected_topics": intent_analysis.get("topics", []),
                "estimated_complexity": intent_analysis.get("complexity"),
            },
        }

    except Exception as e:
        logger.error(f"Query analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Query analysis failed: {str(e)}")
