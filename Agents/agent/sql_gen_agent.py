# agent/sql_gen_agent.py
"""SQL Generation Agent — Graph Node.

Generates a SQL query from the user's natural-language question and the
relevant schema. Supports retry loops: when validation errors are present
in state, the prompt includes prior SQL + errors so the LLM can fix them.
"""

from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage

from agent.Prompts.sql_gen_prompt import SQL_GEN_SYSTEM_PROMPT, build_sql_gen_user_prompt
from agent.Schema.sql_gen_schema import SQLGenerationOutput
from config import SQL_GEN_MODEL, DEFAULT_ROW_LIMIT, OLLAMA_BASE_URL


def sql_gen_node(state: dict) -> dict:
    """LangGraph node: generate SQL from question + schema.

    Reads:
        state["question"]
        state["relevant_schema"]
        state["db_dialect"]
        state.get("generated_sql")       — prior attempt (for retries)
        state.get("validation_errors")   — errors from prior attempt

    Returns partial state update:
        {"generated_sql": "...", "sql_gen_attempts": N}
    """
    llm = ChatOllama(
        model=SQL_GEN_MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=0,
    )
    structured_llm = llm.with_structured_output(
        SQLGenerationOutput, method="json_schema"
    )

    # Combine static validation errors and runtime database execution errors for retry prompt
    prior_errors = list(state.get("validation_errors") or [])
    if state.get("execution_error"):
        prior_errors.append(f"Database runtime error: {state['execution_error']}")

    prior_sql = state.get("optimized_sql") or state.get("generated_sql", "")

    messages = [
        SystemMessage(
            content=SQL_GEN_SYSTEM_PROMPT.format(
                dialect=state["db_dialect"],
                row_limit=DEFAULT_ROW_LIMIT,
            )
        ),
        HumanMessage(
            content=build_sql_gen_user_prompt(
                state["question"],
                state["relevant_schema"],
                prior_sql,
                prior_errors if prior_errors else None,
            )
        ),
    ]
    result: SQLGenerationOutput = structured_llm.invoke(messages)

    return {
        "generated_sql": result.sql,
        "sql_gen_attempts": state.get("sql_gen_attempts", 0) + 1,
        "validation_errors": [],
        "execution_error": None,
    }
