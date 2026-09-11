"""
Admin schemas — request/response models for admin management endpoints.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class RoleCreate(BaseModel):
    """Create a new role."""
    name: str = Field(..., max_length=50, examples=["analyst"])
    description: Optional[str] = None
    can_manage_users: bool = False
    can_manage_connections: bool = False
    can_manage_policies: bool = False
    can_view_audit: bool = False


class RoleResponse(BaseModel):
    """Role details response."""
    id: str
    name: str
    description: Optional[str] = None
    can_manage_users: bool
    can_manage_connections: bool
    can_manage_policies: bool
    can_view_audit: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TablePolicyCreate(BaseModel):
    """Create a table access policy."""
    role_id: str
    connection_id: str
    table_name: str = Field(..., max_length=255)
    allowed: bool = True
    sensitive_columns: Optional[List[str]] = None   # Columns to mask
    blocked_columns: Optional[List[str]] = None      # Columns to hide entirely


class TablePolicyResponse(BaseModel):
    """Table policy response."""
    id: str
    role_id: str
    connection_id: str
    table_name: str
    allowed: bool
    sensitive_columns: Optional[str] = None
    blocked_columns: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserRoleUpdate(BaseModel):
    """Update a user's role."""
    role: str = Field(..., examples=["admin", "analyst", "viewer"])
