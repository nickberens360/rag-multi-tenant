"""
Pydantic models for admin API endpoints.
Migrated from admin/backend/models.py with improvements.
"""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1)


class LoginResponse(BaseModel):
    success: bool
    message: str
    user: Optional[Dict] = None
    session_id: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=128)


class UpdateDisplayNameRequest(BaseModel):
    display_name: str = Field(..., min_length=2, max_length=50, description="Display name for the user")


class UpdateEmailRequest(BaseModel):
    email: str = Field(..., pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", description="Valid email address")
    password: str = Field(..., min_length=1, description="Current password for verification")


class CreateUserRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8, max_length=128)
    email: Optional[str] = None
    role: str = Field(default="viewer", pattern="^(admin|viewer|owner)$")


# Admin dashboard models
class OverviewStats(BaseModel):
    total_queries: int = 0
    unique_sessions: int = 0
    avg_response_time_ms: float = 0.0
    error_rate: float = 0.0
    cache_hit_rate: float = 0.0
    helpful_rate: float = 0.0
    queries_today: int = 0
    queries_this_week: int = 0
    # Comparison data for percentage calculations
    total_queries_change: float = 0.0
    unique_sessions_change: float = 0.0
    avg_response_time_change: float = 0.0
    error_rate_change: float = 0.0
    cache_hit_rate_change: float = 0.0
    helpful_rate_change: float = 0.0


class QueryResponse(BaseModel):
    queries: List[Dict]
    total: int
    limit: int
    offset: int


class FeedbackUpdate(BaseModel):
    feedback: str = Field(..., max_length=1000)


# Knowledge base models
class FileContentUpdate(BaseModel):
    content: str = Field(..., max_length=1000000)  # 1MB limit


# Performance models
class PerformanceMetric(BaseModel):
    current: float
    previous: float
    change: float


class PerformanceMetrics(BaseModel):
    response_time: PerformanceMetric
    throughput: PerformanceMetric
    error_rate: PerformanceMetric
    cache_hit_rate: PerformanceMetric


# Session models
class SessionInfo(BaseModel):
    session_id: str
    user_id: int
    username: str
    started_at: datetime
    last_active_at: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    is_active: bool


# Content models
class ContentGap(BaseModel):
    id: int
    pattern: str
    count: int
    avg_score: float
    first_seen: datetime
    last_seen: datetime
    resolved: bool
    notes: Optional[str] = None
    sample_query: Optional[str] = None


# Follow-up category models
class FollowupCategory(BaseModel):
    id: int
    name: str
    display_name: str
    description: Optional[str] = None
    icon: str = "help-circle"
    sort_order: int = 0
    is_active: bool = True
    created_at: datetime
    updated_at: datetime


class CreateFollowupCategoryRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=50, pattern="^[a-z_][a-z0-9_]*$")
    display_name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    icon: str = Field(default="help-circle", max_length=50)
    sort_order: int = Field(default=0, ge=0, le=1000)


class UpdateFollowupCategoryRequest(BaseModel):
    display_name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    icon: Optional[str] = Field(None, max_length=50)
    sort_order: Optional[int] = Field(None, ge=0, le=1000)
    is_active: Optional[bool] = None


class ReorderCategoriesRequest(BaseModel):
    categories: List[Dict[str, int]] = Field(..., description="List of {id: int, sort_order: int}")


# Follow-up question models (normalized)
class FollowupQuestion(BaseModel):
    id: int
    category_id: int
    question_text: str
    sort_order: int = 0
    is_active: bool = True
    created_at: datetime
    updated_at: datetime
    created_by: Optional[int] = None
    category_name: Optional[str] = None
    category_display_name: Optional[str] = None


class CreateFollowupQuestionRequest(BaseModel):
    category_id: int = Field(..., gt=0)
    question_text: str = Field(..., min_length=1, max_length=500)
    sort_order: Optional[int] = Field(None, ge=0, le=1000)


class UpdateFollowupQuestionRequest(BaseModel):
    question_text: Optional[str] = Field(None, min_length=1, max_length=500)
    sort_order: Optional[int] = Field(None, ge=0, le=1000)
    is_active: Optional[bool] = None


class BulkQuestionOperation(BaseModel):
    action: str = Field(..., pattern="^(delete|activate|deactivate|update)$")
    question_id: int = Field(..., gt=0)
    question_text: Optional[str] = Field(None, max_length=500)
    sort_order: Optional[int] = Field(None, ge=0, le=1000)


class BulkQuestionRequest(BaseModel):
    operations: List[BulkQuestionOperation] = Field(..., min_length=1, max_length=50)


class CategoryDeleteRequest(BaseModel):
    strategy: str = Field(..., pattern="^(move|delete|deactivate)$")
    target_category_id: Optional[int] = Field(None, gt=0)


class QuestionSearchRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=100)
    category_id: Optional[int] = Field(None, gt=0)
    limit: int = Field(default=20, ge=1, le=50)


class CategoryWithStats(BaseModel):
    id: int
    name: str
    display_name: str
    description: Optional[str] = None
    icon: str = "help-circle"
    sort_order: int = 0
    is_active: bool = True
    created_at: datetime
    updated_at: datetime
    questions_count: int = 0
    questions: Optional[List[FollowupQuestion]] = None


# Welcome question models
class WelcomeQuestion(BaseModel):
    id: int
    question_text: str
    sort_order: int = 0
    is_active: bool = True
    created_at: datetime
    updated_at: datetime
    created_by: Optional[int] = None


class CreateWelcomeQuestionRequest(BaseModel):
    question_text: str = Field(..., min_length=1, max_length=500)
    sort_order: Optional[int] = Field(None, ge=0, le=1000)


class UpdateWelcomeQuestionRequest(BaseModel):
    question_text: Optional[str] = Field(None, min_length=1, max_length=500)
    sort_order: Optional[int] = Field(None, ge=0, le=1000)
    is_active: Optional[bool] = None


# Export models
class ExportRequest(BaseModel):
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    format: str = Field(default="csv", pattern="^(csv|json|xlsx)$")
    include_responses: bool = False


# API Response models
class SuccessResponse(BaseModel):
    success: bool = True
    message: str
    data: Optional[Dict] = None


class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    error_code: Optional[str] = None
    details: Optional[Dict] = None


# Health check model
class HealthCheck(BaseModel):
    status: str
    timestamp: datetime
    services: Optional[Dict[str, str]] = None
    version: Optional[str] = None


# Settings models
class AdminSetting(BaseModel):
    setting_key: str
    setting_value: str
    updated_at: datetime
    updated_by: int


class UpdateSettingRequest(BaseModel):
    setting_value: str = Field(..., max_length=1000)


# User management models
class AdminUser(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    role: str
    is_active: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None
    updated_at: datetime


class UpdateUserRequest(BaseModel):
    email: Optional[str] = None
    role: Optional[str] = Field(None, pattern="^(admin|viewer|owner)$")
    is_active: Optional[bool] = None


class BulkDeleteUsersRequest(BaseModel):
    user_ids: List[int] = Field(..., min_length=1, max_length=50, description="List of user IDs to delete")


class BulkDeactivateUsersRequest(BaseModel):
    user_ids: List[int] = Field(..., min_length=1, max_length=50, description="List of user IDs to deactivate")
