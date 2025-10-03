"""
Comprehensive admin routes for the main backend.
Migrated from admin/backend/routes.py with full functionality.
"""

import csv
import io
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, Response, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..core import taxonomy_loader
from ..core.admin_auth import admin_auth_manager, require_admin_auth, require_admin_role

# from ..core.admin_database import admin_db_manager  # deprecated: SQLite path
from ..core.api_key_manager import api_key_manager
from ..core.audit_logger import AuditAction, AuditLogger, audit_logger
from ..core.config_v2 import AppConfig
from ..core.date_utils import parse_time_range
from ..core.db_session import get_db_session
from ..core.settings_manager import get_settings_manager
from ..core.settings_schemas import (
    CoreSettings,
    FeatureFlags,
    FollowUpSettings,
    KnowledgeSettings,
    QueryRoutingSettings,
    RagConfigurationSettings,
    ResponseSettings,
    SearchRetrievalSettings,
    SecuritySettings,
    SystemConfigurationSettings,
    UXSettings,
)
from ..models.admin_models import (
    AdminUser,
    BulkDeactivateUsersRequest,
    BulkDeleteUsersRequest,
    BulkQuestionRequest,
    CategoryDeleteRequest,
    ChangePasswordRequest,
    CreateFollowupCategoryRequest,
    CreateFollowupQuestionRequest,
    CreateUserRequest,
    CreateWelcomeQuestionRequest,
    FeedbackUpdate,
    LoginRequest,
    LoginResponse,
    OverviewStats,
    QueryResponse,
    UpdateDisplayNameRequest,
    UpdateEmailRequest,
    UpdateFollowupCategoryRequest,
    UpdateFollowupQuestionRequest,
    UpdateWelcomeQuestionRequest,
)

# CSRF protection removed - session-based auth is inherently CSRF-resistant for our use case


logger = logging.getLogger(__name__)

# Initialize audit logger
audit_logger = AuditLogger()


router = APIRouter()


# Authentication endpoints
@router.get("/ping", tags=["Admin Authentication"], summary="Lightweight ping for admin API")
async def admin_ping() -> Dict[str, Any]:
    """Simple ping endpoint that does not touch the database.

    Useful to verify routing/middleware without exercising DB access.
    """
    return {"ok": True}


@router.post(
    "/auth/login",
    tags=["Admin Authentication"],
    response_model=LoginResponse,
    summary="Admin Login",
    description="""
            **Authenticate admin user and create secure session.**
            
            **Authentication Flow:**
            1. Submit username and password
            2. System validates credentials and checks rate limits
            3. On success: secure HTTPOnly cookie is set (`admin_session`)
            4. Use this cookie for subsequent admin API calls
            
            **Security Features:**
            - Rate limiting per IP address
            - Secure session management with HTTPOnly cookies
            - Audit logging of all login attempts
            - Password validation and security checks
            - Session fingerprinting for additional security
            
            **Session Management:**
            - Session expires in 24 hours
            - HTTPOnly cookie prevents XSS attacks
            - Secure flag enabled in production (HTTPS)
            - SameSite=Lax for CSRF protection
            
            **Next Steps After Login:**
            1. Cookie is automatically included in browser requests
            2. Access admin endpoints like `/api/admin/stats/overview`
            3. Use `/api/admin/auth/me` to verify current session
            """,
    responses={
        200: {
            "description": "Login successful - session cookie set",
            "content": {
                "application/json": {
                    "examples": {
                        "successful_login": {
                            "summary": "Successful admin login",
                            "value": {
                                "success": True,
                                "message": "Login successful",
                                "user": {
                                    "id": 1,
                                    "username": "admin",
                                    "role": "admin",
                                    "created_at": "2024-01-01T00:00:00Z",
                                    "last_login": "2024-09-02T17:00:00Z",
                                },
                            },
                        },
                        "invalid_credentials": {
                            "summary": "Invalid login credentials",
                            "value": {"success": False, "message": "Invalid username or password"},
                        },
                        "missing_fields": {
                            "summary": "Missing required fields",
                            "value": {"success": False, "message": "Username and password are required"},
                        },
                    }
                }
            },
            "headers": {
                "Set-Cookie": {
                    "description": "Secure session cookie for admin authentication",
                    "schema": {"type": "string"},
                    "example": "admin_session=abc123...; HttpOnly; Secure; SameSite=Lax; Max-Age=86400",
                }
            },
        }
    },
)
async def login(login_data: LoginRequest, request: Request, response: Response) -> LoginResponse:
    """Authenticate user and create session with rate limiting and security checks."""
    try:
        # Basic rate limiting check (in production, use Redis or similar)
        client_ip = request.client.host if request.client else "unknown"

        # Validate input
        if not login_data.username.strip() or not login_data.password:
            return LoginResponse(success=False, message="Username and password are required")
        user_agent = request.headers.get("User-Agent", "")

        auth_result = admin_auth_manager.authenticate_user(
            login_data.username, login_data.password, ip_address=client_ip, user_agent=user_agent
        )

        if not auth_result:
            logger.warning(f"Failed login attempt for username: {login_data.username} from IP: {client_ip}")

            # Audit log failed login
            from ..core.audit_logger import audit_logger

            audit_logger.log_login(
                login_data.username, client_ip, user_agent, success=False, error_message="Invalid credentials"
            )

            return LoginResponse(success=False, message="Invalid username or password")

        user_data = auth_result["user"].copy()
        user_data.pop("password_hash", None)  # Remove password hash from response

        # Set secure HTTPOnly session cookie
        # Detect HTTPS even when behind a proxy and choose SameSite based on cross-site usage
        forwarded_proto = request.headers.get("x-forwarded-proto", "").lower()
        is_https = request.url.scheme == "https" or forwarded_proto == "https"

        # Determine same-site vs cross-site more accurately, treating localhost/127.0.0.1 as same-site.
        # Default to same-site when Origin header is missing (typical for same-origin requests).
        origin = request.headers.get("origin")
        is_cross_site = False
        if origin:
            try:
                from urllib.parse import urlparse

                origin_url = urlparse(origin)
                origin_host = origin_url.hostname
                request_host = request.url.hostname

                def _is_local(host: Optional[str]) -> bool:
                    return host in {"localhost", "127.0.0.1"}

                # Schemeful same-site: hostnames equal OR both local, and schemes equal
                is_same_host = bool(origin_host and request_host and origin_host == request_host)
                is_both_local = _is_local(origin_host) and _is_local(request_host)
                is_same_scheme = origin_url.scheme == request.url.scheme

                is_cross_site = not ((is_same_host or is_both_local) and is_same_scheme)
            except Exception:
                is_cross_site = False

        # Avoid invalid SameSite=None without Secure (browsers will reject). Fallback to Lax in that case.
        cookie_samesite = "none" if (is_cross_site and is_https) else "lax"

        response.set_cookie(
            key="admin_session",
            value=auth_result["session_id"],
            max_age=24 * 60 * 60,  # 24 hours
            httponly=True,  # Always HTTPOnly for security
            secure=is_https,  # Secure when request is HTTPS or forwarded as HTTPS
            samesite=cookie_samesite,  # Allow cross-site cookies only when needed
            path="/",
        )

        # Audit log successful login
        from ..core.audit_logger import audit_logger

        audit_logger.log_login(login_data.username, client_ip, user_agent, success=True, method="password")

        return LoginResponse(
            success=True, message="Login successful", user=user_data, session_id=auth_result["session_id"]
        )

    except Exception as e:
        logger.error(f"Login error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Login failed")


@router.post("/auth/logout")
async def logout(
    request: Request, response: Response, session: Dict[str, Any] = Depends(require_admin_auth)
) -> Dict[str, Any]:
    """Logout user and expire session securely."""
    try:
        session_id = request.cookies.get("admin_session")
        if session_id:
            admin_auth_manager.expire_session(session_id)

        # Clear session cookie with attributes matching how it was set
        forwarded_proto = request.headers.get("x-forwarded-proto", "").lower()
        is_https = request.url.scheme == "https" or forwarded_proto == "https"
        origin = request.headers.get("origin")
        is_cross_site = False
        if origin:
            try:
                from urllib.parse import urlparse

                origin_url = urlparse(origin)
                origin_host = origin_url.hostname
                request_host = request.url.hostname

                def _is_local(host: Optional[str]) -> bool:
                    return host in {"localhost", "127.0.0.1"}

                is_same_host = bool(origin_host and request_host and origin_host == request_host)
                is_both_local = _is_local(origin_host) and _is_local(request_host)
                is_same_scheme = origin_url.scheme == request.url.scheme

                is_cross_site = not ((is_same_host or is_both_local) and is_same_scheme)
            except Exception:
                is_cross_site = False
        cookie_samesite = "none" if (is_cross_site and is_https) else "lax"

        response.delete_cookie(key="admin_session", secure=is_https, samesite=cookie_samesite, path="/")

        # Audit log logout
        from ..core.audit_logger import audit_logger

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")
        audit_logger.log_logout(session["username"], client_ip, user_agent)

        return {"success": True, "message": "Logout successful"}

    except Exception as e:
        logger.error(f"Logout error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Logout failed")


