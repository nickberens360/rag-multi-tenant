"""
Common response schemas and error models for OpenAPI documentation.

This module provides reusable response schemas that can be used across
multiple endpoints to ensure consistent API documentation.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Standard error response format."""

    detail: str = Field(
        ...,
        description="Human-readable error message describing what went wrong",
        examples=[
            "Rate limit exceeded: 100/minute",
            "Invalid username or password",
            "Query contains potentially unsafe content",
            "An error occurred while processing your request",
        ],
    )


class ValidationErrorResponse(BaseModel):
    """Detailed validation error response."""

    detail: List[Dict[str, Any]] = Field(
        ...,
        description="List of validation errors with field locations and messages",
        examples=[
            [
                {"loc": ["body", "question"], "msg": "field required", "type": "value_error.missing"},
                {
                    "loc": ["body", "chat_history", 0, "text"],
                    "msg": "ensure this value has at most 1000 characters",
                    "type": "value_error.any_str.max_length",
                    "ctx": {"limit_value": 1000},
                },
            ]
        ],
    )


class RateLimitResponse(BaseModel):
    """Rate limit exceeded response."""

    detail: str = Field(
        default="Rate limit exceeded", description="Rate limit error message with current limit information"
    )
    retry_after: Optional[int] = Field(None, description="Seconds to wait before retrying the request")


class HealthResponse(BaseModel):
    """Health check response format."""

    status: str = Field(..., description="Application health status", examples=["healthy", "degraded", "initializing"])
    illustration_count: Optional[int] = Field(None, description="Number of illustrations available in the system")
    timestamp: Optional[float] = Field(None, description="Unix timestamp when status was generated")


class StatusResponse(BaseModel):
    """Detailed system status response."""

    status: str = Field(..., description="Overall system status", examples=["online", "degraded", "maintenance"])
    timestamp: float = Field(..., description="Unix timestamp when status was generated")
    primary_llm: str = Field(..., description="Primary AI model being used", examples=["claude", "gemini"])
    app_initialized: bool = Field(..., description="Whether the application has fully initialized")
    rate_limits: Dict[str, bool] = Field(
        ...,
        description="Rate limit status for each AI provider (true = rate limited)",
        examples=[{"claude": False, "gemini": False}, {"claude": True, "gemini": False}],
    )


class RateLimitStatusResponse(BaseModel):
    """AI model rate limit status response."""

    rate_limits: Dict[str, bool] = Field(
        ...,
        description="Rate limit status for each AI model (true = currently rate limited)",
        examples=[{"claude": False, "gemini": False}, {"claude": True, "gemini": False}],
    )


# Common response examples for reuse across endpoints
COMMON_ERROR_RESPONSES = {
    400: {
        "description": "Bad Request - Invalid input or validation failed",
        "model": ErrorResponse,
        "content": {
            "application/json": {
                "examples": {
                    "validation_error": {
                        "summary": "Input validation failed",
                        "value": {"detail": "Query contains potentially unsafe content"},
                    },
                    "missing_field": {
                        "summary": "Required field missing",
                        "value": {"detail": "Question cannot be empty"},
                    },
                }
            }
        },
    },
    401: {
        "description": "Unauthorized - Authentication required",
        "model": ErrorResponse,
        "content": {
            "application/json": {
                "examples": {
                    "not_authenticated": {
                        "summary": "No valid session",
                        "value": {"detail": "Authentication required"},
                    },
                    "session_expired": {
                        "summary": "Session has expired",
                        "value": {"detail": "Session expired. Please log in again."},
                    },
                }
            }
        },
    },
    403: {
        "description": "Forbidden - Insufficient permissions",
        "model": ErrorResponse,
        "content": {
            "application/json": {
                "examples": {
                    "insufficient_permissions": {
                        "summary": "User lacks required permissions",
                        "value": {"detail": "Admin access required"},
                    },
                    "role_required": {
                        "summary": "Specific role required",
                        "value": {"detail": "Administrator role required for this action"},
                    },
                }
            }
        },
    },
    422: {"description": "Unprocessable Entity - Validation error", "model": ValidationErrorResponse},
    429: {
        "description": "Too Many Requests - Rate limit exceeded",
        "model": RateLimitResponse,
        "content": {
            "application/json": {
                "examples": {
                    "rate_limited": {
                        "summary": "Rate limit exceeded",
                        "value": {"detail": "Rate limit exceeded: 100/minute", "retry_after": 60},
                    }
                }
            }
        },
    },
    500: {
        "description": "Internal Server Error - Unexpected server error",
        "model": ErrorResponse,
        "content": {
            "application/json": {
                "examples": {
                    "server_error": {
                        "summary": "Unexpected server error",
                        "value": {"detail": "An error occurred while processing your request"},
                    },
                    "service_unavailable": {
                        "summary": "External service unavailable",
                        "value": {"detail": "AI service temporarily unavailable"},
                    },
                }
            }
        },
    },
}
