"""Automated test suite for Multi-Database / Federated SQL Analyst architecture."""

import pytest
import os
import sys

# Ensure proper path
_src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)
_agents_dir = os.path.join(_src_dir, "Agents")
if _agents_dir not in sys.path:
    sys.path.insert(0, _agents_dir)

from db.demo_federated_databases import initialize_demo_federated_databases
from db.connection_manager import (
    get_unified_schema_metadata,
    detect_cross_database_relationships,
)
from agent.query_planner_agent import _heuristic_query_plan
from agent.sql_gen_agent import _generate_single_sql, _build_fallback_sql
from agent.validation_agent import validate_sql
from agent.federation_agent import _hash_join_datasets, _build_execution_diagram
from graph.build_graph import build_graph


@pytest.fixture(scope="module")
def setup_databases():
    """Seed and register demo federated databases."""
    db_paths = initialize_demo_federated_databases()
    return db_paths


def test_schema_discovery_and_relationships(setup_databases):
    """Verify schemas and cross-database key relationships are detected."""
    unified_schema = get_unified_schema_metadata()
    assert "order_db" in unified_schema
    assert "inventory_db" in unified_schema
    assert "payment_db" in unified_schema
    assert "analytics_db" in unified_schema

    rels = detect_cross_database_relationships(unified_schema)
    assert len(rels) >= 2
    # Ensure product_id join key detected between order_db and inventory_db
    prod_rel = next(
        (r for r in rels if r["source_column"] == "product_id" or r["target_column"] == "product_id"),
        None,
    )
    assert prod_rel is not None


def test_query_planner_single_vs_multi(setup_databases):
    """Verify query planner accurately distinguishes single DB vs multi DB."""
    unified_schema = get_unified_schema_metadata()
    rels = detect_cross_database_relationships(unified_schema)

    # Single DB query
    plan_single = _heuristic_query_plan(
        question="What are the total payments this month?",
        unified_schema=unified_schema,
        cross_db_relationships=rels,
    )
    assert plan_single.is_federated is False
    assert "payment_db" in plan_single.required_databases

    # Multi DB federated query
    plan_multi = _heuristic_query_plan(
        question="Which products have high demand but low inventory?",
        unified_schema=unified_schema,
        cross_db_relationships=rels,
    )
    assert plan_multi.is_federated is True
    assert "order_db" in plan_multi.required_databases
    assert "inventory_db" in plan_multi.required_databases


def test_security_validation_blocks_destructive_sql():
    """Verify security rules reject DDL/DML destructive statements."""
    dummy_schema = {"orders": {"columns": {"id": "INTEGER", "product_id": "VARCHAR"}}}
    
    res1 = validate_sql("SELECT product_id FROM orders", dummy_schema)
    assert res1.passed is True

    res2 = validate_sql("DELETE FROM orders WHERE id = 1", dummy_schema)
    assert res2.passed is False
    assert any("prohibited" in e.lower() or "violation" in e.lower() for e in res2.errors)

    res3 = validate_sql("DROP TABLE orders", dummy_schema)
    assert res3.passed is False

    res4 = validate_sql("INSERT INTO orders (id) VALUES (1)", dummy_schema)
    assert res4.passed is False


def test_application_level_hash_join():
    """Verify in-memory hash join correctly joins two independent datasets on join key."""
    order_rows = [
        {"product_id": "P001", "demand": 850},
        {"product_id": "P002", "demand": 420},
        {"product_id": "P003", "demand": 45},
    ]
    inventory_rows = [
        {"product_id": "P001", "product_name": "Headphones", "stock_quantity": 20},
        {"product_id": "P002", "product_name": "Tracker", "stock_quantity": 15},
        {"product_id": "P003", "product_name": "Chair", "stock_quantity": 120},
    ]

    joined = _hash_join_datasets(
        left_rows=inventory_rows,
        right_rows=order_rows,
        left_col="product_id",
        right_col="product_id",
        join_type="inner",
        left_db="inventory_db",
        right_db="order_db",
    )

    assert len(joined) == 3
    p1 = next((r for r in joined if r["product_id"] == "P001"), None)
    assert p1 is not None
    assert p1["demand"] == 850
    assert p1["stock_quantity"] == 20
    assert p1["product_name"] == "Headphones"


def test_full_graph_federated_pipeline(setup_databases):
    """End-to-end LangGraph execution test for multi-database federation."""
    g = build_graph()
    initial_state = {
        "question": "Which products have high demand but low inventory?",
        "user_id": "test_user",
        "user_role": "admin",
        "conversation_history": [],
        "sql_gen_attempts": 0,
    }

    final_state = g.invoke(initial_state)

    assert final_state.get("is_federated") is True
    assert "order_db" in final_state.get("database_queries", {})
    assert "inventory_db" in final_state.get("database_queries", {})
    assert final_state.get("row_count") > 0
    assert len(final_state.get("query_result", [])) > 0
    assert final_state.get("execution_plan_diagram") is not None
    assert len(final_state.get("sources_used", [])) >= 2


def test_multi_turn_context_refinement(setup_databases):
    """Verify multi-turn follow-up questions reuse previous query context and refine results."""
    g = build_graph()
    history = [
        {"role": "user", "content": "Which products have high demand but low inventory?"},
        {"role": "assistant", "content": "Here are products with high demand and low inventory.", "sql": "SELECT ..."}
    ]

    followup_state = {
        "question": "Only show products where inventory is below 20.",
        "user_id": "test_user",
        "user_role": "admin",
        "conversation_history": history,
        "sql_gen_attempts": 0,
    }

    final_state = g.invoke(followup_state)
    assert final_state.get("is_federated") is True
    rows = final_state.get("query_result", [])
    assert len(rows) > 0
    # Every row in refined result must have stock_quantity < 20
    for r in rows:
        assert float(r.get("stock_quantity", 0)) < 20