@router.get("/auth/me")
async def get_current_user_info(
    session: Dict[str, Any] = Depends(require_admin_auth),
    db: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    """Get current authenticated user information (excluding sensitive data)."""
    try:
        row = db.execute(
            text(
                """
                SELECT id, username, email, role, is_active, last_login_at, created_at, updated_at, display_name
                FROM admin_users WHERE id = :uid
                """
            ),
            {"uid": session["user_id"]},
        ).first()

        user_data = {
            "id": session["user_id"],
            "username": session["username"],
            "email": row[2] if row else session.get("email"),
            "display_name": row[8] if row else None,
            "role": row[3] if row else session.get("role"),
            "last_login_at": row[5].isoformat() if row and row[5] else session.get("last_login_at"),
        }
        return {"user": user_data}
    except Exception as e:
        logger.error(f"Error loading current user info: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to load user info")


@router.post("/auth/change-password")
async def change_password(
    password_data: ChangePasswordRequest,
    request: Request,
    session: Dict[str, Any] = Depends(require_admin_auth),
    db: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    """Change the current user's password with enhanced security and rate limiting."""
    try:
        # Rate limiting for password change attempts
        client_ip = request.client.host if request.client else "unknown"
        if admin_auth_manager.is_rate_limited(client_ip, "ip"):
            logger.warning(f"Rate limited password change attempt from {client_ip} for user {session['username']}")
            raise HTTPException(status_code=429, detail="Too many password change attempts. Please try again later.")

        # Get the current user from Postgres
        row = db.execute(
            text("SELECT id, username, password_hash FROM admin_users WHERE id = :uid AND is_active = true"),
            {"uid": session["user_id"]},
        ).first()
        if not row:
            raise HTTPException(status_code=404, detail="User not found")

        # Verify current password
        if not admin_auth_manager.verify_password(password_data.current_password, row[2]):
            # Record failed password verification attempt
            admin_auth_manager.record_rate_limit_attempt(client_ip, "ip", 5)
            logger.warning(f"Invalid current password attempt for user: {session['username']} from IP: {client_ip}")
            # Audit failure
            audit_logger.log_action(
                action=AuditAction.PASSWORD_CHANGE,
                username=session["username"],
                details={"reason": "invalid_current_password"},
                ip_address=client_ip,
                user_agent=request.headers.get("User-Agent", ""),
                success=False,
                error_message="Invalid current password",
            )
            raise HTTPException(status_code=400, detail="Current password is incorrect")

        # Validate new password using centralized validation
        try:
            admin_auth_manager.validate_password_strength(password_data.new_password)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        # Hash and update the new password in Postgres
        new_password_hash = admin_auth_manager.hash_password(password_data.new_password)
        res = db.execute(
            text("UPDATE admin_users SET password_hash = :ph, updated_at = now() WHERE id = :uid"),
            {"ph": new_password_hash, "uid": row[0]},
        )
        if (res.rowcount or 0) == 0:
            raise HTTPException(status_code=500, detail="Failed to update password")

        # Reset failed attempts on successful password change (hide DB details behind manager)
        try:
            admin_auth_manager.reset_user_rate_limits(session["username"], client_ip)
        except Exception:
            pass

        # Audit log password change
        from ..core.audit_logger import audit_logger

        audit_logger.log_password_change(
            session["username"], session["username"], client_ip, request.headers.get("User-Agent", ""), success=True
        )

        # SECURITY FIX: Force complete re-authentication after password change
        # This prevents session fixation attacks
        admin_auth_manager.expire_user_sessions(row[0])

        # Force logout by clearing the current session cookie
        response = JSONResponse({"success": True, "message": "Password changed successfully. Please log in again."})
        # Match cookie attributes to ensure clients clear it correctly
        forwarded_proto = request.headers.get("x-forwarded-proto", "").lower()
        is_https = request.url.scheme == "https" or forwarded_proto == "https"
        origin = request.headers.get("origin")
        is_cross_site = False
        if origin:
            try:
                from urllib.parse import urlparse

                origin_url = urlparse(origin)
                origin_host = origin_url.hostname
                request_host = request.url.hostname

                def _is_local(host: Optional[str]) -> bool:
                    return host in {"localhost", "127.0.0.1"}

                is_same_host = bool(origin_host and request_host and origin_host == request_host)
                is_both_local = _is_local(origin_host) and _is_local(request_host)
                is_same_scheme = origin_url.scheme == request.url.scheme

                is_cross_site = not ((is_same_host or is_both_local) and is_same_scheme)
            except Exception:
                is_cross_site = False
        cookie_samesite = "none" if (is_cross_site and is_https) else "lax"

        response.delete_cookie("admin_session", path="/", httponly=True, secure=is_https, samesite=cookie_samesite)
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password change error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to change password")


@router.post("/auth/create-user")
async def create_user(
    request: Request,
    user_data: CreateUserRequest,
    session: Dict[str, Any] = Depends(require_admin_role),
    db: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    """Create a new admin user (admin only) with validation and add to current tenant."""
    try:
        # Get tenant context from middleware
        tenant_id = getattr(request.state, "tenant_id", None)
        tenant_slug = getattr(request.state, "tenant_slug", None)

        if not tenant_id:
            raise HTTPException(status_code=400, detail="Tenant context not available")

        # Check if username already exists (Postgres)
        exists = db.execute(
            text("SELECT 1 FROM admin_users WHERE username = :un"), {"un": user_data.username.lower()}
        ).first()
        if exists:
            raise HTTPException(status_code=400, detail="Username already exists")

        user_id = admin_auth_manager.create_admin_user(
            username=user_data.username, password=user_data.password, email=user_data.email, role=user_data.role
        )

        # Add user to current tenant's memberships
        db.execute(
            text(
                """
                INSERT INTO tenant_memberships (tenant_id, user_id, role, created_at)
                VALUES (:tenant_id, :user_id, :role, NOW())
                ON CONFLICT (tenant_id, user_id) DO NOTHING
                """
            ),
            {"tenant_id": tenant_id, "user_id": user_id, "role": user_data.role or "viewer"},
        )
        db.commit()

        logger.info(
            f"User '{user_data.username}' (ID: {user_id}) created and added to tenant {tenant_slug} (ID: {tenant_id})"
        )

        return {"success": True, "message": f"User '{user_data.username}' created successfully", "user_id": user_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create user error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create user")


# User profile endpoints
@router.put("/user/display-name")
async def update_display_name(
    request_data: UpdateDisplayNameRequest,
    session: Dict[str, Any] = Depends(require_admin_auth),
    db: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    """Update current user's display name."""
    try:
        user_id = session["user_id"]
        res = db.execute(
            text("UPDATE admin_users SET display_name = :dn, updated_at = now() WHERE id = :id"),
            {"dn": request_data.display_name, "id": user_id},
        )

        if (res.rowcount or 0) > 0:
            audit_logger.log_action(
                action=AuditAction.USER_UPDATE,
                username=session["username"],
                details={"field": "display_name", "new_value": request_data.display_name},
            )
            return {"success": True, "message": "Display name updated successfully"}
        else:
            raise HTTPException(status_code=400, detail="Failed to update display name")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Display name update error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update display name")


@router.put("/user/email")
async def update_email(
    request_data: UpdateEmailRequest,
    session: Dict[str, Any] = Depends(require_admin_auth),
    db: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    """Update current user's email address with password verification."""
    try:
        user_id = session["user_id"]

        # Verify current password against Postgres hash
        row = db.execute(text("SELECT password_hash FROM admin_users WHERE id = :id"), {"id": user_id}).first()
        if not row:
            raise HTTPException(status_code=404, detail="User not found")
        if not admin_auth_manager.verify_password(request_data.password, row[0]):
            raise HTTPException(status_code=400, detail="Current password is incorrect")

        # Update email
        try:
            res = db.execute(
                text("UPDATE admin_users SET email = :em, updated_at = now() WHERE id = :id"),
                {"em": request_data.email, "id": user_id},
            )
            if (res.rowcount or 0) == 0:
                raise HTTPException(status_code=400, detail="Failed to update email address")
        except IntegrityError:
            raise HTTPException(status_code=400, detail="Failed to update email address - email may already be in use")

        if True:
            audit_logger.log_action(
                action=AuditAction.USER_UPDATE,
                username=session["username"],
                details={"field": "email", "new_value": request_data.email},
            )
            return {"success": True, "message": "Email address updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Email update error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update email address")


# Stats endpoints
@router.get("/stats/overview", response_model=OverviewStats)
async def get_overview_stats(
    days: float = Query(7, ge=0.1, le=90),
    session: Dict[str, Any] = Depends(require_admin_auth),
    db: Session = Depends(get_db_session),
) -> OverviewStats:
    """Get overview statistics for the specified number of days."""
    try:
        from datetime import datetime as _dt
        from datetime import timedelta

        end = _dt.now()
        start = end - timedelta(days=float(days))
        prev_end = start
        prev_start = prev_end - timedelta(days=float(days))

        params = {"start": start, "end": end, "pstart": prev_start, "pend": prev_end}
        total = (
            db.execute(
                text("SELECT COUNT(*) FROM query_logs WHERE timestamp >= :start AND timestamp < :end"), params
            ).scalar()
            or 0
        )
        prev_total = (
            db.execute(
                text("SELECT COUNT(*) FROM query_logs WHERE timestamp >= :pstart AND timestamp < :pend"), params
            ).scalar()
            or 0
        )
        # Prefer session_id if available; fallback to client_ip
        uniq = (
            db.execute(
                text(
                    "SELECT COUNT(DISTINCT COALESCE(NULLIF(session_id, ''), COALESCE(client_ip, 'unknown'))) FROM query_logs WHERE timestamp >= :start AND timestamp < :end"
                ),
                params,
            ).scalar()
            or 0
        )
        prev_uniq = (
            db.execute(
                text(
                    "SELECT COUNT(DISTINCT COALESCE(NULLIF(session_id, ''), COALESCE(client_ip, 'unknown'))) FROM query_logs WHERE timestamp >= :pstart AND timestamp < :pend"
                ),
                params,
            ).scalar()
            or 0
        )

        row = db.execute(
            text(
                "SELECT AVG(response_time_ms), AVG(CASE WHEN error_occurred THEN 1.0 ELSE 0.0 END), AVG(CASE WHEN cache_hit THEN 1.0 ELSE 0.0 END), AVG(CASE WHEN user_feedback = 'helpful' THEN 1.0 ELSE 0.0 END) FROM query_logs WHERE timestamp >= :start AND timestamp < :end"
            ),
            params,
        ).first()
        avg_rt = float(row[0] or 0)
        error_rate = float((row[1] or 0) * 100)
        cache_hit_rate = float((row[2] or 0) * 100)
        helpful_rate = float((row[3] or 0) * 100)
        rowp = db.execute(
            text(
                "SELECT AVG(response_time_ms), AVG(CASE WHEN error_occurred THEN 1.0 ELSE 0.0 END), AVG(CASE WHEN cache_hit THEN 1.0 ELSE 0.0 END), AVG(CASE WHEN user_feedback = 'helpful' THEN 1.0 ELSE 0.0 END) FROM query_logs WHERE timestamp >= :pstart AND timestamp < :pend"
            ),
            params,
        ).first()
        avg_rt_prev = float(rowp[0] or 0)
        error_rate_prev = float((rowp[1] or 0) * 100)
        cache_hit_rate_prev = float((rowp[2] or 0) * 100)
        helpful_rate_prev = float((rowp[3] or 0) * 100)

        def pct(cur, prev):
            if prev == 0:
                return 0.0 if cur == 0 else 100.0
            return round(((cur - prev) / prev) * 100.0, 1)

        today_start = _dt.now().replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = _dt.now() - timedelta(days=7)
        q_today = (
            db.execute(text("SELECT COUNT(*) FROM query_logs WHERE timestamp >= :ts"), {"ts": today_start}).scalar()
            or 0
        )
        q_week = (
            db.execute(text("SELECT COUNT(*) FROM query_logs WHERE timestamp >= :ws"), {"ws": week_start}).scalar() or 0
        )

        return OverviewStats(
            total_queries=int(total),
            unique_sessions=int(uniq),
            avg_response_time_ms=avg_rt,
            error_rate=error_rate,
            cache_hit_rate=cache_hit_rate,
            helpful_rate=helpful_rate,
            queries_today=int(q_today),
            queries_this_week=int(q_week),
            total_queries_change=pct(float(total), float(prev_total)),
            unique_sessions_change=pct(float(uniq), float(prev_uniq)),
            avg_response_time_change=pct(avg_rt, avg_rt_prev),
            error_rate_change=pct(error_rate, error_rate_prev),
            cache_hit_rate_change=pct(cache_hit_rate, cache_hit_rate_prev),
            helpful_rate_change=pct(helpful_rate, helpful_rate_prev),
        )
    except Exception as e:
        logger.error(f"Error fetching overview stats: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching overview statistics")


# Health endpoint
@router.get("/health")
async def health_check(db: Session = Depends(get_db_session)):
    """Health check endpoint (no auth required)."""
    try:
        # Test Postgres connection
        db.execute(text("SELECT 1"))

        return {"status": "healthy", "timestamp": datetime.now().isoformat()}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database connection failed: {str(e)}")


# Query management endpoints
@router.get("/queries", response_model=QueryResponse)
async def get_queries(
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None, max_length=500),
    errors_only: bool = Query(False),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    session: Dict[str, Any] = Depends(require_admin_auth),
    db: Session = Depends(get_db_session),
) -> QueryResponse:
    """Get paginated list of queries with optional filters and input sanitization."""
    try:
        # Sanitize search input
        if search:
            search = search.strip()[:500]  # Limit search length
        where = []
        params: Dict[str, Any] = {}
        if search:
            where.append("user_query ILIKE :q")
            params["q"] = f"%{search}%"
        if errors_only:
            where.append("error_occurred = true")
        if start_date:
            where.append("timestamp >= :start")
            params["start"] = start_date
        if end_date:
            where.append("timestamp <= :end")
            params["end"] = end_date
        where_clause = (" WHERE " + " AND ".join(where)) if where else ""

        total = db.execute(text(f"SELECT COUNT(*) FROM query_logs{where_clause}"), params).scalar() or 0
        params_lim = dict(params)
        params_lim.update({"limit": int(limit), "offset": int(offset)})
        rows = db.execute(
            text(
                f"""
                SELECT id, session_id, user_query, system_response, response_time_ms, timestamp, llm_provider, llm_model,
                       vector_search_score, sources_used, error_occurred, error_message, cache_hit, user_feedback, follow_up_questions, client_ip
                FROM query_logs{where_clause}
                ORDER BY timestamp DESC
                LIMIT :limit OFFSET :offset
                """
            ),
            params_lim,
        ).fetchall()
        queries = []
        for r in rows:
            q = {
                "id": r[0],
                "session_id": r[1],
                "user_query": r[2],
                "response": r[3],
                "response_time_ms": r[4],
                "timestamp": r[5],
                "llm_provider": r[6],
                "llm_model": r[7],
                "vector_search_score": r[8],
                "sources_used": r[9] or [],
                "error_occurred": bool(r[10]),
                "error_message": r[11],
                "cache_hit": bool(r[12]),
                "user_feedback": r[13],
                "follow_up_questions": r[14] or [],
                "client_ip": r[15],
            }
            queries.append(q)
        return QueryResponse(queries=queries, total=int(total), limit=limit, offset=offset)
    except Exception as e:
        logger.error(f"Error fetching queries: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching queries")


@router.get("/queries/{query_id}")
async def get_query_detail(
    query_id: int,
    session: Dict[str, Any] = Depends(require_admin_auth),
    db: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    """Get detailed information about a specific query with proper error handling."""
    if query_id <= 0:
        raise HTTPException(status_code=400, detail="Invalid query ID")

    try:
        row = db.execute(
            text(
                """
                SELECT id, session_id, user_query, system_response, response_time_ms, timestamp, llm_provider, llm_model,
                       vector_search_score, sources_used, error_occurred, error_message, cache_hit, user_feedback, follow_up_questions, client_ip
                FROM query_logs WHERE id = :id
                """
            ),
            {"id": query_id},
        ).first()

        if not row:
            raise HTTPException(status_code=404, detail="Query not found")

        return {
            "id": row[0],
            "session_id": row[1],
            "user_query": row[2],
            "response": row[3],
            "response_time_ms": row[4],
            "timestamp": row[5],
            "llm_provider": row[6],
            "llm_model": row[7],
            "vector_search_score": row[8],
            "sources_used": row[9] or [],
            "error_occurred": bool(row[10]),
            "error_message": row[11],
            "cache_hit": bool(row[12]),
            "user_feedback": row[13],
            "follow_up_questions": row[14] or [],
            "client_ip": row[15],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching query detail: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching query details")


@router.post("/queries/{query_id}/feedback")
async def update_query_feedback(
    query_id: int,
    feedback: FeedbackUpdate,
    session: Dict[str, Any] = Depends(require_admin_auth),
    db: Session = Depends(get_db_session),
) -> Dict[str, str]:
    """Update user feedback for a query with validation."""
    if query_id <= 0:
        raise HTTPException(status_code=400, detail="Invalid query ID")

    try:
        res = db.execute(
            text("UPDATE query_logs SET user_feedback = :fb WHERE id = :id"), {"fb": feedback.feedback, "id": query_id}
        )
        if (res.rowcount or 0) == 0:
            raise HTTPException(status_code=404, detail="Query not found")
        return {"status": "success", "message": "Feedback updated"}
    except Exception as e:
        logger.error(f"Error updating feedback: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error updating feedback")


# Performance endpoints
@router.get("/performance/metrics")
async def get_performance_metrics(
    time_range: str = Query("24h", pattern="^(1h|6h|24h|7d|30d)$"),
    session: Dict[str, Any] = Depends(require_admin_auth),
    db: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    """Get performance metrics for the specified time range."""
    try:
        # Check if we have any data and get actual latest timestamp
        result = db.execute(text("SELECT MAX(timestamp) FROM query_logs")).first()
        if not result or not result[0]:
            # No data available - return zeros
            return {
                "response_time": {"current": 0, "previous": 0, "change": 0},
                "throughput": {"current": 0, "previous": 0, "change": 0},
                "error_rate": {"current": 0, "previous": 0, "change": 0},
                "cache_hit_rate": {"current": 0, "previous": 0, "change": 0},
            }

        # Use actual latest data timestamp for accurate time range
        end_date = result[0]
        start_date, end_date = parse_time_range(time_range, end_date)

        # Calculate dynamic date ranges based on the period
        period_duration = end_date - start_date
        previous_period_end = start_date
        previous_period_start = previous_period_end - period_duration

        current_period_start = start_date
        current_period_end = end_date
        previous_start = previous_period_start
        previous_end = previous_period_end

        # Get current period metrics
        row = db.execute(
            text(
                """
                SELECT AVG(response_time_ms) AS art,
                       COUNT(*) AS qc,
                       AVG(CASE WHEN error_occurred THEN 1.0 ELSE 0.0 END) AS er
                FROM query_logs
                WHERE timestamp >= :start AND timestamp <= :end AND response_time_ms IS NOT NULL
                """
            ),
            {"start": current_period_start, "end": current_period_end},
        ).first()
        current_response_time = float(row[0] or 0.0)
        current_queries = int(row[1] or 0)
        current_error_rate = float((row[2] or 0.0) * 100)

        # Get previous period metrics
        rowp = db.execute(
            text(
                """
                SELECT AVG(response_time_ms) AS art,
                       COUNT(*) AS qc,
                       AVG(CASE WHEN error_occurred THEN 1.0 ELSE 0.0 END) AS er
                FROM query_logs
                WHERE timestamp >= :start AND timestamp <= :end AND response_time_ms IS NOT NULL
                """
            ),
            {"start": previous_start, "end": previous_end},
        ).first()
        previous_response_time = float(rowp[0] or 0.0)
        previous_queries = int(rowp[1] or 0)
        previous_error_rate = float((rowp[2] or 0.0) * 100)

        # Calculate changes
        def calculate_change(current, previous):
            if previous == 0:
                return 100.0 if current > 0 else 0.0
            return round(((current - previous) / previous) * 100, 2)

        # Calculate throughput (queries per hour)
        period_hours = period_duration.total_seconds() / 3600
        current_throughput = current_queries / period_hours if period_hours > 0 else 0
        previous_throughput = previous_queries / period_hours if period_hours > 0 else 0

        return {
            "response_time": {
                "current": round(current_response_time, 1),
                "previous": round(previous_response_time, 1),
                "change": calculate_change(current_response_time, previous_response_time),
            },
            "throughput": {
                "current": round(current_throughput, 1),
                "previous": round(previous_throughput, 1),
                "change": calculate_change(current_throughput, previous_throughput),
            },
            "error_rate": {
                "current": round(current_error_rate, 2),
                "previous": round(previous_error_rate, 2),
                "change": calculate_change(current_error_rate, previous_error_rate),
            },
            "cache_hit_rate": {
                "current": AppConfig.DEFAULT_CACHE_HIT_RATE * 100,
                "previous": AppConfig.DEFAULT_CACHE_HIT_RATE * 100,
                "change": 0.0,
            },
        }
    except Exception as e:
        logger.error(f"Error fetching performance metrics: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching performance metrics")


@router.get("/performance/timeline")
async def get_performance_timeline(
    days: float = Query(7, ge=0.1, le=30),
    interval: str = Query("day", pattern="^(hour|day)$"),
    session: Dict[str, Any] = Depends(require_admin_auth),
    db: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    """Get performance timeline data for charts."""
    try:
        itv = "hour" if interval == "hour" else "day"
        rows = db.execute(
            text(
                f"""
                SELECT to_char(date_trunc(:itv, timestamp), CASE WHEN :itv = 'hour' THEN 'YYYY-MM-DD HH24:00:00' ELSE 'YYYY-MM-DD' END) AS period,
                       COUNT(*) AS query_count,
                       AVG(response_time_ms) AS avg_response_time,
                       AVG(CASE WHEN error_occurred THEN 1.0 ELSE 0.0 END) AS error_rate,
                       AVG(CASE WHEN cache_hit THEN 1.0 ELSE 0.0 END) AS cache_hit_rate
                FROM query_logs
                WHERE timestamp >= (now() - make_interval(days => :days))
                GROUP BY date_trunc(:itv, timestamp)
                ORDER BY date_trunc(:itv, timestamp)
                """
            ),
            {"itv": itv, "days": int(days)},
        ).fetchall()
        timeline_data = [
            {
                "period": r[0],
                "query_count": int(r[1] or 0),
                "avg_response_time": round(float(r[2] or 0.0), 1),
                "error_rate": round(float((r[3] or 0.0) * 100), 2),
                "cache_hit_rate": round(float((r[4] or 0.0) * 100), 1),
            }
            for r in rows
        ]
        return {"timeline": timeline_data}

    except Exception as e:
        logger.error(f"Error fetching performance timeline: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching performance timeline")


@router.get("/performance/percentiles")
async def get_response_time_percentiles(
    time_range: str = Query("7d", pattern="^(1h|6h|24h|7d|30d)$"),
    session: Dict[str, Any] = Depends(require_admin_auth),
    db: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    """Get response time percentiles for performance analysis."""
    try:
        time_map = {"1h": "1 hours", "6h": "6 hours", "24h": "1 days", "7d": "7 days", "30d": "30 days"}
        interval = time_map.get(time_range, "7 days")
        row = db.execute(
            text(
                """
                SELECT
                  percentile_cont(0.50) WITHIN GROUP (ORDER BY response_time_ms) AS p50,
                  percentile_cont(0.75) WITHIN GROUP (ORDER BY response_time_ms) AS p75,
                  percentile_cont(0.90) WITHIN GROUP (ORDER BY response_time_ms) AS p90,
                  percentile_cont(0.95) WITHIN GROUP (ORDER BY response_time_ms) AS p95,
                  percentile_cont(0.99) WITHIN GROUP (ORDER BY response_time_ms) AS p99,
                  COUNT(*) AS cnt
                FROM query_logs
                WHERE timestamp >= (now() - (:itv)::interval) AND response_time_ms IS NOT NULL
                """
            ),
            {"itv": interval},
        ).first()
        percentiles = {
            "p50": round(float(row[0] or 0.0), 1),
            "p75": round(float(row[1] or 0.0), 1),
            "p90": round(float(row[2] or 0.0), 1),
            "p95": round(float(row[3] or 0.0), 1),
            "p99": round(float(row[4] or 0.0), 1),
        }
        return {"percentiles": percentiles, "sample_size": int(row[5] or 0)}

    except Exception as e:
        logger.error(f"Error fetching response time percentiles: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching response time percentiles")


# Knowledge base endpoints
@router.get("/knowledge/files")
async def get_knowledge_files(session: Dict[str, Any] = Depends(require_admin_auth)):
    """Get list of files in the knowledge base directory."""
    knowledge_dir = Path(__file__).parent.parent / "knowledge"

    if not knowledge_dir.exists():
        return {"files": [], "total_files": 0}

    try:
        files = []
        for file_path in knowledge_dir.iterdir():
            if file_path.is_file() and not file_path.name.startswith("."):
                stat = file_path.stat()
                files.append(
                    {
                        "name": file_path.name,
                        "type": file_path.suffix.lower(),
                        "size": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    }
                )

        # Sort by modification time (newest first)
        files.sort(key=lambda x: x["modified"], reverse=True)

        return {"files": files, "total_files": len(files)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing files: {str(e)}")


# Content management endpoints
# Note: Content gaps endpoints are provided by backend/routes/content.py.
# They are mounted under both /api and /api/admin in app_factory to keep the
# client base URL consistent. This avoids duplicate implementations here.


# Export endpoints
@router.get("/export/csv")
async def export_csv(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    export_type: str = Query("queries", pattern="^(queries|metrics)$"),
    session: Dict[str, Any] = Depends(require_admin_auth),
    db: Session = Depends(get_db_session),
):
    """Export data as CSV file."""
    try:
        output = io.StringIO()
        writer = csv.writer(output)

        if export_type == "queries":
            # Build WHERE clause for date filtering (named params)
            where_conditions = []
            params: Dict[str, Any] = {}

            if start_date:
                where_conditions.append("timestamp >= :start")
                params["start"] = start_date

            if end_date:
                where_conditions.append("timestamp <= :end")
                params["end"] = end_date

            where_clause = (" WHERE " + " AND ".join(where_conditions)) if where_conditions else ""

            rows = db.execute(
                text(
                    f"""
                    SELECT id, user_query, response_time_ms,
                           llm_provider, llm_model, vector_search_score,
                           cache_hit, error_occurred, error_message,
                           user_feedback, timestamp
                    FROM query_logs{where_clause}
                    ORDER BY timestamp DESC
                    """
                ),
                params,
            ).fetchall()

            # Write header
            writer.writerow(
                [
                    "ID",
                    "User Query",
                    "Response Time (ms)",
                    "LLM Provider",
                    "LLM Model",
                    "Search Score",
                    "Cache Hit",
                    "Error Occurred",
                    "Error Message",
                    "User Feedback",
                    "Timestamp",
                ]
            )

            # Write data
            for r in rows:
                writer.writerow(list(r))

        # Prepare response
        output.seek(0)
        filename = f"rag_admin_{export_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        return StreamingResponse(
            io.BytesIO(output.getvalue().encode()),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error exporting CSV: {str(e)}")


# Security monitoring endpoints
@router.get("/security/alerts")
async def get_security_alerts(
    hours: int = Query(24, ge=1, le=168, description="Hours to look back"),
    session: Dict[str, Any] = Depends(require_admin_auth),
) -> Dict[str, Any]:
    """Get recent security events and alerts."""
    try:
        alerts = admin_auth_manager.get_security_alerts(hours)

        # Categorize alerts by severity
        critical = [a for a in alerts if a["severity"] == "critical"]
        high = [a for a in alerts if a["severity"] == "high"]
        medium = [a for a in alerts if a["severity"] == "medium"]
        low = [a for a in alerts if a["severity"] == "low"]

        return {
            "alerts": alerts,
            "summary": {
                "total": len(alerts),
                "critical": len(critical),
                "high": len(high),
                "medium": len(medium),
                "low": len(low),
            },
            "time_range_hours": hours,
        }
    except Exception as e:
        logger.error(f"Error fetching security alerts: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching security alerts")


@router.get("/security/session-stats")
async def get_session_security_stats(
    session: Dict[str, Any] = Depends(require_admin_auth), db: Session = Depends(get_db_session)
) -> Dict[str, Any]:
    """Get session-related security statistics."""
    try:
        # Active sessions by IP (Postgres)
        rows = db.execute(
            text(
                """
                SELECT COALESCE(ip_address, 'unknown') AS ip, COUNT(*) AS session_count
                FROM admin_sessions
                WHERE is_active = true
                GROUP BY ip
                ORDER BY session_count DESC
                LIMIT 10
                """
            )
        ).fetchall()
        sessions_by_ip = [{"ip": r[0], "count": r[1]} for r in rows]

        # Sessions by user
        rows = db.execute(
            text(
                """
                SELECT u.username, COUNT(*) AS session_count
                FROM admin_sessions s
                JOIN admin_users u ON s.user_id = u.id
                WHERE s.is_active = true
                GROUP BY u.username
                ORDER BY session_count DESC
                """
            )
        ).fetchall()
        sessions_by_user = [{"username": r[0], "count": r[1]} for r in rows]

        # Session duration statistics (hours)
        row = db.execute(
            text(
                """
                SELECT
                    AVG(EXTRACT(EPOCH FROM (now() - started_at)) / 3600.0) AS avg_duration_hours,
                    MAX(EXTRACT(EPOCH FROM (now() - started_at)) / 3600.0) AS max_duration_hours,
                    COUNT(*) AS total_active_sessions
                FROM admin_sessions
                WHERE is_active = true
                """
            )
        ).first()
        duration_stats = row or (0.0, 0.0, 0)

        return {
            "sessions_by_ip": sessions_by_ip,
            "sessions_by_user": sessions_by_user,
            "duration_stats": {
                "average_hours": round((duration_stats[0] or 0), 1),
                "max_hours": round((duration_stats[1] or 0), 1),
                "total_active": int(duration_stats[2] or 0),
            },
        }
    except Exception as e:
        logger.error(f"Error fetching session security stats: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching session security statistics")


# Settings endpoints
@router.get("/settings/followup")
async def get_followup_settings(
    request: Request, session: Dict[str, Any] = Depends(require_admin_auth)
) -> Dict[str, Any]:
    """Get current follow-up question settings."""
    try:
        # Use settings manager for cached access
        settings_mgr = get_settings_manager()
        settings = settings_mgr.get_followup_settings()

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.DATA_VIEW,
            username=session["username"],
            details={"resource": "followup_settings"},
            ip_address=client_ip,
            user_agent=user_agent,
        )

        return settings.to_dict()

    except Exception as e:
        logger.error(f"Error getting follow-up settings: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching follow-up settings")


@router.put("/settings/followup")
async def update_followup_settings(
    request: Request, settings_data: Dict[str, Any], session: Dict[str, Any] = Depends(require_admin_auth)
) -> Dict[str, Any]:
    """Update follow-up question settings."""
    try:
        # Validate and create settings object
        settings = FollowUpSettings.from_dict(settings_data)

        # Use settings manager to store settings
        settings_mgr = get_settings_manager()
        success = settings_mgr.set_followup_settings(settings, session["user_id"])

        if not success:
            raise HTTPException(status_code=500, detail="Failed to update settings")

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.CONFIG_UPDATE,
            username=session["username"],
            details={"resource": "followup_settings", "new_settings": settings.to_dict()},
            ip_address=client_ip,
            user_agent=user_agent,
        )

        # Clear cache in follow-up service to ensure immediate effect
        try:
            followup_service = getattr(request.app.state, "followup_service", None)
            if followup_service and hasattr(followup_service, "clear_cache"):
                followup_service.clear_cache()
                logger.info("FollowUp service cache cleared after settings update")
            else:
                logger.warning("FollowUp service not found or clear_cache method not available")
        except Exception as e:
            logger.warning(f"Could not clear followup service cache: {e}")

        # Invalidate cached settings to apply changes promptly
        try:
            settings_mgr.invalidate_cache("followup_settings")
        except Exception:
            pass

        logger.info(f"Follow-up settings updated by user {session['user_id']}: {settings.to_dict()}")

        return {"success": True, "message": "Follow-up settings updated successfully", "settings": settings.to_dict()}

    except Exception as e:
        logger.error(f"Error updating follow-up settings: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error updating follow-up settings")


@router.post("/settings/followup/reset")
async def reset_followup_settings(
    request: Request, session: Dict[str, Any] = Depends(require_admin_auth)
) -> Dict[str, Any]:
    """Reset follow-up settings to defaults."""
    try:
        # Create default settings
        default_settings = FollowUpSettings()

        # Use settings manager to store settings
        settings_mgr = get_settings_manager()
        success = settings_mgr.set_followup_settings(default_settings, session["user_id"])

        if not success:
            raise HTTPException(status_code=500, detail="Failed to reset settings")

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.CONFIG_UPDATE,
            username=session["username"],
            details={
                "resource": "followup_settings",
                "action": "reset_to_defaults",
                "reset_to": default_settings.to_dict(),
            },
            ip_address=client_ip,
            user_agent=user_agent,
        )

        # Clear cache in follow-up service to ensure immediate effect
        try:
            followup_service = getattr(request.app.state, "followup_service", None)
            if followup_service and hasattr(followup_service, "clear_cache"):
                followup_service.clear_cache()
                logger.info("FollowUp service cache cleared after settings reset")
            else:
                logger.warning("FollowUp service not found or clear_cache method not available")
        except Exception as e:
            logger.warning(f"Could not clear followup service cache: {e}")

        # Invalidate cached settings to apply changes promptly
        try:
            settings_mgr.invalidate_cache("followup_settings")
        except Exception:
            pass

        logger.info(f"Follow-up settings reset to defaults by user {session['user_id']}")

        return {
            "success": True,
            "message": "Follow-up settings reset to defaults",
            "settings": default_settings.to_dict(),
        }

    except Exception as e:
        logger.error(f"Error resetting follow-up settings: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error resetting follow-up settings")


# Follow-up Category Management Routes
@router.get("/settings/followup/categories")
async def get_followup_categories(
    request: Request,
    session: Dict[str, Any] = Depends(require_admin_auth),
    include_inactive: bool = Query(default=True, description="Include inactive categories"),
    pg_session: Session = Depends(get_db_session),
) -> List[Dict[str, Any]]:
    """Get all follow-up categories with optional filtering."""
    try:
        # Fetch categories from Postgres with explicit tenant filter
        tenant_filter = "tenant_id = COALESCE(NULLIF(current_setting('app.tenant_id', true), '')::uuid, CAST(:fallback_tid AS uuid))"
        if include_inactive:
            where = f"WHERE {tenant_filter}"
        else:
            where = f"WHERE {tenant_filter} AND is_active = true"

        rows = pg_session.execute(
            text(
                f"""
                SELECT id, name, display_name, description, icon, sort_order, is_active,
                       created_at, updated_at
                FROM followup_categories
                {where}
                ORDER BY sort_order, name
                """
            ),
            {
                "fallback_tid": str(
                    getattr(request.state, "tenant_id", None)
                    or os.getenv("DEFAULT_TENANT_ID")
                    or "00000000-0000-0000-0000-000000000001"
                )
            },
        ).fetchall()
        categories = [
            {
                "id": r[0],
                "name": r[1],
                "display_name": r[2],
                "description": r[3],
                "icon": r[4],
                "sort_order": int(r[5] or 0),
                "is_active": bool(r[6]) if r[6] is not None else True,
                "created_at": r[7],
                "updated_at": r[8],
            }
            for r in rows
        ]

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.DATA_VIEW,
            username=session["username"],
            details={"resource": "followup_categories", "include_inactive": include_inactive, "count": len(categories)},
            ip_address=client_ip,
            user_agent=user_agent,
        )

        return categories

    except Exception as e:
        logger.error(f"Error getting follow-up categories: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching follow-up categories")


@router.post("/settings/followup/categories")
async def create_followup_category(
    request: Request,
    category_data: CreateFollowupCategoryRequest,
    session: Dict[str, Any] = Depends(require_admin_auth),
    pg_session: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    """Create a new follow-up category."""
    try:
        # Ensure unique per-tenant name
        dup = pg_session.execute(
            text("SELECT 1 FROM followup_categories WHERE name = :name"), {"name": category_data.name}
        ).first()
        if dup:
            raise HTTPException(status_code=409, detail=f"Category '{category_data.name}' already exists")

        row = pg_session.execute(
            text(
                """
                INSERT INTO followup_categories (tenant_id, name, display_name, description, icon, sort_order, is_active)
                VALUES (
                    COALESCE(NULLIF(current_setting('app.tenant_id', true), '')::uuid, CAST(:fallback_tid AS uuid)),
                    :name, :display_name, :description, :icon, :sort_order, true
                )
                RETURNING id, name, display_name, description, icon, sort_order, is_active, created_at, updated_at
                """
            ),
            {
                "fallback_tid": str(
                    getattr(request.state, "tenant_id", None)
                    or os.getenv("DEFAULT_TENANT_ID")
                    or "00000000-0000-0000-0000-000000000001"
                ),
                "name": category_data.name,
                "display_name": category_data.display_name,
                "description": category_data.description,
                "icon": category_data.icon or "help-circle",
                "sort_order": category_data.sort_order or 0,
            },
        ).first()
        created_category = {
            "id": row[0],
            "name": row[1],
            "display_name": row[2],
            "description": row[3],
            "icon": row[4],
            "sort_order": int(row[5] or 0),
            "is_active": bool(row[6]),
            "created_at": row[7],
            "updated_at": row[8],
        }

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.DATA_CREATE,
            username=session["username"],
            details={
                "resource": "followup_category",
                "category_id": created_category["id"],
                "name": category_data.name,
            },
            ip_address=client_ip,
            user_agent=user_agent,
        )

        logger.info(f"Follow-up category created by user {session['user_id']}: {category_data.name}")

        return created_category

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating follow-up category: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error creating follow-up category")


@router.put("/settings/followup/categories/{category_id}")
async def update_followup_category(
    request: Request,
    category_id: int,
    category_data: UpdateFollowupCategoryRequest,
    session: Dict[str, Any] = Depends(require_admin_auth),
    pg_session: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    """Update an existing follow-up category."""
    try:
        # Ensure the category exists and belongs to tenant
        exists = pg_session.execute(
            text("SELECT 1 FROM followup_categories WHERE id = :id"), {"id": category_id}
        ).first()
        if not exists:
            raise HTTPException(status_code=404, detail="Category not found")

        updates = []
        params: Dict[str, Any] = {"id": category_id}
        for field, col in [
            ("display_name", "display_name"),
            ("description", "description"),
            ("icon", "icon"),
            ("sort_order", "sort_order"),
            ("is_active", "is_active"),
        ]:
            val = getattr(category_data, field, None)
            if val is not None:
                updates.append(f"{col} = :{field}")
                params[field] = val
        if not updates:
            # No changes
            row = pg_session.execute(
                text(
                    "SELECT id, name, display_name, description, icon, sort_order, is_active, created_at, updated_at FROM followup_categories WHERE id = :id"
                ),
                {"id": category_id},
            ).first()
        else:
            set_clause = ", ".join(updates) + ", updated_at = now()"
            pg_session.execute(text(f"UPDATE followup_categories SET {set_clause} WHERE id = :id"), params)
            row = pg_session.execute(
                text(
                    "SELECT id, name, display_name, description, icon, sort_order, is_active, created_at, updated_at FROM followup_categories WHERE id = :id"
                ),
                {"id": category_id},
            ).first()
        updated_category = {
            "id": row[0],
            "name": row[1],
            "display_name": row[2],
            "description": row[3],
            "icon": row[4],
            "sort_order": int(row[5] or 0),
            "is_active": bool(row[6]),
            "created_at": row[7],
            "updated_at": row[8],
        }

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.DATA_UPDATE,
            username=session["username"],
            details={
                "resource": "followup_category",
                "category_id": category_id,
                "changes": category_data.dict(exclude_unset=True),
            },
            ip_address=client_ip,
            user_agent=user_agent,
        )

        logger.info(f"Follow-up category {category_id} updated by user {session['user_id']}")

        return updated_category

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating follow-up category: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error updating follow-up category")


@router.post("/settings/followup/categories/{category_id}/delete")
async def delete_followup_category_with_strategy(
    request: Request,
    category_id: int,
    delete_request: CategoryDeleteRequest,
    session: Dict[str, Any] = Depends(require_admin_auth),
    pg_session: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    """Delete a follow-up category using specified strategy."""
    try:
        # Ensure category exists
        cat = pg_session.execute(text("SELECT 1 FROM followup_categories WHERE id = :id"), {"id": category_id}).first()
        if not cat:
            raise HTTPException(status_code=404, detail="Category not found")

        if delete_request.strategy == "delete":
            # Delete questions then category
            pg_session.execute(text("DELETE FROM followup_questions WHERE category_id = :id"), {"id": category_id})
            pg_session.execute(text("DELETE FROM followup_categories WHERE id = :id"), {"id": category_id})
            result = {"success": True, "action": "delete", "category_id": category_id}
        elif delete_request.strategy == "deactivate":
            pg_session.execute(
                text("UPDATE followup_categories SET is_active = false, updated_at = now() WHERE id = :id"),
                {"id": category_id},
            )
            result = {"success": True, "action": "deactivated", "category_id": category_id}
        elif delete_request.strategy == "move":
            if not delete_request.target_category_id:
                raise HTTPException(status_code=400, detail="target_category_id required for move strategy")
            tgt = pg_session.execute(
                text("SELECT 1 FROM followup_categories WHERE id = :id"),
                {"id": delete_request.target_category_id},
            ).first()
            if not tgt:
                raise HTTPException(status_code=400, detail="Invalid target category")
            pg_session.execute(
                text("UPDATE followup_questions SET category_id = :tgt WHERE category_id = :src"),
                {"tgt": delete_request.target_category_id, "src": category_id},
            )
            pg_session.execute(text("DELETE FROM followup_categories WHERE id = :id"), {"id": category_id})
            result = {
                "success": True,
                "action": "move",
                "category_id": category_id,
                "target_category_id": delete_request.target_category_id,
            }
        else:
            raise HTTPException(status_code=400, detail="Unknown strategy")

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        # Best-effort audit logging
        try:
            audit_logger.log_action(
                action=AuditAction.DATA_DELETE,
                username=session["username"],
                details={
                    "resource": "followup_category",
                    "category_id": category_id,
                    "strategy": delete_request.strategy,
                    "result": result,
                },
                ip_address=client_ip,
                user_agent=user_agent,
            )
        except Exception as log_err:
            logger.error(f"Audit log failed for category delete {category_id}: {log_err}")

        logger.info(
            f"Follow-up category {category_id} deleted by user {session['user_id']} using strategy: {delete_request.strategy}"
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting follow-up category: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error deleting follow-up category")


@router.get("/settings/followup/categories/{category_id}/stats")
async def get_followup_category_stats(
    request: Request,
    category_id: int,
    session: Dict[str, Any] = Depends(require_admin_auth),
    pg_session: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    """Get statistics for a specific follow-up category."""
    try:
        # First verify category exists for current tenant
        tenant_filter = "tenant_id = COALESCE(NULLIF(current_setting('app.tenant_id', true), '')::uuid, CAST(:fallback_tid AS uuid))"
        fallback_tid = str(
            getattr(request.state, "tenant_id", None)
            or os.getenv("DEFAULT_TENANT_ID")
            or "00000000-0000-0000-0000-000000000001"
        )

        category = pg_session.execute(
            text(f"SELECT id, name, display_name FROM followup_categories WHERE id = :id AND {tenant_filter}"),
            {"id": category_id, "fallback_tid": fallback_tid},
        ).first()
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")

        # Count questions with tenant filter
        qcount = (
            pg_session.execute(
                text(f"SELECT COUNT(*) FROM followup_questions WHERE category_id = :id AND {tenant_filter}"),
                {"id": category_id, "fallback_tid": fallback_tid},
            ).scalar()
            or 0
        )
        active_count = (
            pg_session.execute(
                text(
                    f"SELECT COUNT(*) FROM followup_questions WHERE category_id = :id AND is_active = true AND {tenant_filter}"
                ),
                {"id": category_id, "fallback_tid": fallback_tid},
            ).scalar()
            or 0
        )
        inactive_count = qcount - active_count

        stats = {
            "question_count": qcount,
            "active_questions": active_count,
            "inactive_questions": inactive_count,
            "category_id": category_id,
            "category_name": category[1],
            "category_display_name": category[2],
        }

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.DATA_VIEW,
            username=session["username"],
            details={"resource": "followup_category_stats", "category_id": category_id},
            ip_address=client_ip,
            user_agent=user_agent,
        )

        return stats

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting follow-up category stats: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error getting follow-up category stats")


# Follow-up Question Management Routes
@router.get("/settings/followup/questions")
async def get_followup_questions(
    request: Request,
    session: Dict[str, Any] = Depends(require_admin_auth),
    category_id: Optional[int] = Query(default=None, description="Filter by category ID"),
    active_only: bool = Query(default=False, description="Return only active questions"),
    search: Optional[str] = Query(default=None, description="Search in question text"),
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum number of questions to return"),
    offset: int = Query(default=0, ge=0, description="Number of questions to skip"),
    pg_session: Session = Depends(get_db_session),
) -> List[Dict[str, Any]]:
    """Get follow-up questions with filtering and pagination."""
    try:
        # Add explicit tenant filter
        tenant_filter = "tenant_id = COALESCE(NULLIF(current_setting('app.tenant_id', true), '')::uuid, CAST(:fallback_tid AS uuid))"
        where = [tenant_filter]
        params: Dict[str, Any] = {
            "limit": limit,
            "offset": offset,
            "fallback_tid": str(
                getattr(request.state, "tenant_id", None)
                or os.getenv("DEFAULT_TENANT_ID")
                or "00000000-0000-0000-0000-000000000001"
            ),
        }

        if category_id is not None:
            where.append("category_id = :cid")
            params["cid"] = category_id
        if active_only:
            where.append("is_active = true")
        if search:
            where.append("question_text ILIKE :q")
            params["q"] = f"%{search}%"
        where_clause = " WHERE " + " AND ".join(where)
        rows = pg_session.execute(
            text(
                f"""
                SELECT id, category_id, question_text, sort_order, is_active, created_at, updated_at, created_by
                FROM followup_questions
                {where_clause}
                ORDER BY sort_order, id
                LIMIT :limit OFFSET :offset
                """
            ),
            params,
        ).fetchall()
        questions = [
            {
                "id": r[0],
                "category_id": r[1],
                "question_text": r[2],
                "sort_order": int(r[3] or 0),
                "is_active": bool(r[4]) if r[4] is not None else True,
                "created_at": r[5],
                "updated_at": r[6],
                "created_by": r[7],
            }
            for r in rows
        ]

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.DATA_VIEW,
            username=session["username"],
            details={
                "resource": "followup_questions",
                "category_id": category_id,
                "active_only": active_only,
                "count": len(questions),
            },
            ip_address=client_ip,
            user_agent=user_agent,
        )

        return questions

    except Exception as e:
        logger.error(f"Error getting follow-up questions: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching follow-up questions")


@router.post("/settings/followup/questions")
async def create_followup_question(
    request: Request,
    question_data: CreateFollowupQuestionRequest,
    session: Dict[str, Any] = Depends(require_admin_auth),
    pg_session: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    """Create a new follow-up question."""
    try:
        exists = pg_session.execute(
            text("SELECT 1 FROM followup_categories WHERE id = :id"), {"id": question_data.category_id}
        ).first()
        if not exists:
            raise HTTPException(status_code=404, detail="Category not found")

        row = pg_session.execute(
            text(
                """
                INSERT INTO followup_questions (
                    tenant_id, category_id, question_text, sort_order, is_active, created_by
                ) VALUES (
                    COALESCE(NULLIF(current_setting('app.tenant_id', true), '')::uuid, CAST(:fallback_tid AS uuid)),
                    :category_id, :question_text, :sort_order, true, :created_by
                ) RETURNING id, category_id, question_text, sort_order, is_active, created_at, updated_at, created_by
                """
            ),
            {
                "fallback_tid": str(
                    getattr(request.state, "tenant_id", None)
                    or os.getenv("DEFAULT_TENANT_ID")
                    or "00000000-0000-0000-0000-000000000001"
                ),
                "category_id": question_data.category_id,
                "question_text": question_data.question_text,
                "sort_order": question_data.sort_order or 0,
                "created_by": session.get("user_id"),
            },
        ).first()
        created_question = {
            "id": row[0],
            "category_id": row[1],
            "question_text": row[2],
            "sort_order": int(row[3] or 0),
            "is_active": bool(row[4]),
            "created_at": row[5],
            "updated_at": row[6],
            "created_by": row[7],
        }

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        # Best-effort audit logging
        try:
            audit_logger.log_action(
                action=AuditAction.DATA_CREATE,
                username=session["username"],
                details={
                    "resource": "followup_question",
                    "question_id": created_question["id"],
                    "category_id": question_data.category_id,
                    "question_text": question_data.question_text,
                },
                ip_address=client_ip,
                user_agent=user_agent,
            )
        except Exception as log_err:
            logger.error(f"Audit log failed for question create: {log_err}")

        logger.info(f"Follow-up question created by user {session['user_id']}: {question_data.question_text}")

        return created_question

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating follow-up question: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error creating follow-up question")


@router.put("/settings/followup/questions/{question_id}")
async def update_followup_question(
    request: Request,
    question_id: int,
    question_data: UpdateFollowupQuestionRequest,
    session: Dict[str, Any] = Depends(require_admin_auth),
    pg_session: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    """Update an existing follow-up question."""
    try:
        exists = pg_session.execute(
            text("SELECT 1 FROM followup_questions WHERE id = :id"), {"id": question_id}
        ).first()
        if not exists:
            raise HTTPException(status_code=404, detail="Question not found")

        updates = []
        params: Dict[str, Any] = {"id": question_id}
        for field, col in [
            ("question_text", "question_text"),
            ("sort_order", "sort_order"),
            ("is_active", "is_active"),
        ]:
            val = getattr(question_data, field, None)
            if val is not None:
                updates.append(f"{col} = :{field}")
                params[field] = val
        if updates:
            set_clause = ", ".join(updates) + ", updated_at = now()"
            pg_session.execute(text(f"UPDATE followup_questions SET {set_clause} WHERE id = :id"), params)
        row = pg_session.execute(
            text(
                "SELECT id, category_id, question_text, sort_order, is_active, created_at, updated_at, created_by FROM followup_questions WHERE id = :id"
            ),
            {"id": question_id},
        ).first()
        updated_question = {
            "id": row[0],
            "category_id": row[1],
            "question_text": row[2],
            "sort_order": int(row[3] or 0),
            "is_active": bool(row[4]) if row[4] is not None else True,
            "created_at": row[5],
            "updated_at": row[6],
            "created_by": row[7],
        }

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        # Best-effort audit logging; do not fail the request if logging fails
        try:
            audit_logger.log_action(
                action=AuditAction.DATA_UPDATE,
                username=session["username"],
                details={
                    "resource": "followup_question",
                    "question_id": question_id,
                    "changes": question_data.dict(exclude_unset=True),
                },
                ip_address=client_ip,
                user_agent=user_agent,
            )
        except Exception as log_err:
            logger.error(f"Audit log failed for question update {question_id}: {log_err}")

        logger.info(f"Follow-up question {question_id} updated by user {session['user_id']}")

        return updated_question

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating follow-up question: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error updating follow-up question")


@router.delete("/settings/followup/questions/{question_id}")
async def delete_followup_question(
    request: Request,
    question_id: int,
    session: Dict[str, Any] = Depends(require_admin_auth),
    pg_session: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    """Delete a follow-up question."""
    try:
        row = pg_session.execute(
            text("SELECT question_text FROM followup_questions WHERE id = :id"), {"id": question_id}
        ).first()
        if not row:
            raise HTTPException(status_code=404, detail="Question not found")
        existing_question = {"question_text": row[0]}

        pg_session.execute(text("DELETE FROM followup_questions WHERE id = :id"), {"id": question_id})

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.DATA_DELETE,
            username=session["username"],
            details={
                "resource": "followup_question",
                "question_id": question_id,
                "question_text": existing_question.get("question_text", ""),
            },
            ip_address=client_ip,
            user_agent=user_agent,
        )

        logger.info(f"Follow-up question {question_id} deleted by user {session['user_id']}")

        return {"success": True, "message": "Question deleted successfully", "question_id": question_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting follow-up question: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error deleting follow-up question")


@router.post("/settings/followup/questions/bulk")
async def bulk_update_followup_questions(
    request: Request, bulk_request: BulkQuestionRequest, session: Dict[str, Any] = Depends(require_admin_auth)
) -> Dict[str, Any]:
    """Perform bulk operations on follow-up questions."""
    try:
        # Initialize management service
        from ..core.followup_management_service import FollowUpManagementService

        management_service = FollowUpManagementService()

        # Convert operations to expected format
        operations = [op.dict() for op in bulk_request.operations]

        # Perform bulk operations
        result = management_service.bulk_update_questions(operations)

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.DATA_UPDATE,
            username=session["username"],
            details={"resource": "followup_questions_bulk", "operation_count": len(operations), "result": result},
            ip_address=client_ip,
            user_agent=user_agent,
        )

        logger.info(f"Bulk question operations performed by user {session['user_id']}: {len(operations)} operations")

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error performing bulk question operations: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error performing bulk question operations")


# Additional settings endpoints for new functionality
@router.get("/settings/response")
async def get_response_settings(
    request: Request, session: Dict[str, Any] = Depends(require_admin_auth)
) -> Dict[str, Any]:
    """Get current response generation settings."""
    try:
        settings_mgr = get_settings_manager()
        settings = settings_mgr.get_response_settings()

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.DATA_VIEW,
            username=session["username"],
            details={"resource": "response_settings"},
            ip_address=client_ip,
            user_agent=user_agent,
        )

        return settings.to_dict()

    except Exception as e:
        logger.error(f"Error getting response settings: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching response settings")


@router.put("/settings/response")
async def update_response_settings(
    request: Request, settings_data: Dict[str, Any], session: Dict[str, Any] = Depends(require_admin_auth)
) -> Dict[str, Any]:
    """Update response generation settings."""
    try:
        settings = ResponseSettings.from_dict(settings_data)
        settings_mgr = get_settings_manager()
        success = settings_mgr.set_response_settings(settings, session["user_id"])

        if not success:
            raise HTTPException(status_code=500, detail="Failed to update response settings")

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.CONFIG_UPDATE,
            username=session["username"],
            details={"resource": "response_settings", "new_settings": settings.to_dict()},
            ip_address=client_ip,
            user_agent=user_agent,
        )

        # Invalidate cached settings to apply changes promptly
        try:
            settings_mgr.invalidate_cache("response_settings")
        except Exception:
            pass

        logger.info(f"Response settings updated by user {session['user_id']}: {settings.to_dict()}")
        return {"success": True, "message": "Response settings updated successfully", "settings": settings.to_dict()}

    except Exception as e:
        logger.error(f"Error updating response settings: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error updating response settings")


@router.get("/settings/routing")
async def get_routing_settings(
    request: Request, session: Dict[str, Any] = Depends(require_admin_auth)
) -> Dict[str, Any]:
    """Get current query routing settings."""
    try:
        settings_mgr = get_settings_manager()
        settings = settings_mgr.get_routing_settings()

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.DATA_VIEW,
            username=session["username"],
            details={"resource": "routing_settings"},
            ip_address=client_ip,
            user_agent=user_agent,
        )

        return settings.to_dict()

    except Exception as e:
        logger.error(f"Error getting routing settings: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching routing settings")


@router.put("/settings/routing")
async def update_routing_settings(
    request: Request, settings_data: Dict[str, Any], session: Dict[str, Any] = Depends(require_admin_auth)
) -> Dict[str, Any]:
    """Update query routing settings."""
    try:
        settings = QueryRoutingSettings.from_dict(settings_data)
        settings_mgr = get_settings_manager()
        success = settings_mgr.set_routing_settings(settings, session["user_id"])

        if not success:
            raise HTTPException(status_code=500, detail="Failed to update routing settings")

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.CONFIG_UPDATE,
            username=session["username"],
            details={"resource": "routing_settings", "new_settings": settings.to_dict()},
            ip_address=client_ip,
            user_agent=user_agent,
        )

        # Invalidate cached settings to apply changes promptly
        try:
            settings_mgr.invalidate_cache("routing_settings")
        except Exception:
            pass

        logger.info(f"Routing settings updated by user {session['user_id']}: {settings.to_dict()}")
        return {"success": True, "message": "Routing settings updated successfully", "settings": settings.to_dict()}

    except Exception as e:
        logger.error(f"Error updating routing settings: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error updating routing settings")


@router.get("/settings/features")
async def get_feature_flags(request: Request, session: Dict[str, Any] = Depends(require_admin_auth)) -> Dict[str, Any]:
    """Get current feature flags."""
    try:
        settings_mgr = get_settings_manager()
        settings = settings_mgr.get_feature_flags()

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.DATA_VIEW,
            username=session["username"],
            details={"resource": "feature_flags"},
            ip_address=client_ip,
            user_agent=user_agent,
        )

        return settings.to_dict()

    except Exception as e:
        logger.error(f"Error getting feature flags: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching feature flags")


@router.put("/settings/features")
async def update_feature_flags(
    request: Request, settings_data: Dict[str, Any], session: Dict[str, Any] = Depends(require_admin_auth)
) -> Dict[str, Any]:
    """Update feature flags."""
    try:
        settings = FeatureFlags.from_dict(settings_data)
        settings_mgr = get_settings_manager()
        success = settings_mgr.set_feature_flags(settings, session["user_id"])

        if not success:
            raise HTTPException(status_code=500, detail="Failed to update feature flags")

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.CONFIG_UPDATE,
            username=session["username"],
            details={"resource": "feature_flags", "new_settings": settings.to_dict()},
            ip_address=client_ip,
            user_agent=user_agent,
        )

        # Invalidate cached settings to apply changes promptly
        try:
            settings_mgr.invalidate_cache("feature_flags")
        except Exception:
            pass

        logger.info(f"Feature flags updated by user {session['user_id']}: {settings.to_dict()}")
        return {"success": True, "message": "Feature flags updated successfully", "settings": settings.to_dict()}

    except Exception as e:
        logger.error(f"Error updating feature flags: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error updating feature flags")


@router.get("/settings/cache/status")
async def get_settings_cache_status(
    request: Request, session: Dict[str, Any] = Depends(require_admin_auth)
) -> Dict[str, Any]:
    """Get settings cache status for monitoring."""
    try:
        settings_mgr = get_settings_manager()
        cache_status = settings_mgr.get_cache_status()

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.DATA_VIEW,
            username=session["username"],
            details={"resource": "settings_cache_status"},
            ip_address=client_ip,
            user_agent=user_agent,
        )

        return cache_status

    except Exception as e:
        logger.error(f"Error getting settings cache status: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching cache status")


@router.post("/settings/cache/invalidate")
async def invalidate_settings_cache(
    request: Request, session: Dict[str, Any] = Depends(require_admin_auth)
) -> Dict[str, Any]:
    """Invalidate settings cache to force refresh."""
    try:
        settings_mgr = get_settings_manager()
        settings_mgr.invalidate_cache()

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.CONFIG_UPDATE,
            username=session["username"],
            details={"resource": "settings_cache_invalidation"},
            ip_address=client_ip,
            user_agent=user_agent,
        )

        logger.info(f"Settings cache invalidated by user {session['user_id']}")
        return {"success": True, "message": "Settings cache invalidated successfully"}

    except Exception as e:
        logger.error(f"Error invalidating settings cache: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error invalidating cache")


# Welcome Question Management Routes
@router.get("/settings/welcome/questions")
async def get_welcome_questions(
    request: Request,
    session: Dict[str, Any] = Depends(require_admin_auth),
    active_only: bool = Query(default=False, description="Return only active questions"),
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum number of questions to return"),
    offset: int = Query(default=0, ge=0, description="Number of questions to skip"),
    pg_session: Session = Depends(get_db_session),
) -> List[Dict[str, Any]]:
    """Get welcome questions with filtering and pagination."""
    try:
        # Apply explicit tenant filter in addition to RLS, to avoid leakage when connected with superuser
        tenant_filter = "tenant_id = COALESCE(NULLIF(current_setting('app.tenant_id', true), '')::uuid, CAST(:fallback_tid AS uuid))"
        clauses = [tenant_filter]
        if active_only:
            clauses.append("is_active = true")
        where_sql = " WHERE " + " AND ".join(clauses)

        rows = pg_session.execute(
            text(
                f"""
                SELECT id, question_text, sort_order, is_active, created_at, updated_at, created_by
                FROM welcome_questions
                {where_sql}
                ORDER BY sort_order, id
                LIMIT :limit OFFSET :offset
                """
            ),
            {
                "fallback_tid": str(
                    getattr(request.state, "tenant_id", None)
                    or os.getenv("DEFAULT_TENANT_ID")
                    or "00000000-0000-0000-0000-000000000001"
                ),
                "limit": limit,
                "offset": offset,
            },
        ).fetchall()
        questions = [
            {
                "id": r[0],
                "question_text": r[1],
                "sort_order": int(r[2] or 0),
                "is_active": bool(r[3]) if r[3] is not None else True,
                "created_at": r[4],
                "updated_at": r[5],
                "created_by": r[6],
            }
            for r in rows
        ]

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.DATA_VIEW,
            username=session["username"],
            details={
                "resource": "welcome_questions",
                "active_only": active_only,
                "count": len(questions),
            },
            ip_address=client_ip,
            user_agent=user_agent,
        )

        return questions

    except Exception as e:
        logger.error(f"Error getting welcome questions: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching welcome questions")


@router.post("/settings/welcome/questions")
async def create_welcome_question(
    request: Request,
    question_data: CreateWelcomeQuestionRequest,
    session: Dict[str, Any] = Depends(require_admin_auth),
    pg_session: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    """Create a new welcome question."""
    try:
        # Defensive: ensure GUC is populated for this connection and verify value
        try:
            # Re-apply to be extra safe if anything changed transaction context
            import os

            from sqlalchemy import text as _text

            tid = (
                getattr(request.state, "tenant_id", None)
                or os.getenv("DEFAULT_TENANT_ID")
                or "00000000-0000-0000-0000-000000000001"
            )
            pg_session.execute(_text("SET LOCAL app.tenant_id = :tid"), {"tid": str(tid)})
            # Optional sanity check (does not alter behavior)
            _guc = pg_session.execute(_text("SELECT current_setting('app.tenant_id', true)"))
            _val = _guc.scalar() if _guc else None
            if not _val:
                logger.warning("Tenant GUC empty prior to welcome insert; re-setting with fallback value")
                pg_session.execute(_text("SET LOCAL app.tenant_id = :tid"), {"tid": str(tid)})
        except Exception:
            # Non-fatal; proceed. RLS/policies will still enforce.
            pass
        row = pg_session.execute(
            text(
                """
                INSERT INTO welcome_questions (tenant_id, question_text, sort_order, is_active, created_by)
                VALUES (
                    COALESCE(NULLIF(current_setting('app.tenant_id', true), '')::uuid, CAST(:fallback_tid AS uuid)),
                    :text, :sort_order, true, :uid
                )
                RETURNING id, question_text, sort_order, is_active, created_at, updated_at, created_by
                """
            ),
            {
                "fallback_tid": str(
                    getattr(request.state, "tenant_id", None)
                    or os.getenv("DEFAULT_TENANT_ID")
                    or "00000000-0000-0000-0000-000000000001"
                ),
                "text": question_data.question_text,
                "sort_order": question_data.sort_order or 0,
                "uid": session["user_id"],
            },
        ).first()
        created_question = {
            "id": row[0],
            "question_text": row[1],
            "sort_order": int(row[2] or 0),
            "is_active": bool(row[3]),
            "created_at": row[4],
            "updated_at": row[5],
            "created_by": row[6],
        }

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.DATA_CREATE,
            username=session["username"],
            details={
                "resource": "welcome_question",
                "question_id": created_question["id"],
                "question_text": question_data.question_text,
            },
            ip_address=client_ip,
            user_agent=user_agent,
        )

        logger.info(f"Welcome question created by user {session['user_id']}: {question_data.question_text}")

        return created_question

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating welcome question: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error creating welcome question")


@router.put("/settings/welcome/questions/{question_id}")
async def update_welcome_question(
    request: Request,
    question_id: int,
    question_data: UpdateWelcomeQuestionRequest,
    session: Dict[str, Any] = Depends(require_admin_auth),
    pg_session: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    """Update an existing welcome question."""
    try:
        exists = pg_session.execute(text("SELECT 1 FROM welcome_questions WHERE id = :id"), {"id": question_id}).first()
        if not exists:
            raise HTTPException(status_code=404, detail="Question not found")

        updates = []
        params: Dict[str, Any] = {"id": question_id}
        for field, col in [
            ("question_text", "question_text"),
            ("sort_order", "sort_order"),
            ("is_active", "is_active"),
        ]:
            val = getattr(question_data, field, None)
            if val is not None:
                updates.append(f"{col} = :{field}")
                params[field] = val
        if updates:
            set_clause = ", ".join(updates) + ", updated_at = now()"
            pg_session.execute(text(f"UPDATE welcome_questions SET {set_clause} WHERE id = :id"), params)
        row = pg_session.execute(
            text(
                "SELECT id, question_text, sort_order, is_active, created_at, updated_at, created_by FROM welcome_questions WHERE id = :id"
            ),
            {"id": question_id},
        ).first()
        updated_question = {
            "id": row[0],
            "question_text": row[1],
            "sort_order": int(row[2] or 0),
            "is_active": bool(row[3]) if row[3] is not None else True,
            "created_at": row[4],
            "updated_at": row[5],
            "created_by": row[6],
        }

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.DATA_UPDATE,
            username=session["username"],
            details={
                "resource": "welcome_question",
                "question_id": question_id,
                "changes": question_data.dict(exclude_unset=True),
            },
            ip_address=client_ip,
            user_agent=user_agent,
        )

        logger.info(f"Welcome question {question_id} updated by user {session['user_id']}")

        return updated_question

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating welcome question: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error updating welcome question")


@router.delete("/settings/welcome/questions/{question_id}")
async def delete_welcome_question(
    request: Request,
    question_id: int,
    session: Dict[str, Any] = Depends(require_admin_auth),
    pg_session: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    """Delete a welcome question."""
    try:
        row = pg_session.execute(
            text("SELECT question_text FROM welcome_questions WHERE id = :id"), {"id": question_id}
        ).first()
        if not row:
            raise HTTPException(status_code=404, detail="Question not found")
        existing_question = {"question_text": row[0]}

        pg_session.execute(text("DELETE FROM welcome_questions WHERE id = :id"), {"id": question_id})

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.DATA_DELETE,
            username=session["username"],
            details={
                "resource": "welcome_question",
                "question_id": question_id,
                "question_text": existing_question.get("question_text", ""),
            },
            ip_address=client_ip,
            user_agent=user_agent,
        )

        logger.info(f"Welcome question {question_id} deleted by user {session['user_id']}")

        return {"success": True, "message": "Question deleted successfully", "question_id": question_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting welcome question: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error deleting welcome question")


# Debug helper: list recent welcome questions (admin-only)
@router.get("/debug/welcome-questions")
async def debug_list_welcome_questions(
    request: Request,
    session: Dict[str, Any] = Depends(require_admin_auth),
    pg_session: Session = Depends(get_db_session),
    limit: int = Query(default=20, ge=1, le=1000, description="Max rows to return"),
    include_inactive: bool = Query(default=True, description="Include inactive questions"),
) -> Dict[str, Any]:
    try:
        where = "" if include_inactive else "WHERE is_active = true"
        rows = pg_session.execute(
            text(
                f"""
                SELECT id, tenant_id, question_text, sort_order, is_active, created_at, updated_at, created_by
                FROM welcome_questions
                {where}
                ORDER BY created_at DESC, id DESC
                LIMIT :limit
                """
            ),
            {"limit": limit},
        ).fetchall()

        items = [
            {
                "id": int(r[0]),
                "tenant_id": str(r[1]) if r[1] is not None else None,
                "question_text": r[2],
                "sort_order": int(r[3] or 0),
                "is_active": bool(r[4]) if r[4] is not None else True,
                "created_at": r[5],
                "updated_at": r[6],
                "created_by": r[7],
            }
            for r in rows
        ]

        # Report current tenant context for clarity
        try:
            tid_row = pg_session.execute(text("SELECT current_setting('app.tenant_id', true)"))
            tenant_ctx = tid_row.scalar() if tid_row else None
        except Exception:
            tenant_ctx = None

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")
        audit_logger.log_action(
            action=AuditAction.DATA_VIEW,
            username=session["username"],
            details={
                "resource": "welcome_questions_debug",
                "count": len(items),
                "include_inactive": include_inactive,
            },
            ip_address=client_ip,
            user_agent=user_agent,
        )

        return {"tenant_context": tenant_ctx, "rows": items, "count": len(items)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing debug welcome questions: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error listing welcome questions")


# Debug helper: list recent follow-up categories (admin-only)
@router.get("/debug/followup-categories")
async def debug_list_followup_categories(
    request: Request,
    session: Dict[str, Any] = Depends(require_admin_auth),
    pg_session: Session = Depends(get_db_session),
    limit: int = Query(default=20, ge=1, le=1000, description="Max rows to return"),
    include_inactive: bool = Query(default=True, description="Include inactive categories"),
) -> Dict[str, Any]:
    try:
        where = "" if include_inactive else "WHERE is_active = true"
        rows = pg_session.execute(
            text(
                f"""
                SELECT id, tenant_id, name, display_name, description, icon, sort_order, is_active, created_at, updated_at
                FROM followup_categories
                {where}
                ORDER BY created_at DESC, id DESC
                LIMIT :limit
                """
            ),
            {"limit": limit},
        ).fetchall()

        items = [
            {
                "id": int(r[0]),
                "tenant_id": str(r[1]) if r[1] is not None else None,
                "name": r[2],
                "display_name": r[3],
                "description": r[4],
                "icon": r[5],
                "sort_order": int(r[6] or 0),
                "is_active": bool(r[7]) if r[7] is not None else True,
                "created_at": r[8],
                "updated_at": r[9],
            }
            for r in rows
        ]

        try:
            tid_row = pg_session.execute(text("SELECT current_setting('app.tenant_id', true)"))
            tenant_ctx = tid_row.scalar() if tid_row else None
        except Exception:
            tenant_ctx = None

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")
        audit_logger.log_action(
            action=AuditAction.DATA_VIEW,
            username=session["username"],
            details={
                "resource": "followup_categories_debug",
                "count": len(items),
                "include_inactive": include_inactive,
            },
            ip_address=client_ip,
            user_agent=user_agent,
        )

        return {"tenant_context": tenant_ctx, "rows": items, "count": len(items)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing debug follow-up categories: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error listing follow-up categories")


# Debug helper: list recent follow-up questions (admin-only)
@router.get("/debug/followup-questions")
async def debug_list_followup_questions(
    request: Request,
    session: Dict[str, Any] = Depends(require_admin_auth),
    pg_session: Session = Depends(get_db_session),
    limit: int = Query(default=20, ge=1, le=1000, description="Max rows to return"),
    include_inactive: bool = Query(default=True, description="Include inactive questions"),
    category_id: Optional[int] = Query(default=None, description="Filter by category"),
    search: Optional[str] = Query(default=None, description="Search in question text"),
) -> Dict[str, Any]:
    try:
        where = []
        params: Dict[str, Any] = {"limit": limit}
        if not include_inactive:
            where.append("is_active = true")
        if category_id is not None:
            where.append("category_id = :cid")
            params["cid"] = category_id
        if search:
            where.append("question_text ILIKE :q")
            params["q"] = f"%{search}%"
        where_clause = (" WHERE " + " AND ".join(where)) if where else ""

        rows = pg_session.execute(
            text(
                f"""
                SELECT id, tenant_id, category_id, question_text, sort_order, is_active, created_at, updated_at, created_by
                FROM followup_questions
                {where_clause}
                ORDER BY created_at DESC, id DESC
                LIMIT :limit
                """
            ),
            params,
        ).fetchall()

        items = [
            {
                "id": int(r[0]),
                "tenant_id": str(r[1]) if r[1] is not None else None,
                "category_id": r[2],
                "question_text": r[3],
                "sort_order": int(r[4] or 0),
                "is_active": bool(r[5]) if r[5] is not None else True,
                "created_at": r[6],
                "updated_at": r[7],
                "created_by": r[8],
            }
            for r in rows
        ]

        try:
            tid_row = pg_session.execute(text("SELECT current_setting('app.tenant_id', true)"))
            tenant_ctx = tid_row.scalar() if tid_row else None
        except Exception:
            tenant_ctx = None

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")
        audit_logger.log_action(
            action=AuditAction.DATA_VIEW,
            username=session["username"],
            details={
                "resource": "followup_questions_debug",
                "count": len(items),
                "include_inactive": include_inactive,
                "category_id": category_id,
            },
            ip_address=client_ip,
            user_agent=user_agent,
        )

        return {"tenant_context": tenant_ctx, "rows": items, "count": len(items)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing debug follow-up questions: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error listing follow-up questions")


@router.post("/test/reset-database")
async def reset_test_database(session: Dict[str, Any] = Depends(require_admin_auth)):
    """Reset database to default state for testing purposes."""
    try:
        # Only allow in development or test environments
        env = os.environ.get("ENVIRONMENT", "development")  # Default to development
        if env not in ["development", "test", "testing"] and not os.environ.get("ALLOW_DB_RESET"):
            raise HTTPException(
                status_code=403, detail="Database reset only available in development/test environments"
            )

        # Clear test data but preserve admin users (Postgres)
        from backend.core.db_session import get_db_session_sync

        with get_db_session_sync() as session_db:
            if session_db is None:
                raise HTTPException(status_code=500, detail="Database unavailable")
            session_db.execute(text("DELETE FROM query_logs"))
            session_db.execute(text("DELETE FROM content_gaps"))

        logger.info(f"Test database reset completed by admin user {session['username']}")

        return {
            "success": True,
            "message": "Test database reset completed",
            "reset_items": ["query_logs", "content_gaps"],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resetting test database: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error resetting test database")


# API Key Management Endpoints
@router.get("/settings/api-keys")
async def get_api_keys(
    request: Request,
    session: Dict[str, Any] = Depends(require_admin_auth),
    include_inactive: bool = Query(default=False, description="Include inactive API keys"),
) -> Dict[str, Any]:
    """Get all API keys (without actual values)."""
    try:
        keys = api_key_manager.list_api_keys(include_inactive=include_inactive)

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.DATA_VIEW,
            username=session["username"],
            details={"resource": "api_keys", "count": len(keys), "include_inactive": include_inactive},
            ip_address=client_ip,
            user_agent=user_agent,
        )

        return {"keys": keys, "total": len(keys)}

    except Exception as e:
        logger.error(f"Error getting API keys: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching API keys")


@router.post("/settings/api-keys")
async def create_api_key(
    request: Request,
    key_data: Dict[str, Any],
    session: Dict[str, Any] = Depends(require_admin_auth),
) -> Dict[str, Any]:
    """Create a new API key."""
    try:
        # Validate required fields
        if not all(k in key_data for k in ["key_name", "key_type", "api_key"]):
            raise HTTPException(status_code=400, detail="Missing required fields: key_name, key_type, api_key")

        # Create the key
        created_key = api_key_manager.create_api_key(
            key_name=key_data["key_name"],
            key_type=key_data["key_type"],
            api_key=key_data["api_key"],
            updated_by=session["user_id"],
        )

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.DATA_CREATE,
            username=session["username"],
            details={"resource": "api_key", "key_name": created_key["key_name"], "key_type": created_key["key_type"]},
            ip_address=client_ip,
            user_agent=user_agent,
        )

        return {"success": True, "message": "API key created successfully", "key": created_key}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating API key: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error creating API key")


@router.put("/settings/api-keys/{key_name}")
async def update_api_key(
    request: Request,
    key_name: str,
    key_data: Dict[str, Any],
    session: Dict[str, Any] = Depends(require_admin_auth),
) -> Dict[str, Any]:
    """Update an existing API key."""
    try:
        if "api_key" not in key_data:
            raise HTTPException(status_code=400, detail="Missing required field: api_key")

        # Update the key
        success = api_key_manager.update_api_key(
            key_name=key_name, new_api_key=key_data["api_key"], updated_by=session["user_id"]
        )

        if not success:
            raise HTTPException(status_code=404, detail="API key not found")

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.DATA_UPDATE,
            username=session["username"],
            details={"resource": "api_key", "key_name": key_name},
            ip_address=client_ip,
            user_agent=user_agent,
        )

        return {"success": True, "message": "API key updated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating API key {key_name}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error updating API key")


@router.post("/settings/api-keys/{key_name}/toggle")
async def toggle_api_key(
    request: Request,
    key_name: str,
    toggle_data: Dict[str, Any],
    session: Dict[str, Any] = Depends(require_admin_auth),
) -> Dict[str, Any]:
    """Enable or disable an API key."""
    try:
        if "is_active" not in toggle_data:
            raise HTTPException(status_code=400, detail="Missing required field: is_active")

        success = api_key_manager.toggle_api_key(
            key_name=key_name, is_active=toggle_data["is_active"], updated_by=session["user_id"]
        )

        if not success:
            raise HTTPException(status_code=404, detail="API key not found")

        action_name = "enabled" if toggle_data["is_active"] else "disabled"
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.DATA_UPDATE,
            username=session["username"],
            details={
                "resource": "api_key",
                "key_name": key_name,
                "action": action_name,
                "is_active": toggle_data["is_active"],
            },
            ip_address=client_ip,
            user_agent=user_agent,
        )

        return {"success": True, "message": f"API key {action_name} successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling API key {key_name}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error toggling API key")


@router.delete("/settings/api-keys/{key_name}")
async def delete_api_key(
    request: Request,
    key_name: str,
    session: Dict[str, Any] = Depends(require_admin_auth),
) -> Dict[str, Any]:
    """Delete an API key."""
    try:
        success = api_key_manager.delete_api_key(key_name)

        if not success:
            raise HTTPException(status_code=404, detail="API key not found")

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.DATA_DELETE,
            username=session["username"],
            details={"resource": "api_key", "key_name": key_name},
            ip_address=client_ip,
            user_agent=user_agent,
        )

        return {"success": True, "message": "API key deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting API key {key_name}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error deleting API key")


@router.post("/settings/api-keys/{key_name}/validate")
async def validate_api_key(
    request: Request,
    key_name: str,
    session: Dict[str, Any] = Depends(require_admin_auth),
) -> Dict[str, Any]:
    """Validate an API key by testing it with the provider."""
    try:
        is_valid, message = api_key_manager.validate_api_key(key_name)

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.DATA_VIEW,
            username=session["username"],
            details={
                "resource": "api_key_validation",
                "key_name": key_name,
                "is_valid": is_valid,
                "validation_message": message,
            },
            ip_address=client_ip,
            user_agent=user_agent,
        )

        return {"success": True, "valid": is_valid, "message": message, "key_name": key_name}

    except Exception as e:
        logger.error(f"Error validating API key {key_name}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error validating API key")


