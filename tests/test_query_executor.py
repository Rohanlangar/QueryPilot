"""
QueryPilot — Query Executor Tests
"""

import pytest
from sqlalchemy import text
from app.core.query_executor import QueryExecutor
from tests.conftest import test_engine


def test_validate_read_only_blocks_writes():
    executor = QueryExecutor()

    # Allowed queries
    executor._validate_read_only("SELECT * FROM users")
    executor._validate_read_only("WITH cte AS (SELECT 1) SELECT * FROM cte")

    # Blocked queries
    dangerous = [
        "DROP TABLE users",
        "DELETE FROM orders WHERE id = 1",
        "INSERT INTO users VALUES (1, 'bad')",
        "UPDATE accounts SET balance = 0",
        "TRUNCATE TABLE logs",
        "ALTER TABLE users ADD COLUMN hacked TEXT",
    ]
    for q in dangerous:
        with pytest.raises(ValueError, match="Write operations are not allowed"):
            executor._validate_read_only(q)


def test_enforce_row_limit():
    executor = QueryExecutor()
    query_no_limit = "SELECT * FROM products"
    limited = executor._enforce_row_limit(query_no_limit)
    assert f"LIMIT {executor.max_rows}" in limited

    query_with_limit = "SELECT * FROM products LIMIT 50"
    already_limited = executor._enforce_row_limit(query_with_limit)
    assert already_limited.strip() == query_with_limit


@pytest.mark.asyncio
async def test_execute_query_on_engine():
    executor = QueryExecutor()
    # Execute a simple select query against the test engine
    result = await executor.execute(test_engine, "SELECT 1 AS num, 'hello' AS greeting")
    assert result["columns"] == ["num", "greeting"]
    assert len(result["rows"]) == 1
    assert result["rows"][0]["num"] == 1
    assert result["rows"][0]["greeting"] == "hello"
    assert result["row_count"] == 1
    assert result["execution_time_ms"] >= 0
