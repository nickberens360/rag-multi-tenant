"""
Main query endpoint for handling user questions and requests.

This module contains the primary query endpoint that:
- Validates and sanitizes user input
- Routes queries to appropriate handlers (images vs text)
- Handles streaming responses for AI text generation
- Applies rate limiting and security validation
- Manages LLM rate limit status and fallback
"""

import json
import logging
import os as _os
import time
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from ..core.config_v2 import AppConfig
from ..core.llm_chain import get_rate_limit_status, stream_with_fallback
from ..core.query_logger import get_query_logger
from ..core.query_router import QueryType
from ..dependencies import get_services, get_tenant_context
from ..models.request_models import Query
from ..security.validator import SecurityValidator

# Initialize router and logger
router = APIRouter()
logger = logging.getLogger(__name__)


def get_success_message_template(found_images: bool, query_type: QueryType, fell_back_to_all: bool) -> str:
    """Get appropriate success message template based on query results."""
    if found_images:
        if query_type == QueryType.ALL_IMAGES or fell_back_to_all:
            return "Here are some of my illustrations:"
        else:
            return "Here are the illustrations I found for '{}':"
    else:
        return "Sorry, no illustrations found for '{}'."


# Build a test-aware rate limit decorator
_testing = _os.getenv("TESTING", "false").lower() == "true" or "PYTEST_CURRENT_TEST" in _os.environ
_rate_limit_decorator = (lambda f: f) if _testing else (lambda f: f)


