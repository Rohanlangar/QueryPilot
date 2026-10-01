# graph/build_graph.py
"""LangGraph wiring — assembles all agent nodes into a compiled graph.

Pipeline flow:
     ambiguity ──(is_ambiguous)──> explain ──> END
        │
     (clear)
        ↓
     schema ──> sql_gen ──> validate ──(pass)──> sandbox ──(pass)──> optimize ──> post_opt_validate ──> execute ──> explain ──> END
                              │                    │                                                        │
                      (fail + retries)     (fail + retries)                                         (fail + retries)
                              ↓                    ↓                                                        ↓
                           sql_gen              sql_gen                                                  sql_gen
"""

import sys
import os

# Add the Agents/ directory to sys.path so `import agent` resolves correctly
_agents_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Agents")
if _agents_dir not in sys.path:
    sys.path.insert(0, _agents_dir)

from langgraph.graph import StateGraph, END

from graph.state import AgentState
from agent.ambiguity_agent import ambiguity_node
from agent.schema_agent import schema_node
from agent.sql_gen_agent import sql_gen_node
from agent.validation_agent import validation_node, post_optimization_validation_node
from agent.sandbox_node import sandbox_node
from agent.optimization_agent import optimization_node
from agent.explanation_agent import explanation_node
from db.connectors import execute_query_node
from config import MAX_SQL_GEN_RETRIES


def route_after_ambiguity(state: AgentState) -> str:
    """Conditional router after Ambiguity Check.

    Returns:
        "clarify" — request is ambiguous, return clarification question immediately
        "proceed" — request is clear, continue to schema understanding
    """
    if state.get("is_ambiguous"):
        return "clarify"
    return "proceed"


def route_after_validation(state: AgentState) -> str:
    """Conditional router after the initial Validation Agent.

    Returns:
        "sandbox"    — AST/security validation passed, test in isolated sandbox
        "regenerate" — validation failed, retries remaining → back to sql_gen
        "fail"       — validation failed, max retries exhausted → end graph
    """
    if state.get("validation_passed"):
        return "sandbox"
    if state.get("sql_gen_attempts", 0) >= MAX_SQL_GEN_RETRIES:
        return "fail"
    return "regenerate"


def route_after_sandbox(state: AgentState) -> str:
    """Conditional router after isolated Sandbox execution.

    Enforces: NEVER return a query unless it has successfully executed in the sandbox first.
    If sandbox returns an error or semantic defect, feeds error back to sql_gen for retry.

    Returns:
        "optimize"   — sandbox execution succeeded, proceed to optimizer
        "regenerate" — sandbox execution failed, retries remaining → back to sql_gen
        "fail"       — sandbox failed, max retries exhausted → explain failure
    """
    if state.get("sandbox_passed"):
        return "optimize"
    if state.get("sql_gen_attempts", 0) >= MAX_SQL_GEN_RETRIES:
        return "fail"
    return "regenerate"


def route_after_execution(state: AgentState) -> str:
    """Conditional router after real database execution node.

    If runtime database error occurs on real DB, routes back to sql_gen if retries remain.
    """
    if state.get("execution_error"):
        if state.get("sql_gen_attempts", 0) < MAX_SQL_GEN_RETRIES:
            return "regenerate"
        return "fail"
    return "explain"


def build_graph():
    """Build and compile the full Text-to-SQL LangGraph pipeline with:
      1. Ambiguity Detection (asks clarification instead of guessing)
      2. Schema Understanding (retrieval + LLM)
      3. SQL Generation
      4. Deterministic AST/RBAC Validation
      5. Isolated PostgreSQL / Fallback Sandbox execution with self-healing retry loop
      6. Query Optimization Reviewer
      7. Post-Optimization Re-Validation
      8. Real Database Execution (read-only timeout & optional approval gate)
      9. Business Explanation & Insights
    """
    g = StateGraph(AgentState)

    # ── Register nodes ─────────────────────────────────────────────────
    g.add_node("ambiguity", ambiguity_node)
    g.add_node("schema", schema_node)
    g.add_node("sql_gen", sql_gen_node)
    g.add_node("validate", validation_node)
    g.add_node("sandbox", sandbox_node)
    g.add_node("optimize", optimization_node)
    g.add_node("post_opt_validate", post_optimization_validation_node)
    g.add_node("execute", execute_query_node)
    g.add_node("explain", explanation_node)

    # ── Wire edges ─────────────────────────────────────────────────────
    g.set_entry_point("ambiguity")

    # Ambiguity router: ambiguous -> explain (returns clarification), clear -> schema
    g.add_conditional_edges(
        "ambiguity",
        route_after_ambiguity,
        {
            "clarify": "explain",
            "proceed": "schema",
        },
    )

    g.add_edge("schema", "sql_gen")
    g.add_edge("sql_gen", "validate")

    # Validation router: pass -> sandbox, fail -> retry sql_gen or end
    g.add_conditional_edges(
        "validate",
        route_after_validation,
        {
            "sandbox": "sandbox",
            "regenerate": "sql_gen",
            "fail": END,
        },
    )

    # Sandbox router: pass -> optimize, fail -> retry sql_gen with sandbox_error
    g.add_conditional_edges(
        "sandbox",
        route_after_sandbox,
        {
            "optimize": "optimize",
            "regenerate": "sql_gen",
            "fail": "explain",
        },
    )

    # Send optimized query to post-optimization validation, then execute
    g.add_edge("optimize", "post_opt_validate")
    g.add_edge("post_opt_validate", "execute")

    # Real DB Execution router
    g.add_conditional_edges(
        "execute",
        route_after_execution,
        {
            "explain": "explain",
            "regenerate": "sql_gen",
            "fail": "explain",
        },
    )

    g.add_edge("explain", END)

    return g.compile()
