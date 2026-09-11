"""
QueryPilot — Schema Introspector Tests
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.schema_introspector import SchemaIntrospector
from app.models.schema_metadata import SchemaMetadata
from tests.conftest import test_engine


@pytest.mark.asyncio
async def test_schema_sync_and_retrieval(db_session: AsyncSession):
    introspector = SchemaIntrospector()
    conn_id = "test-conn-introspect"

    # Run schema sync against test engine
    sync_result = await introspector.sync_schema(
        engine=test_engine,
        connection_id=conn_id,
        db=db_session,
    )

    assert sync_result["connection_id"] == conn_id
    assert sync_result["tables_found"] > 0
    assert sync_result["columns_found"] > 0
    assert len(sync_result["errors"]) == 0

    # Get tables
    tables = await introspector.get_tables(conn_id, db_session)
    assert len(tables) > 0
    table_names = [t["table_name"] for t in tables]
    assert "users" in table_names

    # Get columns for users table
    columns = await introspector.get_columns(conn_id, "users", db_session)
    assert len(columns) > 0
    col_names = [c.column_name for c in columns]
    assert "email" in col_names
    assert "id" in col_names

    # Get compressed schema context for SQL agent
    context = await introspector.get_schema_context(
        connection_id=conn_id,
        table_names=["users"],
        db=db_session,
    )
    assert "users" in context["tables"]
    users_ctx = context["tables"]["users"]
    assert "columns" in users_ctx
    assert any(c["name"] == "email" for c in users_ctx["columns"])