@router.post(
    "/query",
    tags=["Query"],
    summary="AI-Powered Knowledge Query",
    description="""
            **Primary endpoint for querying Nick's knowledge base using AI.**
            
            This endpoint uses advanced RAG (Retrieval-Augmented Generation) with Claude to provide intelligent responses about:
            - Nick's professional experience and skills
            - Technical projects and implementations  
            - Creative work and illustrations
            - Personal interests and background
            
            **Features:**
            - Smart query routing (determines if you're asking about illustrations vs. text content)
            - Streaming responses for real-time AI generation
            - Rate limiting protection
            - Comprehensive input validation and sanitization
            - Fallback handling for LLM rate limits
            
            **Rate Limits:** {rate_limit} requests per minute per IP
            """.format(
        rate_limit=AppConfig.get_rate_limit().split("/")[0]
    ),
    response_description="Intelligent response based on Nick's knowledge base, with optional illustration results",
    responses={
        200: {
            "description": "Successful response with AI-generated answer",
            "content": {
                "application/json": {
                    "examples": {
                        "text_query": {
                            "summary": "Text-based question about Nick's experience",
                            "value": {
                                "answer": (
                                    "Nick Berens is a Senior Software Engineer with expertise in full-stack "
                                    "development, particularly in Vue.js, Python, and API design. He has worked "
                                    "with companies like Calendly, where he focused on scaling user experiences "
                                    "and implementing robust backend systems."
                                ),
                                "images": [],
                                "model_used": "claude-3-5-sonnet-20241022",
                                "followup_questions": [
                                    "What specific projects has Nick worked on at Calendly?",
                                    "What technologies does Nick prefer for frontend development?",
                                ],
                            },
                        },
                        "illustration_query": {
                            "summary": "Query requesting Nick's artwork/illustrations",
                            "value": {
                                "answer": "Here are some of my illustrations:",
                                "images": [
                                    {
                                        "file": "flying-robot.png",
                                        "title": "Flying Robot",
                                        "tags": ["robot", "flying", "futuristic"],
                                    },
                                    {
                                        "file": "dope-goose.jpg",
                                        "title": "Dope Goose",
                                        "tags": ["animal", "bird", "cartoon"],
                                    },
                                ],
                                "model_used": "claude-3-5-sonnet-20241022",
                                "followup_questions": [
                                    "Can you show me more animal illustrations?",
                                    "What tools do you use for digital art?",
                                ],
                            },
                        },
                    }
                }
            },
        },
        400: {
            "description": "Bad Request - Invalid input or security validation failed",
            "content": {
                "application/json": {
                    "examples": {
                        "validation_error": {
                            "summary": "Input validation failed",
                            "value": {"detail": "Query contains potentially unsafe content"},
                        },
                        "empty_query": {
                            "summary": "Empty or missing question",
                            "value": {"detail": "Question cannot be empty"},
                        },
                    }
                }
            },
        },
        429: {
            "description": "Too Many Requests - Rate limit exceeded",
            "content": {"application/json": {"example": {"detail": "Rate limit exceeded: 100/minute"}}},
        },
        500: {
            "description": "Internal Server Error",
            "content": {"application/json": {"example": {"detail": "An error occurred while processing your request"}}},
        },
    },
)
async def query_endpoint(
    request: Request,
    query: Query,
    services: dict = Depends(get_services),
    tenant_context: dict = Depends(get_tenant_context),
):
    from slowapi.util import get_remote_address

    # Get client IP and query logger
    client_ip = get_remote_address(request)

    # Check for proxy headers to get the real client IP.
    # Note: This assumes the service is behind a trusted proxy.
    forwarded_for = request.headers.get("X-Forwarded-For")
    real_ip = request.headers.get("X-Real-IP")

    if forwarded_for:
        # Use the first IP in the chain (original client)
        client_ip = forwarded_for.split(",")[0].strip()
    elif real_ip:
        client_ip = real_ip.strip()

    query_logger = get_query_logger()
    request_id = str(uuid.uuid4())
    start_time = time.time()

    # Restore validation and sanitization calls
    is_valid, error_msg = SecurityValidator.validate_query(query, client_ip)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)

    sanitized_question = SecurityValidator.sanitize_input(query.question)

    # Sanitize chat history as well
    sanitized_history = [
        {"sender": msg.sender, "text": SecurityValidator.sanitize_input(msg.text)} for msg in query.chat_history
    ]

    # Validate query router service is available
    query_router = services.get("query_router")
    if query_router is None:
        raise HTTPException(status_code=500, detail="Query router service is not initialized")

    query_type, search_term = query_router.route_query(sanitized_question.lower().strip())

    # Handle image queries
    if query_type != QueryType.AI_TEXT_RESPONSE:
        illustration_service = services.get("illustration_service")
        fell_back_to_all = False
        if illustration_service is None:
            found_images = []
            logger.warning("Illustration service not available - returning empty results")
        else:
            if query_type == QueryType.ALL_IMAGES:
                found_images = illustration_service.get_all()
            else:
                found_images = illustration_service.search(search_term)
                # Fallback to showing all illustrations if search returns no results
                if not found_images:
                    logger.info(
                        f"No specific illustrations found for '{search_term}', falling back to all illustrations"
                    )
                    found_images = illustration_service.get_all()
                    fell_back_to_all = True

        # Update the response message based on whether we found specific results or fell back to all
        success_message_template = get_success_message_template(bool(found_images), query_type, fell_back_to_all)

        followup_service = services.get("followup_service")
        followup_questions = (
            followup_service.generate_followups(
                sanitized_question, success_message_template.format(search_term), sanitized_history
            )
            if followup_service
            else []
        )

        response_service = services.get("response_service")
        if response_service is None:
            logger.error("Response service not available - cannot build image response")
            raise HTTPException(status_code=503, detail="Image service temporarily unavailable")

        response_data = response_service.build_image_response(
            search_term, found_images, start_time, followup_questions, success_message_template
        )

        # Add rate limit status to image responses too
        rate_limits = get_rate_limit_status()
        response_dict = response_data.model_dump()
        response_dict["rate_limits"] = rate_limits

        # Log the image query
        response_time = time.time() - start_time
        query_logger.log_query(
            client_ip=client_ip,
            question=sanitized_question,
            response=(
                success_message_template.format(search_term)
                if "{}" in success_message_template
                else success_message_template
            ),
            model_used="image_search",
            query_type="image",
            response_time=response_time,
            metadata={
                "search_term": search_term,
                "images_found": len(found_images),
                "query_type_enum": query_type.value,
                "fell_back_to_all": fell_back_to_all,
            },
        )

        return JSONResponse(content=response_dict)

    # Handle AI text responses using smart retriever
    formatted_chat_history: List[BaseMessage] = [
        (HumanMessage(content=msg["text"]) if msg["sender"] == "user" else AIMessage(content=msg["text"]))
        for msg in sanitized_history
    ]

    # Get current rate limit status before processing
    current_rate_limits = get_rate_limit_status()

    # If user's preferred model is rate limited, log a warning and let the system fallback
    if query.preferred_model and current_rate_limits.get(query.preferred_model, False):
        logger.warning(
            f"User requested {query.preferred_model} but it's rate limited. Will fallback to available model."
        )

    # Use the enhanced retriever system (now with smart routing built-in)
    try:
        # Log smart routing info for debugging if unified retriever is available
        from ..core.app_initializer_v2 import get_unified_retriever
        from ..core.smart_query_handler import SmartQueryHandler

        unified_retriever = get_unified_retriever(services["retrievers"])
        if unified_retriever:
            llm = request.app.state.llm
            if not llm:
                logger.error("LLM not initialized, skipping smart query analysis.")
            else:
                smart_handler = SmartQueryHandler(unified_retriever, llm, use_fast_classifier=True)
                intent_analysis = smart_handler.analyze_query_fast(sanitized_question)
                logger.info(
                    f"Smart routing: Query '{sanitized_question}' -> Topics: "
                    f"{intent_analysis.get('topics', [])} | Complexity: {intent_analysis.get('complexity')}"
                )

        # Generate followup questions before streaming
        followup_service = services.get("followup_service")
        followup_questions = (
            followup_service.generate_followups(sanitized_question, "", sanitized_history) if followup_service else []
        )

        text_stream, actual_model_used, metadata = await stream_with_fallback(
            services["retrievers"],
            formatted_chat_history,
            sanitized_question,
            query.preferred_model,
            client_ip=client_ip,
            question=sanitized_question,
            request_id=request_id,
            start_time=start_time,
            tenant_id=tenant_context.get("tenant_id"),
            additional_metadata={
                "preferred_model": query.preferred_model,
                "chat_history_length": len(sanitized_history),
                "followup_questions": followup_questions,
                "tenant_id": tenant_context.get("tenant_id"),
                "tenant_slug": tenant_context.get("tenant_slug"),
            },
        )

        # If we get here, the LLM fallback succeeded, so return 200
    except Exception as e:
        # Only return 503 if both retrievers and LLM fallback fail
        logger.error(f"Both retrievers and LLM fallback failed: {e}")
        raise HTTPException(status_code=503, detail="AI service temporarily unavailable")

    # Note: Full response logging now happens in llm_chain.py after streaming completes
    # This eliminates duplicate logging and ensures we capture complete responses

    # Include rate limit status in headers
    headers = {
        "X-Model-Used": actual_model_used,
        "X-Followup-Questions": json.dumps(followup_questions),
        "X-Rate-Limits": json.dumps(metadata.get("rate_limit_status", {})),
    }

    return StreamingResponse(text_stream, media_type="text/plain", headers=headers)


@router.get(
    "/default-model",
    tags=["Query"],
    summary="Get Default Model Setting",
    response_description="Returns the configured default model for responses",
)
async def get_default_model():
    """
    Get the default response model from admin settings.

    This endpoint allows the frontend to initialize with the correct
    default model as configured by the admin, while still allowing
    per-session user overrides.
    """
    try:
        # Prefer database-backed settings via SettingsManager
        from ..core.settings_manager import get_settings_manager

        sm = get_settings_manager()
        default_model = sm.get_response_llm() or "claude"
        return {"default_model": default_model, "available_models": ["claude", "gemini"]}
    except Exception as e:
        logger.error(f"Error getting default model setting: {e}")
        return {"default_model": "claude", "available_models": ["claude", "gemini"]}