@router.post("/settings/api-keys/migrate-from-env")
async def migrate_api_keys_from_env(
    request: Request,
    session: Dict[str, Any] = Depends(require_admin_auth),
) -> Dict[str, Any]:
    """Migrate API keys from environment variables to database."""
    try:
        results = api_key_manager.migrate_from_environment(session["user_id"])

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.CONFIG_UPDATE,
            username=session["username"],
            details={"resource": "api_key_migration", "migration_results": results},
            ip_address=client_ip,
            user_agent=user_agent,
        )

        successful = sum(1 for success in results.values() if success)
        total = len(results)

        return {
            "success": True,
            "message": f"Migration completed: {successful}/{total} keys migrated",
            "results": results,
        }

    except Exception as e:
        logger.error(f"Error migrating API keys from environment: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error migrating API keys")


# System Configuration Settings Endpoints
@router.get("/settings/system-config")
async def get_system_config_settings(
    request: Request, session: Dict[str, Any] = Depends(require_admin_auth)
) -> Dict[str, Any]:
    """Get current system configuration settings."""
    try:
        settings_mgr = get_settings_manager()
        settings = settings_mgr.get_system_config_settings()

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.DATA_VIEW,
            username=session["username"],
            details={"resource": "system_config_settings"},
            ip_address=client_ip,
            user_agent=user_agent,
        )

        return settings.to_dict()

    except Exception as e:
        logger.error(f"Error getting system config settings: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching system configuration settings")


