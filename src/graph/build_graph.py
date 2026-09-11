# graph/build_graph.py
"""LangGraph wiring — assembles all federated agent nodes into a compiled graph.

Pipeline flow:
    schema (Discovery) ──▶ planner (Planning) ──▶ sql_gen (Generation) ──▶ validate (Validation)
                                                        ▲                        │
                                                        │ (regenerate on error)  ▼ (pass)
                                                        └── execute ◀────────────┘
                                                               │
                                                               ▼ (success)
                                                           federate (Join & Merge)
                                                               │
                                                               ▼
                                                           explain (Business Insights)
                                                               │
                                                               ▼
                                                              END
"""

import sys
import os

# Add the Agents/ directory to sys.path so `import agent` resolves correctly
_agents_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Agents")
if _agents_dir not in sys.path:
    sys.path.insert(0, _agents_dir)

from langgraph.graph import StateGraph, END

from graph.state import AgentState
from agent.schema_agent import schema_node
from agent.query_planner_agent import query_planner_node
from agent.sql_gen_agent import sql_gen_node
from agent.validation_agent import validation_node
from agent.federation_agent import federation_agent_node
from agent.explanation_agent import explanation_node
from db.connectors import execute_query_node
from config import MAX_SQL_GEN_RETRIES


def route_after_validation(state: AgentState) -> str:
    """Conditional router after the initial Validation Agent.

    Returns:
        "execute"    — validation passed, proceed to execution
        "fail"       — security incident detected or max retries exhausted → explain/halt
        "regenerate" — validation failed (syntax/schema), retries remaining → back to sql_gen
    """
    if state.get("security_incident"):
        return "fail"
    if state.get("validation_passed"):
        return "execute"
    if state.get("sql_gen_attempts", 0) >= MAX_SQL_GEN_RETRIES:
        return "fail"
    return "regenerate"


def route_after_execution(state: AgentState) -> str:
    """Conditional router after the database execution node.

    If a query threw a runtime database error (e.g. unknown column, syntax error),
    routes back to sql_gen with execution traceback for auto-recovery if retries remain.
    """
    if state.get("execution_error"):
        if state.get("sql_gen_attempts", 0) < MAX_SQL_GEN_RETRIES:
            return "regenerate"
        return "explain"
    return "federate"


def build_graph():
    """Build and compile the full Multi-Database Federated Text-to-SQL LangGraph pipeline:
      1. Schema Discovery Agent (discovers schemas across ALL active databases)
      2. Query Planning Agent (determines 1 DB vs multi-DB join plan & sub-goals)
      3. SQL Generation Agent (generates database-specific SQL queries)
      4. Validation Agent (verifies read-only safety, syntax, and schema existence per DB)
      5. Query Execution Agent (runs read-only queries on target DB engines with PII masking)
      6. Federation / Join Agent (application-level in-memory hash join, merge, aggregation)
      7. Explanation Agent (synthesizes unified business insights, sources attribution, plan)
    """
    g = StateGraph(AgentState)

    # ── Register nodes ─────────────────────────────────────────────────
    g.add_node("schema", schema_node)
    g.add_node("planner", query_planner_node)
    g.add_node("sql_gen", sql_gen_node)
    g.add_node("validate", validation_node)
    g.add_node("execute", execute_query_node)
    g.add_node("federate", federation_agent_node)
    g.add_node("explain", explanation_node)

    # ── Wire edges ─────────────────────────────────────────────────────
    g.set_entry_point("schema")
    g.add_edge("schema", "planner")
    g.add_edge("planner", "sql_gen")
    g.add_edge("sql_gen", "validate")

    # Conditional routing after validation:
    # pass → execute, fail → regenerate or explain
    g.add_conditional_edges(
        "validate",
        route_after_validation,
        {
            "execute": "execute",
            "regenerate": "sql_gen",
            "fail": "explain",
        },
    )

    # Conditional routing after execution:
    # success → federate, error → regenerate or explain
    g.add_conditional_edges(
        "execute",
        route_after_execution,
        {
            "federate": "federate",
            "regenerate": "sql_gen",
            "explain": "explain",
        },
    )

    g.add_edge("federate", "explain")
    g.add_edge("explain", END)

    return g.compile()
