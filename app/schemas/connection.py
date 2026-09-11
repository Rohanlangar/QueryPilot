"""
Connection schemas — request/response models for DB connection management.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ConnectionCreate(BaseModel):
    """Request body for creating a new database connection."""
    name: str = Field(..., max_length=255, examples=["Production PostgreSQL"])
    db_type: str = Field(
        ..., pattern="^(postgresql|mysql|mssql|oracle)$",
        examples=["postgresql"],
    )
    host: str = Field(..., max_length=255, examples=["db.example.com"])
    port: int = Field(..., ge=1, le=65535, examples=[5432])
    database_name: str = Field(..., max_length=255, examples=["analytics_db"])
    username: str = Field(..., max_length=255, examples=["readonly_user"])
    password: str = Field(..., max_length=500)
    ssl_enabled: bool = False
    extra_params: Optional[str] = None  # JSON string


class ConnectionUpdate(BaseModel):
    """Request body for updating a connection."""
    name: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    database_name: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    ssl_enabled: Optional[bool] = None
    extra_params: Optional[str] = None


class ConnectionResponse(BaseModel):
    """Connection info response (password excluded)."""
    id: str
    name: str
    db_type: str
    host: str
    port: int
    database_name: str
    username: str
    ssl_enabled: bool
    is_active: bool
    last_tested_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConnectionTestResult(BaseModel):
    """Result of testing a database connection."""
    success: bool
    message: str
    latency_ms: Optional[float] = None