@router.put("/settings/system-config")
async def update_system_config_settings(
    request: Request, settings_data: Dict[str, Any], session: Dict[str, Any] = Depends(require_admin_auth)
) -> Dict[str, Any]:
    """Update system configuration settings."""
    try:
        settings = SystemConfigurationSettings.from_dict(settings_data)
        settings_mgr = get_settings_manager()
        success = settings_mgr.set_system_config_settings(settings, session["user_id"])

        if not success:
            raise HTTPException(status_code=500, detail="Failed to update system configuration settings")

        # IMPORTANT: Invalidate settings cache to ensure changes take effect immediately
        # This prevents the 5-minute cache from serving stale settings
        settings_mgr.invalidate_cache("system_config_settings")
        logger.info("Invalidated system config settings cache after admin update")

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.CONFIG_UPDATE,
            username=session["username"],
            details={"resource": "system_config_settings", "new_settings": settings.to_dict()},
            ip_address=client_ip,
            user_agent=user_agent,
        )

        logger.info(f"System config settings updated by user {session['user_id']}: {settings.to_dict()}")
        return {
            "success": True,
            "message": "System configuration settings updated successfully",
            "settings": settings.to_dict(),
        }

    except Exception as e:
        logger.error(f"Error updating system config settings: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error updating system configuration settings")


