"""
QueryPilot — Audit Trail Routes

Paginated audit logs and aggregate statistics for admin dashboard.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.user import User
from app.core.security import get_current_admin
from app.services.audit_service import audit_service
from app.schemas.audit import AuditLogListResponse, AuditLogResponse, AuditStats

router = APIRouter(prefix="/api/audit", tags=["Audit"])


@router.get("/logs", response_model=AuditLogListResponse)
async def get_audit_logs(
    user_id: str = None,
    session_id: str = None,
    connection_id: str = None,
    action: str = None,
    status: str = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated audit logs with optional filters (admin only)."""
    result = await audit_service.get_logs(
        db=db,
        user_id=user_id,
        session_id=session_id,
        connection_id=connection_id,
        action=action,
        status=status,
        page=page,
        page_size=page_size,
    )

    return AuditLogListResponse(
        logs=[AuditLogResponse.model_validate(log) for log in result["logs"]],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
        total_pages=result["total_pages"],
    )


@router.get("/stats", response_model=AuditStats)
async def get_audit_stats(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get aggregate audit statistics (admin only)."""
    stats = await audit_service.get_stats(db)
    return AuditStats(**stats)
