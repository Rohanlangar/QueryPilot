"""
Auth schemas — request/response models for authentication endpoints.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


# ── Requests ──────────────────────────────────────────────────

class UserRegister(BaseModel):
    """Registration request body."""
    email: str = Field(..., min_length=5, max_length=255, examples=["analyst@company.com"])
    username: str = Field(..., min_length=3, max_length=100, examples=["john_doe"])
    password: str = Field(..., min_length=8, max_length=128)
    full_name: Optional[str] = Field(None, max_length=255, examples=["John Doe"])


class UserLogin(BaseModel):
    """Login request body."""
    username: str = Field(..., examples=["john_doe"])
    password: str = Field(...)


class TokenRefresh(BaseModel):
    """Token refresh request body."""
    token: str


# ── Responses ─────────────────────────────────────────────────

class TokenResponse(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class UserResponse(BaseModel):
    """Public user profile response."""
    id: str
    email: str
    username: str
    full_name: Optional[str]
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    """User profile update request."""
    full_name: Optional[str] = None
    email: Optional[str] = None
