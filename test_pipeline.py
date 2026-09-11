"""Comprehensive test runner for the Text-to-SQL system.

Verifies:
  1. Pydantic structured output schemas
  2. Prompt builders
  3. Database seeding & reflection (Phase 4)
  4. RBAC table access control (Phase 4)
  5. SQL extraction & PII masking (Phase 4)
  6. Query execution node (Phase 4)
  7. Deterministic validation node
  8. LangGraph pipeline compilation
  9. FastAPI app routing (Phase 7)
"""

import sys
import os

# Add Agents to path
_agents_dir = os.path.join(os.path.dirname(__file__), "Agents")
if _agents_dir not in sys.path:
    sys.path.insert(0, _agents_dir)

from graph.state import AgentState
from graph.build_graph import build_graph
from agent.validation_agent import validation_node
from agent.Schema.schema_agent_schema import SchemaSelectionOutput
from agent.Schema.sql_gen_schema import SQLGenerationOutput
from agent.Schema.validation_schema import ValidationResult
from agent.Schema.optimization_schema import OptimizationOutput
from agent.Schema.explanation_schema import ExplanationOutput
from agent.Prompts.schema_prompt import build_schema_user_prompt
from agent.Prompts.sql_gen_prompt import build_sql_gen_user_prompt
from agent.Prompts.optimization_prompt import build_optimization_user_prompt
from agent.Prompts.explanation_prompt import build_explanation_user_prompt

from db.seed import seed_database
from db.connectors import (
    get_full_schema_metadata,
    extract_table_names,
    mask_pii_rows,
    execute_query_node,
    get_engine_for_dialect,
)
from db.rbac import user_can_access_tables


def test_schemas():
    print("\n[1/7] Testing Pydantic Schemas...")
    s1 = SchemaSelectionOutput(relevant_tables=["customers", "orders"], reasoning="Needed for customer orders.")
    assert len(s1.relevant_tables) == 2

    s2 = SQLGenerationOutput(sql="SELECT * FROM orders", assumptions=["Assumed active orders"])
    assert s2.sql == "SELECT * FROM orders"

    s3 = ValidationResult(passed=True, errors=[])
    assert s3.passed is True

    s4 = OptimizationOutput(
        optimized_sql="SELECT id FROM orders",
        notes=["Added index suggestion"],
        estimated_cost="low",
        index_suggestions=["idx_orders_customer_id"]
    )
    assert s4.estimated_cost == "low"

    s5 = ExplanationOutput(
        explanation="Customer total is 100",
        confidence_label="High",
        confidence_reason="Direct match",
        suggested_followups=["Show breakdown by month"]
    )
    assert s5.confidence_label == "High"
    print("  ✓ All 5 Pydantic output schemas verified.")


def test_prompts():
    print("\n[2/7] Testing Prompt Builders...")
    p1 = build_schema_user_prompt("How many orders?", {"orders": {}})
    assert "orders" in p1

    p2 = build_sql_gen_user_prompt("How many orders?", {"orders": {}}, prior_sql="SELECT 1", errors=["Invalid column"])
    assert "Previous attempt failed validation" in p2

    p3 = build_optimization_user_prompt("SELECT * FROM orders", {"orders": {"row_count": 1000}})
    assert "row_count" in p3

    p4 = build_explanation_user_prompt("How many orders?", "SELECT COUNT(*) FROM orders", 1, [{"count": 10}])
    assert "Result" in p4
    print("  ✓ All prompt builders verified.")


def test_database_layer():
    print("\n[3/7] Testing Database Seeding & Schema Reflection (Phase 4)...")
    db_path = seed_database()
    assert os.path.exists(db_path), "company.db was not created"

    metadata = get_full_schema_metadata(force_refresh=True)
    expected_tables = ["departments", "employees", "salaries", "projects", "employee_projects", "customers", "orders", "order_items"]
    for t in expected_tables:
        assert t in metadata, f"Table {t} missing from reflected metadata"
        assert len(metadata[t]["columns"]) > 0, f"Table {t} has no columns reflected"

    # Verify schema enrichment (FKs and Sample Values)
    assert len(metadata["employees"]["foreign_keys"]) > 0, "Foreign keys missing on employees"
    assert "tier" in metadata["customers"]["sample_values"], "Sample values missing for customers.tier"
    assert "Enterprise" in metadata["customers"]["sample_values"]["tier"]
    print(f"  ✓ Reflected {len(metadata)} tables with FKs and sample values: {list(metadata.keys())}")


def test_rbac():
    print("\n[4/7] Testing RBAC (Phase 4)...")
    # Admin can access everything
    assert user_can_access_tables("admin", ["employees", "salaries", "orders"]) is True

    # Analyst cannot access salaries
    assert user_can_access_tables("analyst", ["employees", "orders"]) is True
    assert user_can_access_tables("analyst", ["salaries"]) is False

    # Viewer cannot access employees or salaries
    assert user_can_access_tables("viewer", ["departments", "projects"]) is True
    assert user_can_access_tables("viewer", ["employees"]) is False
    assert user_can_access_tables("viewer", ["salaries"]) is False
    print("  ✓ RBAC role checks (admin, analyst, viewer) verified.")


