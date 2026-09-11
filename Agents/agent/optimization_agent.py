# agent/optimization_agent.py
"""Optimization Agent — Graph Node.

Reviews a validated SQL query for performance improvements:
  - Rewrite correlated subqueries as JOINs
  - Suggest indexes for unindexed WHERE/JOIN columns on large tables
  - Flag unbounded result sets
Returns the original SQL unchanged if no improvements are needed.
"""

from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage

from agent.Prompts.optimization_prompt import (
    OPTIMIZATION_SYSTEM_PROMPT,
    build_optimization_user_prompt,
)
from agent.Schema.optimization_schema import OptimizationOutput
from config import OPTIMIZATION_MODEL, OLLAMA_BASE_URL


def optimization_node(state: dict) -> dict:
    """LangGraph node: optimize the validated SQL query.

    Reads:
        state["generated_sql"]
        state["relevant_schema"]
        state["db_dialect"]

    Returns partial state update:
        {"optimized_sql": "...", "optimization_notes": [...], "estimated_cost": "..."}
    """
    row_counts = {
        t: state["relevant_schema"][t].get("row_count")
        for t in state["relevant_schema"]
    }

    llm = ChatOllama(
        model=OPTIMIZATION_MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=0,
    )
    structured_llm = llm.with_structured_output(
        OptimizationOutput, method="json_schema"
    )

    messages = [
        SystemMessage(
            content=OPTIMIZATION_SYSTEM_PROMPT.format(dialect=state["db_dialect"])
        ),
        HumanMessage(
            content=build_optimization_user_prompt(
                state["generated_sql"], row_counts
            )
        ),
    ]
    result: OptimizationOutput = structured_llm.invoke(messages)

    return {
        "optimized_sql": result.optimized_sql,
        "optimization_notes": result.notes,
        "estimated_cost": result.estimated_cost,
    }