# Security Settings Endpoints
@router.get("/settings/security")
async def get_security_settings(
    request: Request, session: Dict[str, Any] = Depends(require_admin_auth)
) -> Dict[str, Any]:
    """Get current security settings."""
    try:
        settings_mgr = get_settings_manager()
        settings = settings_mgr.get_security_settings()

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.DATA_VIEW,
            username=session["username"],
            details={"resource": "security_settings"},
            ip_address=client_ip,
            user_agent=user_agent,
        )

        return settings.to_dict()

    except Exception as e:
        logger.error(f"Error getting security settings: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching security settings")


@router.put("/settings/security")
async def update_security_settings(
    request: Request, settings_data: Dict[str, Any], session: Dict[str, Any] = Depends(require_admin_auth)
) -> Dict[str, Any]:
    """Update security settings."""
    try:
        settings = SecuritySettings.from_dict(settings_data)
        settings_mgr = get_settings_manager()
        success = settings_mgr.set_security_settings(settings, session["user_id"])

        if not success:
            raise HTTPException(status_code=500, detail="Failed to update security settings")

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.CONFIG_UPDATE,
            username=session["username"],
            details={"resource": "security_settings", "new_settings": settings.to_dict()},
            ip_address=client_ip,
            user_agent=user_agent,
        )

        # Invalidate cached settings to apply changes promptly
        try:
            settings_mgr = get_settings_manager()
            settings_mgr.invalidate_cache("security_settings")
        except Exception:
            pass

        logger.info(f"Security settings updated by user {session['user_id']}: {settings.to_dict()}")
        return {"success": True, "message": "Security settings updated successfully", "settings": settings.to_dict()}

    except Exception as e:
        logger.error(f"Error updating security settings: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error updating security settings")


