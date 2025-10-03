"""
Admin refresh endpoint for the main backend.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address

from ..core.admin_auth import require_admin_auth

logger = logging.getLogger(__name__)

# Initialize rate limiter for admin refresh endpoints
# Check if we're in testing environment to disable rate limiting
import os

_is_testing = os.getenv("TESTING", "false").lower() == "true" or "pytest" in os.environ.get("_", "")

if _is_testing:
    # Use memory storage during testing to avoid rate limiting issues
    limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")
else:
    limiter = Limiter(key_func=get_remote_address)


router = APIRouter(
    tags=["admin"],
    dependencies=[Depends(require_admin_auth)],
)


class RefreshRequest(BaseModel):
    force_reindex: bool = True


@router.post("/refresh")
@limiter.limit("5/minute")  # Limit refresh requests to 5 per minute
async def trigger_refresh(request: Request, refresh_request: RefreshRequest) -> Dict:
    """
    Trigger a knowledge base refresh.

    This endpoint is called by the admin interface to trigger re-indexing
    of the knowledge base. It sets a flag that will be checked on next startup.
    """
    try:
        # Create refresh flag file
        backend_dir = Path(__file__).parent.parent
        flag_file = backend_dir / ".refresh_required"

        flag_content = f"""refresh_requested_at={datetime.now().isoformat()}
force_reindex={refresh_request.force_reindex}
requested_by=admin_interface
"""

        flag_file.write_text(flag_content)

        logger.info(f"Refresh flag set: force_reindex={refresh_request.force_reindex}")

        return {
            "message": "Refresh flag set successfully",
            "force_reindex": refresh_request.force_reindex,
            "timestamp": datetime.now().isoformat(),
            "note": "Changes will take effect on next server restart",
        }

    except Exception as e:
        logger.error("Failed to set refresh flag: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to set refresh flag: {str(e)}") from e


@router.get("/refresh/status")
@limiter.limit("10/minute")  # Allow more frequent status checks
async def get_refresh_status(request: Request) -> Dict:
    """Get the current refresh status."""
    try:
        backend_dir = Path(__file__).parent.parent
        flag_file = backend_dir / ".refresh_required"

        if flag_file.exists():
            flag_content = flag_file.read_text()
            return {
                "refresh_pending": True,
                "flag_content": flag_content,
                "note": "Refresh will occur on next server restart",
            }
        else:
            return {"refresh_pending": False, "note": "No refresh currently pending"}

    except Exception as e:
        logger.error("Failed to check refresh status: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to check refresh status: {str(e)}") from e
