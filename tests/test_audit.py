"""
QueryPilot — Audit Service Tests
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.audit_service import AuditService
from app.models.user import User


@pytest.mark.asyncio
async def test_audit_log_query_and_retrieve(db_session: AsyncSession, test_user: User):
    service = AuditService()

    # Log query
    log_entry = await service.log_query(
        db=db_session,
        user_id=test_user.id,
        session_id="session-123",
        connection_id="conn-456",
        natural_language_input="Show all orders from last week",
        sql_generated="SELECT * FROM orders WHERE created_at > NOW() - INTERVAL '7 days'",
        sql_executed="SELECT * FROM orders WHERE created_at > NOW() - INTERVAL '7 days' LIMIT 1000",
        rows_returned=42,
        execution_time_ms=15.5,
        status="success",
    )
    assert log_entry.id is not None
    assert log_entry.rows_returned == 42
    assert log_entry.status == "success"

    # Query logs
    res = await service.get_logs(
        db=db_session,
        user_id=test_user.id,
        page=1,
        page_size=10,
    )
    assert res["total"] >= 1
    assert any(l.id == log_entry.id for l in res["logs"])

    # Get stats
    stats = await service.get_stats(db=db_session)
    assert stats["total_queries"] >= 1
    assert stats["queries_today"] >= 1
    assert stats["error_rate"] == 0.0
