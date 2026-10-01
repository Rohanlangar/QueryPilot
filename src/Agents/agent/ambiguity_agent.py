# agent/ambiguity_agent.py
"""Ambiguity Detection Agent — Graph Node.

Checks if the user's question has conflicting interpretations or missing criteria.
If ambiguous, returns a clarification question directly so the system asks the user
instead of guessing.
"""

from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage

from agent.Prompts.ambiguity_prompt import AMBIGUITY_SYSTEM_PROMPT, build_ambiguity_user_prompt
from agent.Schema.ambiguity_schema import AmbiguityCheckOutput
from config import SCHEMA_AGENT_MODEL, OLLAMA_BASE_URL


def ambiguity_node(state: dict) -> dict:
    """LangGraph node: detects ambiguity in user question.

    Reads:
        state["question"]

    Returns partial state update:
        {"is_ambiguous": bool, "clarification_question": str | None}
    """
    question = state.get("question", "").strip()

    # Fast heuristics: extremely short vague questions or questions explicitly with "or"
    if not question:
        return {
            "is_ambiguous": True,
            "clarification_question": "Could you please specify what data you would like to look up?",
        }

    try:
        llm = ChatOllama(
            model=SCHEMA_AGENT_MODEL,
            base_url=OLLAMA_BASE_URL,
            temperature=0,
        )
        structured_llm = llm.with_structured_output(
            AmbiguityCheckOutput, method="json_schema"
        )

        messages = [
            SystemMessage(content=AMBIGUITY_SYSTEM_PROMPT),
            HumanMessage(content=build_ambiguity_user_prompt(question)),
        ]
        result: AmbiguityCheckOutput = structured_llm.invoke(messages)

        if result.is_ambiguous and result.clarification_question:
            return {
                "is_ambiguous": True,
                "clarification_question": result.clarification_question,
                "final_answer": result.clarification_question,
                "explanation": result.clarification_question,
            }
        return {
            "is_ambiguous": False,
            "clarification_question": None,
        }
    except Exception:
        # On model error or timeout, default to False to avoid blocking clear questions
        return {
            "is_ambiguous": False,
            "clarification_question": None,
        }
