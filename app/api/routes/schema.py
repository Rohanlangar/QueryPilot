"""
QueryPilot — Schema Introspection Routes

Endpoints for viewing, syncing, and updating schema metadata.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.connection import Connection
from app.models.schema_metadata import SchemaMetadata
from app.models.user import User
from app.core.security import get_current_user
from app.services.connection_manager import connection_manager
from app.services.schema_introspector import schema_introspector
from app.services.semantic_cache import semantic_cache
from app.schemas.schema import (
    ColumnInfo,
    ColumnUpdate,
    SchemaSyncResult,
    TableDetail,
)

router = APIRouter(prefix="/api/schema", tags=["Schema"])


@router.post("/{connection_id}/sync", response_model=SchemaSyncResult)
async def sync_schema(
    connection_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger a full schema re-sync from the external database."""
    # Verify connection ownership
    result = await db.execute(
        select(Connection).where(
            Connection.id == connection_id,
            Connection.user_id == user.id,
        )
    )
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")

    # Get or create engine
    engine = await connection_manager.create_engine(conn)

    # Run sync
    sync_result = await schema_introspector.sync_schema(engine, connection_id, db)

    # Invalidate semantic cache (schema changed)
    await semantic_cache.invalidate_cache(connection_id, db)

    return SchemaSyncResult(**sync_result)


@router.get("/{connection_id}/tables")
async def list_tables(
    connection_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all tables with row counts for a connection."""
    # Verify connection ownership
    result = await db.execute(
        select(Connection).where(
            Connection.id == connection_id,
            Connection.user_id == user.id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Connection not found")

    tables = await schema_introspector.get_tables(connection_id, db)
    return {"tables": tables, "total": len(tables)}


@router.get("/{connection_id}/tables/{table_name}/columns", response_model=list[ColumnInfo])
async def get_table_columns(
    connection_id: str,
    table_name: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed column metadata for a specific table."""
    # Verify connection ownership
    result = await db.execute(
        select(Connection).where(
            Connection.id == connection_id,
            Connection.user_id == user.id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Connection not found")

    columns = await schema_introspector.get_columns(connection_id, table_name, db)
    if not columns:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found in schema")

    return columns


@router.patch("/{connection_id}/tables/{table_name}/columns/{column_name}")
async def update_column_metadata(
    connection_id: str,
    table_name: str,
    column_name: str,
    body: ColumnUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a column's description or PII tag."""
    result = await db.execute(
        select(SchemaMetadata).where(
            SchemaMetadata.connection_id == connection_id,
            SchemaMetadata.table_name == table_name,
            SchemaMetadata.column_name == column_name,
        )
    )
    metadata = result.scalar_one_or_none()
    if not metadata:
        raise HTTPException(status_code=404, detail="Column not found in schema metadata")

    if body.column_description is not None:
        metadata.column_description = body.column_description
    if body.is_pii is not None:
        metadata.is_pii = body.is_pii
    if body.pii_type is not None:
        metadata.pii_type = body.pii_type

    await db.flush()
    await db.refresh(metadata)
    return {"message": "Column metadata updated", "column": column_name}


@router.get("/{connection_id}/context")
async def get_schema_context(
    connection_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get the compressed schema context for a connection.
    This is what gets passed to the SQL generation agent.
    """
    context = await schema_introspector.get_schema_context(connection_id, None, db)
    return context
