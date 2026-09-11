# agent/schema_agent.py
"""Schema Selection Agent — Graph Node.

Narrows the full DB schema down to only the tables needed to answer
the user's question. Uses embedding pre-filter (retrieval.py) to get
candidates, then an LLM to select the precise subset.
"""

from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage

from agent.Prompts.schema_prompt import SCHEMA_SYSTEM_PROMPT, build_schema_user_prompt
from agent.Schema.schema_agent_schema import SchemaSelectionOutput
from db.retrieval import retrieve_candidate_tables
from config import SCHEMA_AGENT_MODEL, OLLAMA_BASE_URL


def schema_node(state: dict) -> dict:
    """LangGraph node: select relevant tables from embedding-ranked candidates.

    Reads:
        state["question"]

    Returns partial state update:
        {"relevant_schema": {table_name: table_metadata, ...}}
    """
    # Step 1: Embedding pre-filter — narrow full schema to top-k candidates
    candidate_schema = retrieve_candidate_tables(state["question"], top_k=25)

    # Step 2: LLM selects the precise subset via structured output
    llm = ChatOllama(
        model=SCHEMA_AGENT_MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=0,
    )
    structured_llm = llm.with_structured_output(
        SchemaSelectionOutput, method="json_schema"
    )

    messages = [
        SystemMessage(content=SCHEMA_SYSTEM_PROMPT),
        HumanMessage(
            content=build_schema_user_prompt(state["question"], candidate_schema)
        ),
    ]
    result: SchemaSelectionOutput = structured_llm.invoke(messages)

    # Step 3: Filter candidates to only the LLM-selected tables
    relevant = {
        t: candidate_schema[t]
        for t in result.relevant_tables
        if t in candidate_schema
    }

    return {"relevant_schema": relevant}
