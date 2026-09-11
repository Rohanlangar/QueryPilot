# agent/explanation_agent.py
"""Explanation Agent — Graph Node.

Translates query results into a plain-English explanation for a
non-technical business user. Includes confidence rating and
suggested follow-up questions.
"""

from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage

from agent.Prompts.explanation_prompt import (
    EXPLANATION_SYSTEM_PROMPT,
    build_explanation_user_prompt,
)
from agent.Schema.explanation_schema import ExplanationOutput
from config import EXPLANATION_MODEL, MAX_ROWS_TO_LLM, OLLAMA_BASE_URL


def explanation_node(state: dict) -> dict:
    """LangGraph node: explain query results in plain English.

    Reads:
        state["question"]
        state["optimized_sql"]
        state["query_result"]
        state["row_count"]

    Returns partial state update:
        {"explanation": "...", "confidence_label": "...",
         "suggested_followups": [...], "final_answer": "..."}
    """
    # Cap rows sent to the LLM to avoid overwhelming the context window
    sample = state["query_result"][:MAX_ROWS_TO_LLM]

    llm = ChatOllama(
        model=EXPLANATION_MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=0.3,
    )
    structured_llm = llm.with_structured_output(
        ExplanationOutput, method="json_schema"
    )

    messages = [
        SystemMessage(content=EXPLANATION_SYSTEM_PROMPT),
        HumanMessage(
            content=build_explanation_user_prompt(
                state["question"],
                state["optimized_sql"],
                state["row_count"],
                sample,
            )
        ),
    ]
    result: ExplanationOutput = structured_llm.invoke(messages)

    return {
        "explanation": result.explanation,
        "confidence_label": result.confidence_label,
        "confidence_reason": getattr(result, "confidence_reason", ""),
        "suggested_followups": result.suggested_followups,
        "final_answer": result.explanation,
    }