@router.get("/settings/rag-config")
async def get_rag_config_settings(
    request: Request, session: Dict[str, Any] = Depends(require_admin_auth)
) -> Dict[str, Any]:
    """Get current RAG configuration settings."""
    try:
        settings_mgr = get_settings_manager()
        settings = settings_mgr.get_rag_config_settings()

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.DATA_VIEW,
            username=session["username"],
            details={"resource": "rag_config_settings"},
            ip_address=client_ip,
            user_agent=user_agent,
        )

        return {"settings": settings.to_dict(), "lastUpdated": datetime.now().isoformat()}

    except Exception as e:
        logger.error(f"Error getting RAG configuration settings: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching RAG configuration settings")


@router.put("/settings/rag-config")
async def update_rag_config_settings(
    request: Request, settings_data: Dict[str, Any], session: Dict[str, Any] = Depends(require_admin_auth)
) -> Dict[str, Any]:
    """Update RAG configuration settings."""
    try:
        settings = RagConfigurationSettings.from_dict(settings_data)

        # Validate settings before saving
        is_valid, errors = settings.validate()
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"Invalid RAG configuration settings: {', '.join(errors)}")

        settings_mgr = get_settings_manager()
        success = settings_mgr.set_rag_config_settings(settings, session["user_id"])

        if not success:
            raise HTTPException(status_code=500, detail="Failed to update RAG configuration settings")

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.CONFIG_UPDATE,
            username=session["username"],
            details={"resource": "rag_config_settings", "new_settings": settings.to_dict()},
            ip_address=client_ip,
            user_agent=user_agent,
        )

        # Invalidate cached settings to apply changes promptly
        try:
            settings_mgr.invalidate_cache("rag_config_settings")
        except Exception:
            pass

        logger.info(f"RAG configuration settings updated by user {session['user_id']}: {settings.to_dict()}")
        return {
            "success": True,
            "message": "RAG configuration settings updated successfully",
            "settings": settings.to_dict(),
            "lastUpdated": datetime.now().isoformat(),
        }

    except HTTPException:
        raise  # Re-raise HTTP exceptions without modification
    except Exception as e:
        logger.error(f"Error updating RAG configuration settings: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error updating RAG configuration settings")


# === Core Settings Endpoints ===
@router.get("/settings/core")
async def get_core_settings(session: Dict[str, Any] = Depends(require_admin_auth)) -> Dict[str, Any]:
    """Get core system configuration settings."""
    try:
        settings_mgr = get_settings_manager()
        settings = settings_mgr.get_core_settings()
        return {"settings": settings.to_dict()}

    except Exception as e:
        logger.error(f"Error getting core settings: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching core settings")


