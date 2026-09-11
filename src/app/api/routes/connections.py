"""
QueryPilot — Connection Management Routes

CRUD endpoints for managing external database connections.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.connection import Connection
from app.models.user import User
from app.core.security import get_current_user, encrypt_credential
from app.services.connection_manager import connection_manager
from app.services.schema_introspector import schema_introspector
from app.schemas.connection import (
    ConnectionCreate,
    ConnectionUpdate,
    ConnectionResponse,
    ConnectionTestResult,
    ConnectionTestParams,
)

router = APIRouter(prefix="/api/connections", tags=["Connections"])


@router.post("/test-params", response_model=ConnectionTestResult)
async def test_connection_params(
    body: ConnectionTestParams,
    user: User = Depends(get_current_user),
):
    """Test connectivity using raw connection parameters before saving."""
    result = await connection_manager.test_raw_connection(
        db_type=body.db_type,
        host=body.host,
        port=body.port,
        database_name=body.database_name,
        username=body.username,
        password=body.password,
        ssl_enabled=body.ssl_enabled,
        extra_params=body.extra_params,
    )
    return ConnectionTestResult(**result)


@router.post("", response_model=ConnectionResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=ConnectionResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
async def create_connection(
    body: ConnectionCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Save a new database connection with encrypted credentials."""
    conn = Connection(
        user_id=user.id,
        name=body.name,
        db_type=body.db_type,
        host=body.host,
        port=body.port,
        database_name=body.database_name,
        username=body.username,
        encrypted_password=encrypt_credential(body.password),
        ssl_enabled=body.ssl_enabled,
        extra_params=body.extra_params,
    )
    db.add(conn)
    await db.commit()
    await db.refresh(conn)
    return conn


@router.get("", response_model=list[ConnectionResponse])
@router.get("/", response_model=list[ConnectionResponse], include_in_schema=False)
async def list_connections(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List the current user's saved database connections."""
    result = await db.execute(
        select(Connection)
        .where(Connection.user_id == user.id)
        .order_by(Connection.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{connection_id}", response_model=ConnectionResponse)
async def get_connection(
    connection_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific connection's details."""
    result = await db.execute(
        select(Connection).where(
            Connection.id == connection_id,
            Connection.user_id == user.id,
        )
    )
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")
    return conn


@router.patch("/{connection_id}", response_model=ConnectionResponse)
async def update_connection(
    connection_id: str,
    body: ConnectionUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a saved connection."""
    result = await db.execute(
        select(Connection).where(
            Connection.id == connection_id,
            Connection.user_id == user.id,
        )
    )
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")

    if body.name is not None:
        conn.name = body.name
    if body.host is not None:
        conn.host = body.host
    if body.port is not None:
        conn.port = body.port
    if body.database_name is not None:
        conn.database_name = body.database_name
    if body.username is not None:
        conn.username = body.username
    if body.password is not None:
        conn.encrypted_password = encrypt_credential(body.password)
    if body.ssl_enabled is not None:
        conn.ssl_enabled = body.ssl_enabled
    if body.extra_params is not None:
        conn.extra_params = body.extra_params
    if body.is_active is not None:
        conn.is_active = body.is_active

    # Invalidate cached engine since connection params changed
    await connection_manager.close_connection(connection_id)

    await db.commit()
    await db.refresh(conn)
    return conn


@router.delete("/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_connection(
    connection_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a saved connection."""
    result = await db.execute(
        select(Connection).where(
            Connection.id == connection_id,
            Connection.user_id == user.id,
        )
    )
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")

    await connection_manager.close_connection(connection_id)
    await db.delete(conn)
    await db.commit()


@router.post("/{connection_id}/test", response_model=ConnectionTestResult)
async def test_connection(
    connection_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Test connectivity to an external database."""
    result = await db.execute(
        select(Connection).where(
            Connection.id == connection_id,
            Connection.user_id == user.id,
        )
    )
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")

    test_result = await connection_manager.test_connection(conn)

    if test_result["success"]:
        conn.last_tested_at = datetime.now(timezone.utc)
        await db.flush()

    return ConnectionTestResult(**test_result)


@router.get("/{connection_id}/schema")
async def get_connection_schema(
    connection_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get cached schema metadata for a connection."""
    result = await db.execute(
        select(Connection).where(
            Connection.id == connection_id,
            Connection.user_id == user.id,
        )
    )
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")

    tables = await schema_introspector.get_tables(connection_id, db)
    return {
        "connection_id": connection_id,
        "database_name": conn.database_name,
        "tables": tables,
        "total_tables": len(tables),
    }


@router.post("/{connection_id}/toggle-active", response_model=ConnectionResponse)
async def toggle_connection_active(
    connection_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Toggle whether a connection is active for multi-database query federation."""
    result = await db.execute(
        select(Connection).where(
            Connection.id == connection_id,
            Connection.user_id == user.id,
        )
    )
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")

    conn.is_active = not conn.is_active
    await db.commit()
    await db.refresh(conn)
    return conn


@router.get("/active/schemas")
async def get_all_active_schemas(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get schemas for all active database connections for the current user."""
    result = await db.execute(
        select(Connection).where(
            Connection.user_id == user.id,
            Connection.is_active == True,
        )
    )
    active_conns = result.scalars().all()
    schemas = {}
    for conn in active_conns:
        tables = await schema_introspector.get_tables(conn.id, db)
        schemas[conn.database_name or conn.name] = {
            "connection_id": conn.id,
            "database_name": conn.database_name,
            "db_type": conn.db_type,
            "tables": tables,
            "table_count": len(tables),
        }

    return {
        "active_count": len(active_conns),
        "databases": schemas,
    }
