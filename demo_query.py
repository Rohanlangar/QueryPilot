"""Quick end-to-end test script for QueryPilot.

Runs a natural language query through the full multi-agent pipeline
and prints the step-by-step progress and final output.

Usage:
    python demo_query.py
"""

import sys
import os
import json
import time

# Ensure Agents package is accessible in sys.path
_agents_dir = os.path.join(os.path.dirname(__file__), "Agents")
if _agents_dir not in sys.path:
    sys.path.insert(0, _agents_dir)

from graph.build_graph import build_graph
from graph.state import AgentState
from db.seed import seed_database
from db.connectors import get_full_schema_metadata, DEFAULT_DB_FILE


def run_demo(question: str, role: str = "admin"):
    print("=" * 70)
    print(f"QUERYPILOT END-TO-END DEMO")
    print(f"Question: \"{question}\"")
    print(f"User Role: {role}")
    print("=" * 70)

    # 1. Ensure DB exists
    if not os.path.exists(DEFAULT_DB_FILE):
        print("[Setup] Seeding demo company.db...")
        seed_database(DEFAULT_DB_FILE)

    # 2. Pre-warm schema
    schema = get_full_schema_metadata()
    print(f"[Setup] Available tables: {list(schema.keys())}\n")

    # 3. Compile Graph
    print("[Pipeline] Compiling LangGraph...")
    graph = build_graph()

    initial_state: AgentState = {
        "user_id": "demo_user",
        "user_role": role,
        "question": question,
        "db_dialect": "sqlite",
        "conversation_history": [],
        "sql_gen_attempts": 0,
    }

    print("[Pipeline] Executing multi-agent workflow...")
    print("  Step 1: Embedding retrieval + Schema Agent (selecting tables)")
    print("  Step 2: SQL Gen Agent (synthesizing SQL with qwen2.5-coder)")
    print("  Step 3: Validation Agent (deterministic sqlparse + RBAC checks)")
    print("  Step 4: Optimization Agent (query performance review)")
    print("  Step 5: Query Execution Node (SQL execution + PII masking)")
    print("  Step 6: Explanation Agent (business summary + confidence + followups)\n")

    start = time.time()
    try:
        final_state = graph.invoke(initial_state)
        elapsed = round(time.time() - start, 2)

        print("-" * 70)
        print(f"PIPELINE COMPLETED in {elapsed}s")
        print("-" * 70)

        # Print Schema selected
        selected_tables = list(final_state.get("relevant_schema", {}).keys())
        print(f"1. Relevant Tables Selected:\n   {selected_tables}\n")

        # Print SQL
        print(f"2. Synthesized SQL:\n   {final_state.get('generated_sql')}\n")

        # Validation status
        print(f"3. Validation Result:\n   Passed: {final_state.get('validation_passed')}")
        if final_state.get("validation_errors"):
            print(f"   Errors: {final_state.get('validation_errors')}\n")
        else:
            print(f"   No errors detected.\n")

        # Optimized SQL
        print(f"4. Optimized SQL:\n   {final_state.get('optimized_sql')}")
        print(f"   Estimated Cost: {final_state.get('estimated_cost')}")
        if final_state.get("optimization_notes"):
            print(f"   Notes: {final_state.get('optimization_notes')}\n")
        else:
            print()

        # Query execution & PII masking
        result = final_state.get("query_result", [])
        print(f"5. Execution Results ({final_state.get('row_count', 0)} rows, PII masked):")
        for row in result[:5]:
            print(f"   {row}")
        print()

        # Business Explanation
        print(f"6. Business Explanation:")
        print(f"   Answer:     {final_state.get('final_answer')}")
        print(f"   Confidence: {final_state.get('confidence_label')}")
        print(f"   Follow-ups: {final_state.get('suggested_followups')}\n")

    except Exception as e:
        print(f"\n[Error during execution]: {e}")
        print("Note: Ensure Ollama is running (`ollama serve`) and models are pulled.")


if __name__ == "__main__":
    # Test query
    sample_question = "Which departments have the highest budget and who works in them?"
    run_demo(sample_question, role="admin")
