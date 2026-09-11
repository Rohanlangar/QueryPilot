"""
QueryPilot — Admin Routes

User management, role assignment, and RBAC policy endpoints.
Admin-only access.
"""

import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.user import User
from app.models.rbac import Role, TablePolicy
from app.core.security import get_current_admin
from app.schemas.auth import UserResponse
from app.schemas.admin import (
    RoleCreate,
    RoleResponse,
    TablePolicyCreate,
    TablePolicyResponse,
    UserRoleUpdate,
)

router = APIRouter(prefix="/api/admin", tags=["Admin"])


# ── User Management ──────────────────────────────────────────

@router.get("/users", response_model=list[UserResponse])
async def list_users(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all users (admin only)."""
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    return result.scalars().all()


@router.patch("/users/{user_id}/role", response_model=UserResponse)
async def update_user_role(
    user_id: str,
    body: UserRoleUpdate,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Change a user's role (admin only)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot change your own role")

    user.role = body.role
    await db.flush()
    await db.refresh(user)
    return user


@router.patch("/users/{user_id}/deactivate", response_model=UserResponse)
async def deactivate_user(
    user_id: str,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Deactivate a user account (admin only)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate yourself")

    user.is_active = False
    await db.flush()
    await db.refresh(user)
    return user


# ── Role Management ──────────────────────────────────────────

@router.post("/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    body: RoleCreate,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Create a new role (admin only)."""
    # Check uniqueness
    result = await db.execute(select(Role).where(Role.name == body.name))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Role name already exists")

    role = Role(
        name=body.name,
        description=body.description,
        can_manage_users=body.can_manage_users,
        can_manage_connections=body.can_manage_connections,
        can_manage_policies=body.can_manage_policies,
        can_view_audit=body.can_view_audit,
    )
    db.add(role)
    await db.flush()
    await db.refresh(role)
    return role


@router.get("/roles", response_model=list[RoleResponse])
async def list_roles(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all roles (admin only)."""
    result = await db.execute(select(Role).order_by(Role.name))
    return result.scalars().all()


@router.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: str,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Delete a role (admin only)."""
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    if role.name in ("admin", "analyst", "viewer"):
        raise HTTPException(status_code=400, detail="Cannot delete built-in roles")

    await db.delete(role)
    await db.flush()


# ── Table Policy Management ──────────────────────────────────

@router.post("/policies", response_model=TablePolicyResponse, status_code=status.HTTP_201_CREATED)
async def create_table_policy(
    body: TablePolicyCreate,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Create a table access policy (admin only)."""
    policy = TablePolicy(
        role_id=body.role_id,
        connection_id=body.connection_id,
        table_name=body.table_name,
        allowed=body.allowed,
        sensitive_columns=json.dumps(body.sensitive_columns) if body.sensitive_columns else None,
        blocked_columns=json.dumps(body.blocked_columns) if body.blocked_columns else None,
    )
    db.add(policy)
    await db.flush()
    await db.refresh(policy)
    return policy


@router.get("/policies", response_model=list[TablePolicyResponse])
async def list_policies(
    connection_id: str = None,
    role_id: str = None,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """List table access policies with optional filters (admin only)."""
    query = select(TablePolicy)
    if connection_id:
        query = query.where(TablePolicy.connection_id == connection_id)
    if role_id:
        query = query.where(TablePolicy.role_id == role_id)

    result = await db.execute(query.order_by(TablePolicy.table_name))
    return result.scalars().all()


@router.delete("/policies/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_policy(
    policy_id: str,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Delete a table access policy (admin only)."""
    result = await db.execute(select(TablePolicy).where(TablePolicy.id == policy_id))
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    await db.delete(policy)
    await db.flush()
