"""
QueryPilot — RBAC Engine Tests
"""

import json
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import RBACEngine
from app.models.connection import Connection
from app.models.rbac import TablePolicy, Role
from app.models.user import User


@pytest.mark.asyncio
async def test_rbac_admin_full_access(db_session: AsyncSession, test_admin: User):
    engine = RBACEngine()
    result = await engine.check_table_access(
        user=test_admin,
        connection_id="conn-123",
        table_names=["salaries", "users", "confidential_reports"],
        db=db_session,
    )
    assert result["allowed"] is True
    assert len(result["blocked_tables"]) == 0


@pytest.mark.asyncio
async def test_rbac_policy_blocking_table(
    db_session: AsyncSession, test_user: User, test_roles
):
    engine = RBACEngine()
    analyst_role = next(r for r in test_roles if r.name == "analyst")

    # Create dummy connection
    conn = Connection(
        id="conn-test",
        user_id=test_user.id,
        name="Prod DB",
        db_type="postgresql",
        host="localhost",
        port=5432,
        database_name="prod",
        username="reader",
        encrypted_password="enc",
    )
    db_session.add(conn)

    # Add policy blocking 'exec_compensation'
    policy = TablePolicy(
        role_id=analyst_role.id,
        connection_id=conn.id,
        table_name="exec_compensation",
        allowed=False,
    )
    db_session.add(policy)
    await db_session.commit()

    # Query with allowed table
    res1 = await engine.check_table_access(
        user=test_user,
        connection_id=conn.id,
        table_names=["orders", "products"],
        db=db_session,
    )
    assert res1["allowed"] is True

    # Query with blocked table
    res2 = await engine.check_table_access(
        user=test_user,
        connection_id=conn.id,
        table_names=["orders", "exec_compensation"],
        db=db_session,
    )
    assert res2["allowed"] is False
    assert "exec_compensation" in res2["blocked_tables"]


@pytest.mark.asyncio
async def test_rbac_sensitive_and_blocked_columns(
    db_session: AsyncSession, test_user: User, test_roles
):
    engine = RBACEngine()
    analyst_role = next(r for r in test_roles if r.name == "analyst")

    conn = Connection(
        id="conn-test-2",
        user_id=test_user.id,
        name="HR DB",
        db_type="postgresql",
        host="localhost",
        port=5432,
        database_name="hr",
        username="reader",
        encrypted_password="enc",
    )
    db_session.add(conn)

    policy = TablePolicy(
        role_id=analyst_role.id,
        connection_id=conn.id,
        table_name="employees",
        allowed=True,
        sensitive_columns=json.dumps(["email", "phone_number"]),
        blocked_columns=json.dumps(["ssn", "base_salary"]),
    )
    db_session.add(policy)
    await db_session.commit()

    col_rules = await engine.get_sensitive_columns(
        user=test_user,
        connection_id=conn.id,
        table_name="employees",
        db=db_session,
    )

    assert "email" in col_rules["sensitive"]
    assert "phone_number" in col_rules["sensitive"]
    assert "ssn" in col_rules["blocked"]
    assert "base_salary" in col_rules["blocked"]
