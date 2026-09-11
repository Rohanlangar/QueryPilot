"""
QueryPilot — Semantic Cache Tests
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.semantic_cache import SemanticCache


@pytest.mark.asyncio
async def test_cache_normalization():
    cache = SemanticCache()
    norm1 = cache._normalize_question("Show me the top 10 customers by revenue, please!")
    norm2 = cache._normalize_question("What are the top 10 customers by revenue?")
    # Both should reduce to the same set of meaningful words (sorted)
    assert norm1 == norm2
    assert cache._hash_question(norm1) == cache._hash_question(norm2)


@pytest.mark.asyncio
async def test_store_and_check_cache(db_session: AsyncSession):
    cache = SemanticCache()
    conn_id = "conn-cache-test"
    question = "List top 5 products by sales"
    sql = "SELECT product_name, sum(sales) FROM orders GROUP BY product_name ORDER BY 2 DESC LIMIT 5"
    result_data = {"columns": ["product_name", "sales"], "rows": [["Widget", 1000]]}

    # Miss before storing
    entry_miss = await cache.check_cache(question, conn_id, db_session)
    assert entry_miss is None

    # Store in cache
    stored = await cache.store_cache(
        question=question,
        connection_id=conn_id,
        sql_generated=sql,
        result_json=result_data,
        confidence_score=0.95,
        db=db_session,
    )
    assert stored is not None

    # Hit after storing
    entry_hit = await cache.check_cache("Please list the top 5 products by sales!", conn_id, db_session)
    assert entry_hit is not None
    assert entry_hit.sql_generated == sql
    assert entry_hit.hit_count >= 1

    # Invalidate
    deleted_count = await cache.invalidate_cache(conn_id, db_session)
    assert deleted_count == 1

    # Miss after invalidation
    entry_after_inv = await cache.check_cache(question, conn_id, db_session)
    assert entry_after_inv is None
