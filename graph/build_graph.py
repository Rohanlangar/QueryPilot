# graph/build_graph.py
"""LangGraph wiring — assembles all agent nodes into a compiled graph.

Pipeline flow:
    schema → sql_gen → validate →(conditional)→ optimize → execute → explain → END
                         ↓ (fail + retries left)
                       sql_gen  (retry loop)
                         ↓ (fail + max retries)
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
from agent.sql_gen_agent import sql_gen_node
from agent.validation_agent import validation_node, post_optimization_validation_node
from agent.optimization_agent import optimization_node
from agent.explanation_agent import explanation_node
from db.connectors import execute_query_node
from config import MAX_SQL_GEN_RETRIES


def route_after_validation(state: AgentState) -> str:
    """Conditional router after the initial Validation Agent.

    Returns:
        "optimize"   — validation passed, proceed to optimization
        "regenerate" — validation failed, retries remaining → back to sql_gen
        "fail"       — validation failed, max retries exhausted → end graph
    """
    if state.get("validation_passed"):
        return "optimize"
    if state.get("sql_gen_attempts", 0) >= MAX_SQL_GEN_RETRIES:
        return "fail"
    return "regenerate"


def route_after_execution(state: AgentState) -> str:
    """Conditional router after the database execution node (Improvement 1).

    If the query threw a runtime database error (e.g. unknown column, syntax error),
    routes back to sql_gen with execution traceback for auto-recovery if retries remain.
    """
    if state.get("execution_error"):
        if state.get("sql_gen_attempts", 0) < MAX_SQL_GEN_RETRIES:
            return "regenerate"
        return "fail"
    return "explain"


def build_graph():
    """Build and compile the full Text-to-SQL LangGraph pipeline with:
      1. Schema selection (retrieval + LLM)
      2. SQL Generation
      3. Deterministic Validation + retry loop
      4. Optimization Reviewer
      5. Post-Optimization Re-Validation (safely reverts if optimizer breaks SQL)
      6. Query Execution with PII masking + runtime error retry feedback loop
      7. Business Explanation
    """
    g = StateGraph(AgentState)

    # ── Register nodes ─────────────────────────────────────────────────
    g.add_node("schema", schema_node)
    g.add_node("sql_gen", sql_gen_node)
    g.add_node("validate", validation_node)
    g.add_node("optimize", optimization_node)
    g.add_node("post_opt_validate", post_optimization_validation_node)
    g.add_node("execute", execute_query_node)
    g.add_node("explain", explanation_node)

    # ── Wire edges ─────────────────────────────────────────────────────
    g.set_entry_point("schema")
    g.add_edge("schema", "sql_gen")
    g.add_edge("sql_gen", "validate")

    # Conditional routing after validation: pass → optimize, fail → retry or end
    g.add_conditional_edges(
        "validate",
        route_after_validation,
        {
            "optimize": "optimize",
            "regenerate": "sql_gen",
            "fail": END,
        },
    )

    # Send optimized query to post-optimization validation (only 1 pass), then execute
    g.add_edge("optimize", "post_opt_validate")
    g.add_edge("post_opt_validate", "execute")

    # Conditional routing after execution:
    # If DB runtime error occurs, auto-recovers by looping back to sql_gen!
    g.add_conditional_edges(
        "execute",
        route_after_execution,
        {
            "explain": "explain",
            "regenerate": "sql_gen",
            "fail": "explain",  # Let explanation agent explain the error gracefully if max retries hit
        },
    )

    g.add_edge("explain", END)

    return g.compile()