@router.put("/settings/core")
async def update_core_settings(
    request: Request, settings_data: Dict[str, Any], session: Dict[str, Any] = Depends(require_admin_auth)
) -> Dict[str, Any]:
    """Update core system configuration settings."""
    try:
        settings = CoreSettings.from_dict(settings_data)
        settings_mgr = get_settings_manager()
        success = settings_mgr.set_core_settings(settings, session["user_id"])

        if not success:
            raise HTTPException(status_code=500, detail="Failed to update core settings")

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.CONFIG_UPDATE,
            username=session["username"],
            details={"resource": "core_settings", "new_settings": settings.to_dict()},
            ip_address=client_ip,
            user_agent=user_agent,
        )

        # Invalidate cached settings to apply changes promptly
        try:
            settings_mgr.invalidate_cache("core_settings")
        except Exception:
            pass

        logger.info(f"Core settings updated by user {session['user_id']}: {settings.to_dict()}")
        return {
            "success": True,
            "message": "Core settings updated successfully",
            "settings": settings.to_dict(),
            "lastUpdated": datetime.now().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating core settings: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error updating core settings")


# === UX Settings Endpoints ===
@router.get("/settings/ux")
async def get_ux_settings(session: Dict[str, Any] = Depends(require_admin_auth)) -> Dict[str, Any]:
    """Get user experience settings."""
    try:
        settings_mgr = get_settings_manager()
        settings = settings_mgr.get_ux_settings()
        return {"settings": settings.to_dict()}

    except Exception as e:
        logger.error(f"Error getting UX settings: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching UX settings")


@router.put("/settings/ux")
async def update_ux_settings(
    request: Request, settings_data: Dict[str, Any], session: Dict[str, Any] = Depends(require_admin_auth)
) -> Dict[str, Any]:
    """Update user experience settings."""
    try:
        settings = UXSettings.from_dict(settings_data)
        settings_mgr = get_settings_manager()
        success = settings_mgr.set_ux_settings(settings, session["user_id"])

        if not success:
            raise HTTPException(status_code=500, detail="Failed to update UX settings")

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.CONFIG_UPDATE,
            username=session["username"],
            details={"resource": "ux_settings", "new_settings": settings.to_dict()},
            ip_address=client_ip,
            user_agent=user_agent,
        )

        # Invalidate cached settings to apply changes promptly
        try:
            settings_mgr.invalidate_cache("ux_settings")
        except Exception:
            pass

        logger.info(f"UX settings updated by user {session['user_id']}: {settings.to_dict()}")
        return {
            "success": True,
            "message": "UX settings updated successfully",
            "settings": settings.to_dict(),
            "lastUpdated": datetime.now().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating UX settings: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error updating UX settings")


# === Search Retrieval Settings Endpoints ===
@router.get("/settings/search-retrieval")
async def get_search_retrieval_settings(session: Dict[str, Any] = Depends(require_admin_auth)) -> Dict[str, Any]:
    """Get search and retrieval configuration settings."""
    try:
        settings_mgr = get_settings_manager()
        settings = settings_mgr.get_search_retrieval_settings()
        return {"settings": settings.to_dict()}

    except Exception as e:
        logger.error(f"Error getting search retrieval settings: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching search retrieval settings")


@router.put("/settings/search-retrieval")
async def update_search_retrieval_settings(
    request: Request, settings_data: Dict[str, Any], session: Dict[str, Any] = Depends(require_admin_auth)
) -> Dict[str, Any]:
    """Update search and retrieval configuration settings."""
    try:
        settings = SearchRetrievalSettings.from_dict(settings_data)
        settings_mgr = get_settings_manager()
        success = settings_mgr.set_search_retrieval_settings(settings, session["user_id"])

        if not success:
            raise HTTPException(status_code=500, detail="Failed to update search retrieval settings")

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.CONFIG_UPDATE,
            username=session["username"],
            details={"resource": "search_retrieval_settings", "new_settings": settings.to_dict()},
            ip_address=client_ip,
            user_agent=user_agent,
        )

        # Invalidate cached settings to apply changes promptly
        try:
            settings_mgr.invalidate_cache("search_retrieval_settings")
        except Exception:
            pass

        logger.info(f"Search retrieval settings updated by user {session['user_id']}: {settings.to_dict()}")
        return {
            "success": True,
            "message": "Search retrieval settings updated successfully",
            "settings": settings.to_dict(),
            "lastUpdated": datetime.now().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating search retrieval settings: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error updating search retrieval settings")


# === Knowledge Settings Endpoints ===
@router.get("/settings/knowledge")
async def get_knowledge_settings(session: Dict[str, Any] = Depends(require_admin_auth)) -> Dict[str, Any]:
    """Get knowledge indexing and synchronization settings."""
    try:
        settings_mgr = get_settings_manager()
        settings = settings_mgr.get_knowledge_settings()
        return {"settings": settings.to_dict()}
    except Exception as e:
        logger.error(f"Error getting knowledge settings: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching knowledge settings")


@router.put("/settings/knowledge")
async def update_knowledge_settings(
    request: Request, settings_data: Dict[str, Any], session: Dict[str, Any] = Depends(require_admin_auth)
) -> Dict[str, Any]:
    """Update knowledge indexing and synchronization settings."""
    try:
        settings = KnowledgeSettings.from_dict(settings_data)
        settings_mgr = get_settings_manager()
        success = settings_mgr.set_knowledge_settings(settings, session["user_id"])

        if not success:
            raise HTTPException(status_code=500, detail="Failed to update knowledge settings")

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.CONFIG_UPDATE,
            username=session["username"],
            details={"resource": "knowledge_settings", "new_settings": settings.to_dict()},
            ip_address=client_ip,
            user_agent=user_agent,
        )

        try:
            settings_mgr.invalidate_cache("knowledge_settings")
        except Exception:
            pass

        logger.info(f"Knowledge settings updated by user {session['user_id']}: {settings.to_dict()}")
        return {
            "success": True,
            "message": "Knowledge settings updated successfully",
            "settings": settings.to_dict(),
            "lastUpdated": datetime.now().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating knowledge settings: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error updating knowledge settings")


# === Taxonomy Settings Endpoints ===
@router.get("/settings/taxonomy")
async def get_taxonomy_settings(
    request: Request, session: Dict[str, Any] = Depends(require_admin_auth), db: Session = Depends(get_db_session)
) -> Dict[str, Any]:
    """Get taxonomy configuration used for search/category detection."""
    try:
        # Prefer DB value when present with explicit tenant filter
        tenant_filter = "tenant_id = COALESCE(NULLIF(current_setting('app.tenant_id', true), '')::uuid, CAST(:fallback_tid AS uuid))"
        row = db.execute(
            text(
                f"SELECT setting_value FROM admin_settings WHERE setting_key = 'taxonomy_settings' AND {tenant_filter} LIMIT 1"
            ),
            {
                "fallback_tid": str(
                    getattr(request.state, "tenant_id", None)
                    or os.getenv("DEFAULT_TENANT_ID")
                    or "00000000-0000-0000-0000-000000000001"
                )
            },
        ).first()
        db_value = row[0] if row else None
        if db_value:
            try:
                data = json.loads(db_value)
            except json.JSONDecodeError:
                logger.warning("Stored taxonomy_settings is invalid JSON; falling back to file")
                data = taxonomy_loader.get_topic_taxonomy() or {}
        else:
            data = taxonomy_loader.get_topic_taxonomy() or {}

        return {"settings": data}
    except Exception as e:
        logger.error(f"Error getting taxonomy settings: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching taxonomy settings")


def _validate_taxonomy_payload(payload: Dict[str, Any]) -> None:
    """Validate taxonomy JSON payload; raise HTTPException 400 on error."""
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Payload must be a JSON object")
    categories = payload.get("categories")
    if not isinstance(categories, dict):
        raise HTTPException(status_code=400, detail="Missing or invalid 'categories' object")

    # Optional size guardrail (approximate)
    try:
        size_bytes = len(json.dumps(payload))
        if size_bytes > 256 * 1024:
            raise HTTPException(status_code=400, detail="Taxonomy JSON too large (limit ~256KB)")
    except Exception:
        pass

    # Validate each category
    import re

    for name, cfg in categories.items():
        if not isinstance(name, str) or not name.strip():
            raise HTTPException(status_code=400, detail="Category names must be non-empty strings")
        if not isinstance(cfg, dict):
            raise HTTPException(status_code=400, detail=f"Category '{name}' must be an object")
        syn = cfg.get("synonyms")
        if syn is not None and not isinstance(syn, list):
            raise HTTPException(status_code=400, detail=f"Category '{name}': 'synonyms' must be an array")
        rx = cfg.get("regex")
        if rx is not None and not isinstance(rx, list):
            raise HTTPException(status_code=400, detail=f"Category '{name}': 'regex' must be an array")
        if isinstance(rx, list):
            for pat in rx:
                if not isinstance(pat, str):
                    raise HTTPException(status_code=400, detail=f"Category '{name}': regex entries must be strings")
                try:
                    re.compile(pat)
                except re.error:
                    raise HTTPException(status_code=400, detail=f"Category '{name}': invalid regex '{pat}'")


@router.put("/settings/taxonomy")
async def update_taxonomy_settings(
    request: Request,
    settings_data: Dict[str, Any],
    session: Dict[str, Any] = Depends(require_admin_auth),
    db: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    """Update taxonomy configuration used for search/category detection."""
    try:
        _validate_taxonomy_payload(settings_data)

        # Snapshot previous version to history (best-effort)
        try:
            tenant_filter = "tenant_id = COALESCE(NULLIF(current_setting('app.tenant_id', true), '')::uuid, CAST(:fallback_tid AS uuid))"
            fallback_tid = str(
                getattr(request.state, "tenant_id", None)
                or os.getenv("DEFAULT_TENANT_ID")
                or "00000000-0000-0000-0000-000000000001"
            )
            row_prev = db.execute(
                text(
                    f"SELECT setting_value FROM admin_settings WHERE setting_key = 'taxonomy_settings' AND {tenant_filter} LIMIT 1"
                ),
                {"fallback_tid": fallback_tid},
            ).first()
            prev = row_prev[0] if row_prev else None
            if prev:
                cats = list((settings_data.get("categories") or {}).keys()) if isinstance(settings_data, dict) else []
                db.execute(
                    text(
                        """
                        INSERT INTO taxonomy_settings_history (tenant_id, settings_json, category_count, note, created_at, updated_by)
                        VALUES (current_setting('app.tenant_id')::uuid, :json, :count, :note, now(), :uid)
                        """
                    ),
                    {
                        "json": prev,
                        "count": len(cats),
                        "note": "auto-snapshot before publish",
                        "uid": session["user_id"],
                    },
                )
        except Exception:
            logger.debug("Could not snapshot previous taxonomy settings to history")

        # Persist to DB (current)
        res = db.execute(
            text(
                """
                INSERT INTO admin_settings (tenant_id, setting_key, setting_value, updated_at, updated_by)
                VALUES (current_setting('app.tenant_id')::uuid, 'taxonomy_settings', :val, now(), :uid)
                ON CONFLICT (tenant_id, setting_key)
                DO UPDATE SET setting_value = EXCLUDED.setting_value, updated_at = now(), updated_by = EXCLUDED.updated_by
                """
            ),
            {"val": json.dumps(settings_data), "uid": session["user_id"]},
        )
        # no explicit rowcount reliable on upsert path; assume success if no exception

        # Audit log with summary (avoid logging entire payload if large)
        try:
            cats = list((settings_data.get("categories") or {}).keys())
            summary = {
                "resource": "taxonomy_settings",
                "category_count": len(cats),
                "version": settings_data.get("version"),
                "first_categories": cats[:10],
            }
            client_ip = request.client.host if request.client else "unknown"
            user_agent = request.headers.get("User-Agent", "")
            audit_logger.log_action(
                action=AuditAction.CONFIG_UPDATE,
                username=session["username"],
                details=summary,
                ip_address=client_ip,
                user_agent=user_agent,
            )
        except Exception:
            pass

        # Invalidate taxonomy cache and warm up
        try:
            taxonomy_loader.invalidate_cache()
            taxonomy_loader.get_topic_taxonomy(force_reload=True)
        except Exception:
            logger.debug("Could not warm taxonomy cache after update")

        logger.info(
            f"Taxonomy settings updated by user {session['user_id']}: categories={len((settings_data.get('categories') or {}).keys())}"
        )
        return {
            "success": True,
            "message": "Taxonomy settings updated successfully",
            "settings": settings_data,
            "lastUpdated": datetime.now().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating taxonomy settings: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error updating taxonomy settings")


# === Taxonomy Versioning Endpoints ===
@router.get("/settings/taxonomy/versions")
async def list_taxonomy_versions(
    limit: int = 20,
    offset: int = 0,
    session: Dict[str, Any] = Depends(require_admin_auth),
    db: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    try:
        limit = max(1, min(100, int(limit)))
        offset = max(0, int(offset))
        # Add explicit tenant filter
        tenant_filter = "tenant_id = COALESCE(NULLIF(current_setting('app.tenant_id', true), '')::uuid, CAST(:fallback_tid AS uuid))"
        rows = db.execute(
            text(
                f"""
                SELECT id, created_at, updated_by, note, category_count
                FROM taxonomy_settings_history
                WHERE {tenant_filter}
                ORDER BY id DESC
                LIMIT :limit OFFSET :offset
                """
            ),
            {
                "limit": limit,
                "offset": offset,
                "fallback_tid": str(
                    getattr(request.state, "tenant_id", None)
                    or os.getenv("DEFAULT_TENANT_ID")
                    or "00000000-0000-0000-0000-000000000001"
                ),
            },
        ).fetchall()
        items = [
            {
                "id": int(r[0]),
                "created_at": r[1],
                "updated_by": r[2],
                "note": r[3],
                "category_count": r[4],
            }
            for r in rows
        ]
        return {"versions": items, "limit": limit, "offset": offset}
    except Exception as e:
        logger.error(f"Error listing taxonomy versions: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error listing taxonomy versions")


@router.get("/settings/taxonomy/versions/{version_id}")
async def get_taxonomy_version(
    version_id: int,
    session: Dict[str, Any] = Depends(require_admin_auth),
    db: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    try:
        # Add explicit tenant filter
        tenant_filter = "tenant_id = COALESCE(NULLIF(current_setting('app.tenant_id', true), '')::uuid, CAST(:fallback_tid AS uuid))"
        row = db.execute(
            text(
                f"SELECT id, created_at, updated_by, note, category_count, settings_json FROM taxonomy_settings_history WHERE id = :id AND {tenant_filter}"
            ),
            {
                "id": int(version_id),
                "fallback_tid": str(
                    getattr(request.state, "tenant_id", None)
                    or os.getenv("DEFAULT_TENANT_ID")
                    or "00000000-0000-0000-0000-000000000001"
                ),
            },
        ).first()
        if not row:
            raise HTTPException(status_code=404, detail="Version not found")
        try:
            data = json.loads(row[5]) if row[5] else None
        except json.JSONDecodeError:
            data = None
        version = {
            "id": int(row[0]),
            "created_at": row[1],
            "updated_by": row[2],
            "note": row[3],
            "category_count": row[4],
        }
        return {"version": version, "settings": data}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting taxonomy version {version_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error getting taxonomy version")


@router.post("/settings/taxonomy/versions/{version_id}/restore")
async def restore_taxonomy_version(
    request: Request,
    version_id: int,
    session: Dict[str, Any] = Depends(require_admin_auth),
    db: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    try:
        # Add explicit tenant filter
        tenant_filter = "tenant_id = COALESCE(NULLIF(current_setting('app.tenant_id', true), '')::uuid, CAST(:fallback_tid AS uuid))"
        row = db.execute(
            text(f"SELECT settings_json FROM taxonomy_settings_history WHERE id = :id AND {tenant_filter}"),
            {
                "id": int(version_id),
                "fallback_tid": str(
                    getattr(request.state, "tenant_id", None)
                    or os.getenv("DEFAULT_TENANT_ID")
                    or "00000000-0000-0000-0000-000000000001"
                ),
            },
        ).first()
        if not row:
            raise HTTPException(status_code=404, detail="Version not found")
        raw = row[0]
        if not raw:
            raise HTTPException(status_code=400, detail="Version payload missing")
        data = json.loads(raw)
        _validate_taxonomy_payload(data)

        # Snapshot current before overwriting (best-effort)
        try:
            # Add explicit tenant filter
            tenant_filter = "tenant_id = COALESCE(NULLIF(current_setting('app.tenant_id', true), '')::uuid, CAST(:fallback_tid AS uuid))"
            row_prev = db.execute(
                text(
                    f"SELECT setting_value FROM admin_settings WHERE setting_key = 'taxonomy_settings' AND {tenant_filter} LIMIT 1"
                ),
                {
                    "fallback_tid": str(
                        getattr(request.state, "tenant_id", None)
                        or os.getenv("DEFAULT_TENANT_ID")
                        or "00000000-0000-0000-0000-000000000001"
                    )
                },
            ).first()
            prev = row_prev[0] if row_prev else None
            if prev:
                cats = list((data.get("categories") or {}).keys()) if isinstance(data, dict) else []
                db.execute(
                    text(
                        """
                        INSERT INTO taxonomy_settings_history (tenant_id, settings_json, category_count, note, created_at, updated_by)
                        VALUES (current_setting('app.tenant_id')::uuid, :json, :count, :note, now(), :uid)
                        """
                    ),
                    {
                        "json": prev,
                        "count": len(cats),
                        "note": "auto-snapshot before restore",
                        "uid": session["user_id"],
                    },
                )
        except Exception:
            pass

        # Persist restored version
        db.execute(
            text(
                """
                INSERT INTO admin_settings (tenant_id, setting_key, setting_value, updated_at, updated_by)
                VALUES (current_setting('app.tenant_id')::uuid, 'taxonomy_settings', :val, now(), :uid)
                ON CONFLICT (tenant_id, setting_key)
                DO UPDATE SET setting_value = EXCLUDED.setting_value, updated_at = now(), updated_by = EXCLUDED.updated_by
                """
            ),
            {"val": raw, "uid": session["user_id"]},
        )

        # Invalidate and warm
        try:
            taxonomy_loader.invalidate_cache()
            taxonomy_loader.get_topic_taxonomy(force_reload=True)
        except Exception:
            logger.debug("Could not warm taxonomy cache after restore")

        # Parse optional note from body
        note: str | None = None
        try:
            body = await request.json()
            if isinstance(body, dict):
                note = body.get("note")
        except Exception:
            note = None

        # Audit
        try:
            cats = list((data.get("categories") or {}).keys())
            summary = {
                "resource": "taxonomy_settings_restore",
                "restored_version_id": int(version_id),
                "category_count": len(cats),
                "note": note,
            }
            client_ip = request.client.host if request.client else "unknown"
            user_agent = request.headers.get("User-Agent", "")
            audit_logger.log_action(
                action=AuditAction.CONFIG_UPDATE,
                username=session["username"],
                details=summary,
                ip_address=client_ip,
                user_agent=user_agent,
            )
        except Exception:
            pass

        return {"success": True, "message": "Restored taxonomy version", "version_id": int(version_id)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error restoring taxonomy version {version_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error restoring taxonomy version")


@router.post("/settings/taxonomy/versions")
async def create_taxonomy_version(
    request: Request,
    payload: Dict[str, Any],
    session: Dict[str, Any] = Depends(require_admin_auth),
    db: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    """Create a manual snapshot of taxonomy settings for history (without publishing).

    Body:
      - settings: object (taxonomy JSON); if omitted, snapshot current DB value
      - note: optional string
    """
    try:
        note = None
        settings_obj = None
        if isinstance(payload, dict):
            note = payload.get("note")
            settings_obj = payload.get("settings")

        if settings_obj is None:
            # Use current DB value
            # Add explicit tenant filter
            tenant_filter = "tenant_id = COALESCE(NULLIF(current_setting('app.tenant_id', true), '')::uuid, CAST(:fallback_tid AS uuid))"
            row = db.execute(
                text(
                    f"SELECT setting_value FROM admin_settings WHERE setting_key = 'taxonomy_settings' AND {tenant_filter} LIMIT 1"
                ),
                {
                    "fallback_tid": str(
                        getattr(request.state, "tenant_id", None)
                        or os.getenv("DEFAULT_TENANT_ID")
                        or "00000000-0000-0000-0000-000000000001"
                    )
                },
            ).first()
            current = row[0] if row else None
            if not current:
                raise HTTPException(status_code=400, detail="No current taxonomy to snapshot")
            raw = current
            try:
                settings_obj = json.loads(current)
            except Exception:
                raise HTTPException(status_code=400, detail="Current taxonomy is corrupt; cannot snapshot")
        else:
            # Validate provided settings
            if not isinstance(settings_obj, dict):
                raise HTTPException(status_code=400, detail="settings must be an object")
            _validate_taxonomy_payload(settings_obj)
            raw = json.dumps(settings_obj)

        row_ins = db.execute(
            text(
                """
                INSERT INTO taxonomy_settings_history (tenant_id, settings_json, category_count, note, created_at, updated_by)
                VALUES (current_setting('app.tenant_id')::uuid, :json, :count, :note, now(), :uid)
                RETURNING id
                """
            ),
            {
                "json": raw,
                "count": len((settings_obj.get("categories") or {})),
                "note": note,
                "uid": session["user_id"],
            },
        ).first()
        version_id = int(row_ins[0]) if row_ins else None
        if not version_id:
            raise HTTPException(status_code=500, detail="Failed to create snapshot")

        # Audit
        try:
            cats = list((settings_obj.get("categories") or {}).keys())
            summary = {
                "resource": "taxonomy_settings_snapshot",
                "category_count": len(cats),
                "note": note,
                "version_id": int(version_id),
            }
            client_ip = request.client.host if request.client else "unknown"
            user_agent = request.headers.get("User-Agent", "")
            audit_logger.log_action(
                action=AuditAction.CONFIG_UPDATE,
                username=session["username"],
                details=summary,
                ip_address=client_ip,
                user_agent=user_agent,
            )
        except Exception:
            pass

        return {"success": True, "version_id": int(version_id)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating taxonomy snapshot: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error creating taxonomy snapshot")


@router.post("/settings/taxonomy/auto-generate")
async def auto_generate_taxonomy(
    request: Request,
    options: Dict[str, Any] | None = None,
    session: Dict[str, Any] = Depends(require_admin_auth),
) -> Dict[str, Any]:
    """Generate a taxonomy proposal from indexed content.

    Options (all optional):
      - max_categories: int (default 10)
      - max_synonyms: int (default 12)
      - min_keyword_len: int (default 4)
      - include_filenames: bool (default True)
    """
    try:
        opts = options or {}
        max_categories = int(opts.get("max_categories", 10))
        max_synonyms = int(opts.get("max_synonyms", 12))
        min_kw_len = int(opts.get("min_keyword_len", 4))
        include_filenames = bool(opts.get("include_filenames", True))

        # Load index metadata if present
        persist_dir = "backend/.unified_chroma"
        index_metadata_path = Path(persist_dir) / "index_metadata.json"

        cat_counts: Dict[str, int] = {}
        cat_terms: Dict[str, Dict[str, int]] = {}
        stop = {
            "this",
            "that",
            "with",
            "from",
            "they",
            "were",
            "been",
            "have",
            "will",
            "would",
            "could",
            "about",
            "there",
            "their",
            "which",
            "these",
            "those",
            "into",
            "your",
            "also",
            "some",
            "more",
            "such",
            "like",
            "when",
            "what",
            "where",
            "them",
            "file",
            "json",
            "data",
            "info",
            "index",
            "readme",
        }

        def add_term(category: str, term: str) -> None:
            term_l = term.strip().lower()
            if not term_l:
                return
            if len(term_l) < min_kw_len:
                return
            if term_l in stop:
                return
            if not term_l.isascii():
                return
            cat_terms.setdefault(category, {})
            cat_terms[category][term_l] = cat_terms[category].get(term_l, 0) + 1

        source = "index"
        if index_metadata_path.exists():
            try:
                import json as _json

                with index_metadata_path.open("r", encoding="utf-8") as f:
                    indexed_files = _json.load(f)
                for file_path, entry in indexed_files.items():
                    cls = None
                    if isinstance(entry, dict):
                        cls = entry.get("classification")
                    # Parse categories
                    cats: list[str] = []
                    keywords: list[str] = []
                    if isinstance(cls, dict):
                        # content_type or content_types can be comma-separated
                        raw_ct = cls.get("content_type") or cls.get("content_types") or ""
                        cats = [c.strip().lower() for c in str(raw_ct).split(",") if c and c.strip()]
                        raw_kw = cls.get("content_keywords") or cls.get("file_keywords") or ""
                        keywords = [k.strip() for k in str(raw_kw).split(",") if k and k.strip()]
                    # Tally
                    for c in cats:
                        if not c:
                            continue
                        cat_counts[c] = cat_counts.get(c, 0) + 1
                        for k in keywords:
                            add_term(c, k)
                        if include_filenames:
                            try:
                                stem = Path(file_path).stem
                                # split on non-alnum
                                import re as _re

                                for t in _re.split(r"[^A-Za-z0-9]+", stem):
                                    add_term(c, t)
                            except Exception:
                                pass
            except Exception as e:
                logger.debug(f"Failed to read index metadata for auto-generate: {e}")
        else:
            source = "default"

        # If no categories were discovered, fall back to a sane starter set
        if not cat_counts:
            source = "default"
            seed = {
                "about": ["bio", "background", "introduction"],
                "skills": ["skill", "stack", "technology", "tools"],
                "experience": ["work", "job", "role", "career"],
                "project": ["portfolio", "demo", "case study"],
                "creative": ["art", "illustration", "design", "inspiration"],
                "technical": ["code", "software", "engineering", "api"],
            }
            for c, syns in seed.items():
                cat_counts[c] = 1
                for s in syns:
                    add_term(c, s)

        # Build taxonomy output
        def topk_terms(d: Dict[str, int], k: int) -> list[str]:
            return [w for w, _ in sorted(d.items(), key=lambda x: x[1], reverse=True)[:k]]

        top_cats = [c for c, _ in sorted(cat_counts.items(), key=lambda x: x[1], reverse=True)[:max_categories]]
        categories: Dict[str, Any] = {}
        for c in top_cats:
            syn = topk_terms(cat_terms.get(c, {}), max_synonyms)
            categories[c] = {"synonyms": syn, "regex": [], "metadata": {"is_illustration_data": c == "creative"}}

        proposal = {"version": "1", "categories": categories}

        # Do not persist; return proposal only
        return {"success": True, "settings": proposal, "source": source, "stats": {"categories": len(categories)}}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error auto-generating taxonomy: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error auto-generating taxonomy")


@router.get("/settings/taxonomy/fallback")
async def get_taxonomy_fallback(session: Dict[str, Any] = Depends(require_admin_auth)) -> Dict[str, Any]:
    """Return the current fallback taxonomy JSON from file, if present."""
    try:
        tl_path = Path(taxonomy_loader.__file__).parent / "topic_taxonomy.json"
        if not tl_path.exists():
            return {"exists": False, "settings": None}
        try:
            with tl_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return {"exists": True, "settings": data}
        except json.JSONDecodeError:
            return {"exists": True, "settings": None, "invalid": True}
    except Exception as e:
        logger.error(f"Error getting taxonomy fallback: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching taxonomy fallback")


@router.post("/settings/taxonomy/fallback-file")
async def upload_taxonomy_fallback_file(
    request: Request,
    file: UploadFile = File(...),
    session: Dict[str, Any] = Depends(require_admin_auth),
) -> Dict[str, Any]:
    """Upload a fallback taxonomy JSON file.

    Overwrites existing fallback file if present; creates it otherwise.
    """
    try:
        if not file.filename or not file.filename.lower().endswith(".json"):
            raise HTTPException(status_code=400, detail="Please upload a .json file")

        raw = await file.read()
        try:
            data = json.loads(raw.decode("utf-8"))
        except Exception:
            raise HTTPException(status_code=400, detail="Uploaded file is not valid JSON")

        _validate_taxonomy_payload(data)

        tl_path = Path(taxonomy_loader.__file__).parent / "topic_taxonomy.json"
        try:
            tl_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to write taxonomy fallback file: {e}")
            raise HTTPException(status_code=500, detail="Failed to write fallback file")

        # Audit
        try:
            cats = list((data.get("categories") or {}).keys())
            summary = {
                "resource": "taxonomy_fallback_file",
                "category_count": len(cats),
                "version": data.get("version"),
                "first_categories": cats[:10],
                "filename": file.filename,
            }
            client_ip = request.client.host if request.client else "unknown"
            user_agent = request.headers.get("User-Agent", "")
            audit_logger.log_action(
                action=AuditAction.CONFIG_UPDATE,
                username=session["username"],
                details=summary,
                ip_address=client_ip,
                user_agent=user_agent,
            )
        except Exception:
            pass

        # Invalidate and warm cache
        try:
            taxonomy_loader.invalidate_cache()
            taxonomy_loader.get_topic_taxonomy(force_reload=True)
        except Exception:
            logger.debug("Could not warm taxonomy cache after fallback upload")

        return {"success": True, "message": "Fallback taxonomy file uploaded"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading taxonomy fallback file: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error uploading taxonomy fallback file")


# User Management endpoints
@router.get(
    "/users",
    response_model=List[AdminUser],
    tags=["Admin Management"],
    summary="Get Admin Users",
    description="""
            **Get all admin users with safe information (excluding password hashes).**
            
            **Access Control:**
            - Requires admin authentication
            - Only users with admin role can access
            
            **Returns:**
            - List of admin users with safe fields only
            - User creation and last login timestamps
            - User roles and active status
            
            **Security:**
            - Password hashes are never returned
            - Audit logged for security monitoring
            """,
)
async def get_admin_users(
    request: Request,
    session: Dict[str, Any] = Depends(require_admin_role),
    db: Session = Depends(get_db_session),
) -> List[AdminUser]:
    """Get tenant-scoped admin users (safe information only)."""
    try:
        # Get tenant context from middleware
        tenant_id = getattr(request.state, "tenant_id", None)
        tenant_slug = getattr(request.state, "tenant_slug", None)

        logger.info(f"Fetching users for tenant: {tenant_slug} (ID: {tenant_id})")

        # Query users that are members of the current tenant
        # Using JOIN with tenant_memberships for tenant isolation
        rows = db.execute(
            text(
                """
                SELECT DISTINCT
                    u.id, u.username, u.email, u.role, u.is_active,
                    u.created_at, u.last_login_at, u.updated_at
                FROM admin_users u
                JOIN tenant_memberships tm ON u.id = tm.user_id
                WHERE tm.tenant_id = :tenant_id
                ORDER BY u.username
                """
            ),
            {"tenant_id": tenant_id},
        ).fetchall()

        users = [
            AdminUser(
                id=int(r[0]),
                username=r[1],
                email=r[2],
                role=r[3],
                is_active=bool(r[4]),
                created_at=r[5],
                last_login_at=r[6],
                updated_at=r[7],
            )
            for r in rows
        ]

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.DATA_VIEW,
            username=session["username"],
            details={
                "resource": "admin_users",
                "user_count": len(users),
                "tenant_id": tenant_id,
                "tenant_slug": tenant_slug,
            },
            ip_address=client_ip,
            user_agent=user_agent,
        )

        logger.info(f"Found {len(users)} users for tenant {tenant_slug}")
        return users

    except Exception as e:
        logger.error(f"Error getting admin users: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching admin users")


@router.post(
    "/users",
    tags=["Admin Management"],
    summary="Create Admin User",
    description="""
            **Create a new admin user account.**
            
            **Requirements:**
            - Username must be unique
            - Password must meet security requirements (min 12 characters)
            - Email is optional but recommended
            - Role defaults to 'viewer' if not specified
            
            **Security:**
            - Password is securely hashed with bcrypt
            - Creation is audit logged
            - Only admin users can create other users
            """,
)
async def create_admin_user(
    request: Request,
    user_data: CreateUserRequest,
    session: Dict[str, Any] = Depends(require_admin_role),
    db: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    """Create a new admin user and add them to the current tenant."""
    try:
        # Get tenant context from middleware
        tenant_id = getattr(request.state, "tenant_id", None)
        tenant_slug = getattr(request.state, "tenant_slug", None)

        if not tenant_id:
            raise HTTPException(status_code=400, detail="Tenant context not available")

        # Validate password strength using centralized validator
        try:
            admin_auth_manager.validate_password_strength(user_data.password)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        # Check if username already exists (Postgres)
        exists = db.execute(
            text("SELECT 1 FROM admin_users WHERE username = :un"), {"un": user_data.username.lower()}
        ).first()
        if exists:
            raise HTTPException(status_code=409, detail="Username already exists")

        # Create user in PG via admin_auth_manager (handles hashing)
        user_id = admin_auth_manager.create_admin_user(
            username=user_data.username,
            password=user_data.password,
            email=user_data.email,
            role=user_data.role or "viewer",
        )

        # Add user to current tenant's memberships
        db.execute(
            text(
                """
                INSERT INTO tenant_memberships (tenant_id, user_id, role, created_at)
                VALUES (:tenant_id, :user_id, :role, NOW())
                ON CONFLICT (tenant_id, user_id) DO NOTHING
                """
            ),
            {"tenant_id": tenant_id, "user_id": user_id, "role": user_data.role or "viewer"},
        )
        db.commit()

        logger.info(
            f"Admin user {user_data.username} (ID: {user_id}) created and added to tenant {tenant_slug} (ID: {tenant_id})"
        )

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.USER_CREATE,
            username=session["username"],
            details={
                "resource": "admin_user",
                "new_user_id": user_id,
                "new_username": user_data.username,
                "new_role": user_data.role or "viewer",
                "created_by": session["user_id"],
                "tenant_id": tenant_id,
                "tenant_slug": tenant_slug,
            },
            ip_address=client_ip,
            user_agent=user_agent,
        )

        # Return safe user data (no password hash)
        row = db.execute(
            text(
                "SELECT id, username, email, role, is_active, created_at, last_login_at, updated_at FROM admin_users WHERE id = :id"
            ),
            {"id": user_id},
        ).first()
        if row:
            safe_user = {
                "id": int(row[0]),
                "username": row[1],
                "email": row[2],
                "role": row[3],
                "is_active": bool(row[4]),
                "created_at": row[5],
                "last_login_at": row[6],
                "updated_at": row[7],
            }
            return {"success": True, "message": "User created successfully", "user": safe_user}
        return {"success": True, "message": "User created successfully", "user_id": user_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating admin user: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error creating admin user")


@router.put(
    "/users/{user_id}/deactivate",
    tags=["Admin Management"],
    summary="Deactivate Admin User",
    description="""
            **Deactivate an admin user account.**
            
            **Actions Performed:**
            - Sets user as inactive
            - Expires all user sessions immediately
            - User cannot log in until reactivated
            
            **Security:**
            - Cannot deactivate your own account (prevents lockout)
            - Action is audit logged
            - All user sessions are terminated
            """,
)
async def deactivate_admin_user(
    request: Request,
    user_id: int,
    session: Dict[str, Any] = Depends(require_admin_role),
    db: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    """Deactivate an admin user."""
    try:
        # Prevent self-deactivation
        if user_id == session["user_id"]:
            raise HTTPException(status_code=400, detail="Cannot deactivate your own account")

        # Check if user exists
        row = db.execute(text("SELECT id, username FROM admin_users WHERE id = :id"), {"id": user_id}).first()
        if not row:
            raise HTTPException(status_code=404, detail="User not found")

        # Deactivate user
        res = db.execute(
            text("UPDATE admin_users SET is_active = false, updated_at = now() WHERE id = :id"), {"id": user_id}
        )
        if (res.rowcount or 0) == 0:
            raise HTTPException(status_code=500, detail="Failed to deactivate user")
        try:
            admin_auth_manager.expire_user_sessions(user_id)
        except Exception:
            pass

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.USER_DEACTIVATE,
            username=session["username"],
            details={
                "resource": "admin_user",
                "target_user_id": user_id,
                "target_username": row[1],
                "deactivated_by": session["user_id"],
            },
            ip_address=client_ip,
            user_agent=user_agent,
        )

        logger.info(f"Admin user {user_id} deactivated by user {session['user_id']}")

        return {"success": True, "message": "User deactivated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deactivating admin user: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error deactivating admin user")


@router.post(
    "/users/{user_id}/reactivate",
    tags=["Admin Management"],
    summary="Reactivate a deactivated admin user",
    description="""
            **Reactivate a deactivated admin user account.**
            
            **Actions Performed:**
            - Sets user as active
            - User can log in again
            
            **Security:**
            - Cannot reactivate your own account (must be active to use this endpoint)
            - Action is audit logged
            """,
)
async def reactivate_admin_user(
    user_id: int,
    request: Request,
    session: Dict[str, Any] = Depends(require_admin_role),
    db: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    """Reactivate a deactivated admin user account."""
    try:
        current_user_id = session["user_id"]
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        # Get user info before reactivation
        row = db.execute(
            text("SELECT id, username, is_active FROM admin_users WHERE id = :id"), {"id": user_id}
        ).first()
        if not row:
            raise HTTPException(status_code=404, detail="User not found")

        if bool(row[2]):
            raise HTTPException(status_code=400, detail="User is already active")

        # Reactivate the user
        res = db.execute(
            text("UPDATE admin_users SET is_active = true, updated_at = now() WHERE id = :id"), {"id": user_id}
        )
        if (res.rowcount or 0) > 0:
            # Log the action
            audit_logger.log_action(
                action=AuditAction.USER_REACTIVATE,
                username=session["username"],
                details={
                    "resource": "admin_user",
                    "target_user_id": user_id,
                    "target_username": row[1],
                    "reactivated_by": current_user_id,
                },
                ip_address=client_ip,
                user_agent=user_agent,
            )
            logger.info(f"Admin user {user_id} reactivated by user {current_user_id}")
            return {"success": True, "message": f"User {row[1]} reactivated successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to reactivate user")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reactivating admin user: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error reactivating admin user")


@router.post(
    "/users/bulk/deactivate",
    tags=["Admin Management"],
    summary="Bulk deactivate admin users",
    description="""
            **Deactivate multiple admin users at once.**
            
            **Actions Performed:**
            - Sets users as inactive
            - Expires all user sessions immediately for each user
            - Users cannot log in until reactivated
            
            **Security:**
            - Cannot deactivate your own account (prevents lockout)
            - Action is audit logged for each user
            - All user sessions are terminated for each deactivated user
            
            **Request Format:**
            ```json
            {
                "user_ids": [1, 2, 3]
            }
            ```
            """,
)
async def bulk_deactivate_admin_users(
    bulk_request: BulkDeactivateUsersRequest,
    request: Request,
    session: Dict[str, Any] = Depends(require_admin_role),
    db: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    """Deactivate multiple admin users at once."""
    try:
        user_ids = bulk_request.user_ids
        current_user_id = session["user_id"]
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        # Validate request
        if not user_ids:
            raise HTTPException(status_code=400, detail="No user IDs provided")

        if len(user_ids) > 50:
            raise HTTPException(status_code=400, detail="Cannot deactivate more than 50 users at once")

        # Prevent self-deactivation
        if current_user_id in user_ids:
            raise HTTPException(status_code=400, detail="Cannot deactivate your own account")

        # Fetch user info from Postgres (acceptable to loop for <=50)
        user_infos = {}
        for uid in user_ids:
            row = db.execute(
                text("SELECT id, username, is_active FROM admin_users WHERE id = :id"), {"id": uid}
            ).first()
            if row:
                user_infos[uid] = {"id": row[0], "username": row[1], "is_active": bool(row[2])}

        # Check if all requested users were found
        missing_user_ids = [user_id for user_id in user_ids if user_id not in user_infos]
        if missing_user_ids:
            if len(missing_user_ids) == 1:
                raise HTTPException(status_code=404, detail=f"User with ID {missing_user_ids[0]} not found")
            else:
                raise HTTPException(status_code=404, detail=f"Users with IDs {missing_user_ids} not found")

        # Deactivate users
        successful_deactivations = []
        failed_deactivations = []

        for user_id in user_ids:
            try:
                res = db.execute(
                    text("UPDATE admin_users SET is_active = false, updated_at = now() WHERE id = :id"), {"id": user_id}
                )
                if (res.rowcount or 0) > 0:
                    successful_deactivations.append(user_id)
                    try:
                        admin_auth_manager.expire_user_sessions(user_id)
                    except Exception:
                        pass

                    # Log audit entry for each deactivation
                    audit_logger.log_action(
                        action=AuditAction.USER_DEACTIVATE,
                        username=session["username"],
                        details={
                            "resource": "admin_user",
                            "target_user_id": user_id,
                            "target_username": user_infos[user_id].get("username"),
                            "deactivated_by": current_user_id,
                            "bulk_operation": True,
                        },
                        ip_address=client_ip,
                        user_agent=user_agent,
                    )
                else:
                    failed_deactivations.append(user_id)
            except Exception as e:
                logger.error(f"Error deactivating user {user_id}: {str(e)}")
                failed_deactivations.append(user_id)

        # Log summary
        logger.info(
            f"Bulk deactivation completed by user {current_user_id}: "
            f"{len(successful_deactivations)} successful, {len(failed_deactivations)} failed"
        )

        # Prepare response
        response_data = {
            "success": True,
            "total_requested": len(user_ids),
            "successful_deactivations": len(successful_deactivations),
            "failed_deactivations": len(failed_deactivations),
            "deactivated_user_ids": successful_deactivations,
        }

        if failed_deactivations:
            response_data["failed_user_ids"] = failed_deactivations
            response_data["message"] = (
                f"Bulk deactivation partially completed. "
                f"{len(successful_deactivations)} users deactivated, "
                f"{len(failed_deactivations)} failed."
            )
        else:
            response_data["message"] = f"Successfully deactivated {len(successful_deactivations)} users"

        return response_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in bulk deactivate admin users: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error deactivating admin users")


@router.delete(
    "/users/bulk",
    summary="Bulk delete admin users",
    description="Permanently delete multiple admin users at once. This action cannot be undone.",
)
async def bulk_delete_admin_users(
    bulk_request: BulkDeleteUsersRequest,
    request: Request,
    session: Dict[str, Any] = Depends(require_admin_role),
    db: Session = Depends(get_db_session),
):
    """
    Permanently delete multiple admin users at once.

    Security restrictions:
        - Cannot delete your own account (prevents lockout)
        - Only admin users can delete other users
        - All deletions are logged for audit purposes
        - Terminates all sessions for deleted users
    """
    try:
        user_ids = bulk_request.user_ids
        current_user_id = session["user_id"]

        # Prevent self-deletion to avoid lockout
        if current_user_id in user_ids:
            raise HTTPException(status_code=400, detail="Cannot delete your own account in bulk operation")

        # Track successful deletions and failures
        successful_deletions = []
        failed_deletions = []
        audit_entries = []

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        # Load all users from Postgres (loop acceptable for <=50)
        users_to_delete = {}
        for uid in user_ids:
            row = db.execute(text("SELECT id, username FROM admin_users WHERE id = :id"), {"id": uid}).first()
            if row:
                users_to_delete[uid] = {"id": row[0], "username": row[1]}

        # Process each user deletion
        for user_id in user_ids:
            try:
                # Get user info from our batch fetch
                user_to_delete = users_to_delete.get(user_id)
                if not user_to_delete:
                    failed_deletions.append({"user_id": user_id, "error": "User not found"})
                    continue

                # Permanently delete the user (sessions cascade)
                res = db.execute(text("DELETE FROM admin_users WHERE id = :id"), {"id": user_id})
                if (res.rowcount or 0) == 0:
                    failed_deletions.append(
                        {
                            "user_id": user_id,
                            "username": user_to_delete["username"],
                            "error": "Failed to delete user from database",
                        }
                    )
                    continue

                # Track successful deletion
                successful_deletions.append({"user_id": user_id, "username": user_to_delete["username"]})

                # Prepare audit entry
                audit_entries.append(
                    {
                        "deleted_user_id": user_id,
                        "deleted_username": user_to_delete["username"],
                    }
                )

            except Exception as e:
                failed_deletions.append({"user_id": user_id, "error": f"Unexpected error: {str(e)}"})

        # Log all successful deletions in a single audit entry
        if successful_deletions:
            audit_logger.log_action(
                action=AuditAction.USER_DELETE,
                username=session["username"],
                details={
                    "bulk_operation": True,
                    "deleted_users": audit_entries,
                    "deleted_by": current_user_id,
                    "total_deleted": len(successful_deletions),
                },
                ip_address=client_ip,
                user_agent=user_agent,
            )

            logger.info(
                f"Bulk deletion: {len(successful_deletions)} users deleted by user {current_user_id}. "
                f"Users: {[d['username'] for d in successful_deletions]}"
            )

        # Prepare response
        response_data = {
            "success": len(failed_deletions) == 0,
            "total_requested": len(user_ids),
            "successful_deletions": len(successful_deletions),
            "failed_deletions": len(failed_deletions),
        }

        if successful_deletions:
            response_data["deleted_users"] = [d["username"] for d in successful_deletions]

        if failed_deletions:
            response_data["failures"] = failed_deletions

        if len(successful_deletions) > 0 and len(failed_deletions) == 0:
            response_data["message"] = f"Successfully deleted {len(successful_deletions)} user(s)"
        elif len(successful_deletions) > 0 and len(failed_deletions) > 0:
            response_data["message"] = (
                f"Partially completed: {len(successful_deletions)} deleted, {len(failed_deletions)} failed"
            )
        else:
            response_data["message"] = "No users were deleted due to errors"

        return response_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in bulk delete admin users: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error processing bulk delete operation")


@router.delete(
    "/users/{user_id}",
    summary="Permanently delete admin user",
    description="Permanently delete an admin user account. This action cannot be undone.",
    dependencies=[Depends(require_admin_auth)],
)
async def delete_admin_user(
    user_id: int,
    request: Request,
    session: Dict[str, Any] = Depends(require_admin_role),
    db: Session = Depends(get_db_session),
):
    """
    Permanently delete an admin user account.

    Security restrictions:
        - Cannot delete your own account (prevents lockout)
        - Only admin users can delete other users
        - Action is logged for audit purposes
        - Terminates all sessions for the deleted user
    """
    try:
        # Prevent self-deletion to avoid lockout
        if user_id == session["user_id"]:
            raise HTTPException(status_code=400, detail="Cannot delete your own account")

        # Get user info before deletion for audit logging
        row = db.execute(text("SELECT id, username FROM admin_users WHERE id = :id"), {"id": user_id}).first()
        if not row:
            raise HTTPException(status_code=404, detail="User not found")

        # Permanently delete the user (sessions cascade)
        res = db.execute(text("DELETE FROM admin_users WHERE id = :id"), {"id": user_id})
        if (res.rowcount or 0) == 0:
            raise HTTPException(status_code=500, detail="Failed to delete user")

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        # Audit log deletion
        audit_logger.log_action(
            action=AuditAction.USER_DELETE,
            username=session["username"],
            details={
                "deleted_user_id": user_id,
                "deleted_username": row[1],
                "deleted_by": session["user_id"],
            },
            ip_address=client_ip,
            user_agent=user_agent,
        )

        logger.info(f"Admin user {user_id} ({row[1]}) permanently deleted by user {session['user_id']}")

        return {"success": True, "message": "User permanently deleted"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting admin user: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error deleting admin user")
