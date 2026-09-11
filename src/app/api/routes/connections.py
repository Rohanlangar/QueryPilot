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
from app.models.schema_metadata import SchemaMetadata
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


@router.get("/{connection_id}/erd")
async def get_connection_erd(
    connection_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get full Entity-Relationship Diagram (ERD) data for a connection,
    including table definitions, columns with primary/foreign keys, and relationships.
    """
    result = await db.execute(
        select(Connection).where(
            Connection.id == connection_id,
            Connection.user_id == user.id,
        )
    )
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")

    # Fetch stored columns from SchemaMetadata
    meta_result = await db.execute(
        select(SchemaMetadata)
        .where(SchemaMetadata.connection_id == connection_id)
        .order_by(SchemaMetadata.table_name, SchemaMetadata.ordinal_position)
    )
    metadata_rows = meta_result.scalars().all()

    # If empty, attempt live sync
    if not metadata_rows:
        try:
            engine = await connection_manager.create_engine(conn)
            await schema_introspector.sync_schema(engine, connection_id, db)
            meta_result = await db.execute(
                select(SchemaMetadata)
                .where(SchemaMetadata.connection_id == connection_id)
                .order_by(SchemaMetadata.table_name, SchemaMetadata.ordinal_position)
            )
            metadata_rows = meta_result.scalars().all()
        except Exception:
            pass

    if metadata_rows:
        tables_map = {}
        relationships = []
        for row in metadata_rows:
            t_name = row.table_name
            if t_name not in tables_map:
                tables_map[t_name] = {
                    "name": t_name,
                    "schema": row.table_schema or "public",
                    "description": row.table_description or "",
                    "row_count": row.table_row_count or 0,
                    "columns": [],
                    "foreign_keys": [],
                }

            tables_map[t_name]["columns"].append({
                "name": row.column_name,
                "type": row.data_type,
                "is_primary_key": row.is_primary_key,
                "is_foreign_key": row.is_foreign_key,
                "is_nullable": row.is_nullable,
                "is_indexed": row.is_indexed,
                "is_unique": row.is_unique,
            })

            if row.is_foreign_key and row.fk_references_table:
                tables_map[t_name]["foreign_keys"].append({
                    "column": row.column_name,
                    "references_table": row.fk_references_table,
                    "references_column": row.fk_references_column,
                })
                relationships.append({
                    "id": f"{t_name}.{row.column_name}->{row.fk_references_table}.{row.fk_references_column}",
                    "from_table": t_name,
                    "from_column": row.column_name,
                    "to_table": row.fk_references_table,
                    "to_column": row.fk_references_column,
                })

        return {
            "connection_id": connection_id,
            "database_name": conn.database_name,
            "db_type": conn.db_type,
            "tables": list(tables_map.values()),
            "relationships": relationships,
            "is_sample": False,
        }

    # Fallback to rich sample schema matching the user's database structure
    from app.services.mock_erd import get_sample_erd_for_connection
    sample = get_sample_erd_for_connection(conn.database_name, conn.db_type)
    return {
        "connection_id": connection_id,
        "database_name": conn.database_name,
        "db_type": conn.db_type,
        "tables": sample["tables"],
        "relationships": sample["relationships"],
        "is_sample": True,
    }