def test_pii_and_execution():
    print("\n[5/8] Testing Table Extraction, PII Masking & Query Node (Phase 4)...")
    # Table extraction with CTE exclusion test
    sql = "SELECT e.first_name, d.name FROM employees e JOIN departments d ON e.department_id = d.id"
    tables = extract_table_names(sql)
    assert "employees" in tables
    assert "departments" in tables

    cte_sql = "WITH member_counts AS (SELECT room_id FROM room_room_members) SELECT * FROM room_room r JOIN member_counts mc ON r.id = mc.room_id"
    cte_tables = extract_table_names(cte_sql)
    assert "member_counts" not in cte_tables, f"CTE was mistakenly extracted as a physical table: {cte_tables}"
    assert "room_room" in cte_tables
    assert "room_room_members" in cte_tables

    # PII masking
    sample_rows = [
        {"name": "Alice", "email": "alice.johnson@company.com", "phone": "+1-555-0101"}
    ]
    masked = mask_pii_rows(sample_rows)
    assert masked[0]["email"] != "alice.johnson@company.com"
    assert "alice" not in masked[0]["email"] or "***" in masked[0]["email"]
    assert masked[0]["phone"] == "[REDACTED_PHONE]"

    # Live query node execution
    exec_state = {
        "optimized_sql": "SELECT id, name, budget FROM departments ORDER BY budget DESC LIMIT 2",
        "db_dialect": "sqlite"
    }
    exec_res = execute_query_node(exec_state)
    assert exec_res["row_count"] == 2
    assert len(exec_res["query_result"]) == 2
    print("  ✓ Table extraction, PII masking, and query node execution verified.")


def test_deterministic_validation():
    print("\n[6/8] Testing Deterministic Validation Agent (Initial + Post-Optimization)...")
    schema = get_full_schema_metadata()

    # Valid initial SQL
    res_valid = validation_node({
        "generated_sql": "SELECT name, budget FROM departments",
        "relevant_schema": schema,
        "user_role": "admin"
    })
    assert res_valid["validation_passed"] is True

    # Unknown table in initial SQL
    res_bad = validation_node({
        "generated_sql": "SELECT * FROM non_existent_table",
        "relevant_schema": schema,
        "user_role": "admin"
    })
    assert res_bad["validation_passed"] is False

    # RBAC denied
    res_rbac = validation_node({
        "generated_sql": "SELECT * FROM salaries",
        "relevant_schema": schema,
        "user_role": "viewer"
    })
    assert res_rbac["validation_passed"] is False

    # Post-optimization validation: valid case
    from agent.validation_agent import post_optimization_validation_node
    post_valid = post_optimization_validation_node({
        "optimized_sql": "SELECT name, budget FROM departments ORDER BY budget DESC",
        "generated_sql": "SELECT name, budget FROM departments",
        "relevant_schema": schema,
        "user_role": "admin"
    })
    assert post_valid["post_optimization_validation_passed"] is True
    assert "ORDER BY" in post_valid["optimized_sql"]

    # Post-optimization validation: invalid case (safe revert to generated_sql)
    post_invalid = post_optimization_validation_node({
        "optimized_sql": "SELECT * FROM fake_optimizer_table",
        "generated_sql": "SELECT name, budget FROM departments",
        "relevant_schema": schema,
        "user_role": "admin"
    })
    assert post_invalid["post_optimization_validation_passed"] is False
    assert post_invalid["optimized_sql"] == "SELECT name, budget FROM departments", "Did not revert to safe generated_sql"
    print("  ✓ Deterministic validation node & post-optimization validator passed all scenarios.")


def test_connection_manager():
    print("\n[7/8] Testing Dynamic Database Connection Manager...")
    from db.connection_manager import (
        DatabaseConfig,
        test_connection,
        register_database,
        get_connection_schema,
        list_registered_connections,
        delete_connection,
    )

    # 1. Test connecting to SQLite
    conf = DatabaseConfig(
        connection_id="test_analytics_db",
        db_type="sqlite",
        database="company.db"
    )
    test_res = test_connection(conf)
    assert test_res["success"] is True, f"Connection test failed: {test_res}"

    # 2. Register DB & reflect schema
    reg_res = register_database(conf)
    assert reg_res["status"] == "connected"
    assert reg_res["table_count"] == 8

    # 3. Retrieve schema via connection ID
    schema = get_connection_schema("test_analytics_db")
    assert "departments" in schema
    assert "orders" in schema

    # 4. List connections
    conns = list_registered_connections()
    assert any(c["connection_id"] == "test_analytics_db" for c in conns)

    # 5. Cleanup
    delete_connection("test_analytics_db")
    print("  ✓ Dynamic database testing, schema reflection, registration, and retrieval verified.")


def test_fastapi_and_graph():
    print("\n[8/8] Testing LangGraph Compilation & FastAPI App (Phase 7)...")
    graph = build_graph()
    assert graph is not None

    try:
        from app.main import app
    except ImportError:
        from main import app
    routes = [route.path for route in app.routes]
    assert "/query" in routes
    assert "/health" in routes
    assert "/schema" in routes
    assert "/audit-logs" in routes
    assert "/connections" in routes or "/api/connections" in [r.split("{")[0].rstrip("/") for r in routes]
    print("  ✓ Graph compiled and all FastAPI routes (/query, /health, /schema, /audit-logs, /connections) registered.")


if __name__ == "__main__":
    print("=" * 65)
    print("QueryPilot Full Multi-Agent Text-to-SQL System Verification")
    print("=" * 65)
    test_schemas()
    test_prompts()
    test_database_layer()
    test_rbac()
    test_pii_and_execution()
    test_deterministic_validation()
    test_connection_manager()
    test_fastapi_and_graph()
    print("\n" + "=" * 65)
    print("ALL 8 TEST SUITES PASSED! System is fully operational.")
    print("=" * 65)
