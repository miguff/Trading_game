"""Admin authentication module for Energy Trading Game."""

import os
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict
from fastapi import Request, HTTPException, Depends
from fastapi.responses import Response

# Admin PIN configuration
ADMIN_PIN = os.environ.get("ADMIN_PIN", "1234")
if ADMIN_PIN == "1234":
    import logging
    logging.warning("ADMIN_PIN not set. Using development default '1234'. Set ADMIN_PIN env var for production.")

# In-memory session storage (no database for MVP)
SESSIONS: Dict[str, datetime] = {}  # token -> expires_at
SESSION_DURATION_HOURS = 8


def validate_pin(pin: str) -> bool:
    """Validate admin PIN."""
    return pin == ADMIN_PIN


def create_session() -> tuple[str, datetime]:
    """Create a new admin session."""
    token = str(uuid.uuid4())
    expires = datetime.utcnow() + timedelta(hours=SESSION_DURATION_HOURS)
    SESSIONS[token] = expires
    return token, expires


def validate_session(token: Optional[str]) -> bool:
    """Validate if session token is active and not expired."""
    if not token:
        return False
    expires = SESSIONS.get(token)
    if not expires:
        return False
    if datetime.utcnow() > expires:
        # Clean up expired session
        del SESSIONS[token]
        return False
    return True


def invalidate_session(token: str) -> None:
    """Invalidate an admin session."""
    SESSIONS.pop(token, None)


def require_admin(request: Request) -> str:
    """FastAPI dependency to require admin authentication."""
    token = request.cookies.get("admin_session")
    if not validate_session(token):
        raise HTTPException(status_code=401, detail="Admin authentication required")
    return token


def get_admin_status(request: Request) -> dict:
    """Get admin authentication status for status endpoint."""
    token = request.cookies.get("admin_session")
    is_authenticated = validate_session(token)
    return {
        "authenticated": is_authenticated,
        "session_valid": is_authenticated
    }
