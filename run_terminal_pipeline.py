"""Terminal Pipeline Visualizer for QueryPilot.

Runs a natural language question through all agents and clearly prints
the output and decisions made at EVERY stage:
  Stage 1: Candidate Tables & Schema Agent Selection
  Stage 2: SQL Generation Agent (qwen2.5:7b)
  Stage 3: Deterministic Validation Agent (syntax, tables, RBAC)
  Stage 4: Optimization Agent (rewritten SQL, cost tier, indexes)
  Stage 5: Post-Optimization Validation (1-pass verification & safe rollback)
  Stage 6: Database Execution (SQL run on SQLite with PII redaction)
  Stage 7: Explanation Agent (business summary, confidence, followups)

Usage:
    python run_terminal_pipeline.py
"""

import sys
import os
import time
import json

# Ensure Agents package is accessible
_agents_dir = os.path.join(os.path.dirname(__file__), "Agents")
if _agents_dir not in sys.path:
    sys.path.insert(0, _agents_dir)

from graph.build_graph import build_graph
from graph.state import AgentState
from db.seed import seed_database
from db.connectors import get_full_schema_metadata, DEFAULT_DB_FILE


def format_box(title: str, content: str, color_code: str = "36") -> str:
    """Helper to render a clean terminal visual box."""
    width = 75
    border = "─" * (width - 2)
    header = f"┌{border}┐\n│ \033[1;{color_code}m{title.center(width - 4)}\033[0m │\n├{border}┤"
    body_lines = []
    for line in content.split("\n"):
        # Wrap or pad lines
        body_lines.append(f"│  {line.ljust(width - 5)}│")
    footer = f"└{border}┘"
    return f"{header}\n" + "\n".join(body_lines) + f"\n{footer}"


def run_pipeline_demo(question: str, role: str = "admin"):
    print("\n" + "═" * 75)
    print(f"  \033[1;32mQUERYPILOT MULTI-AGENT PIPELINE EXECUTION\033[0m")
    print(f"  Question:  \"{question}\"")
    print(f"  User Role: {role}")
    print("═" * 75)

    # Setup database
    if not os.path.exists(DEFAULT_DB_FILE):
        print("  [Setup] Initializing demo company.db...")
        seed_database(DEFAULT_DB_FILE)

    schema = get_full_schema_metadata()
    print(f"  [Setup] 8 Reflected tables loaded with Foreign Keys and sample values.\n")

    graph = build_graph()

    initial_state: AgentState = {
        "user_id": "terminal_user",
        "user_role": role,
        "question": question,
        "db_dialect": "sqlite",
        "conversation_history": [],
        "sql_gen_attempts": 0,
    }

    start_total = time.time()

    # Stream node-by-node execution to show each stage output in real-time
    print("  \033[1;33mExecuting Pipeline Stages...\033[0m\n")

    current_state = dict(initial_state)

    for output in graph.stream(initial_state):
        for node_name, node_output in output.items():
            current_state.update(node_output)

            if node_name == "schema":
                rel_schema = node_output.get("relevant_schema", {})
                tables = list(rel_schema.keys())
                fk_info = []
                for t in tables:
                    for fk in rel_schema[t].get("foreign_keys", []):
                        fk_info.append(f"{t}.{','.join(fk['constrained_columns'])} -> {fk['referred_table']}.{','.join(fk['referred_columns'])}")

                details = (
                    f"Selected Tables: {tables}\n"
                    f"Foreign Keys:    {fk_info if fk_info else 'None required'}\n"
                    f"Sample Context:  Provided {sum(len(rel_schema[t].get('sample_values', {})) for t in tables)} categorical sample values to LLM."
                )
                print(format_box("STAGE 1: SCHEMA SELECTION AGENT", details, "34"))
                print()

            elif node_name == "sql_gen":
                attempt = current_state.get("sql_gen_attempts", 1)
                sql = node_output.get("generated_sql", "").strip()
                details = (
                    f"Attempt:        #{attempt}\n"
                    f"Generated SQL:  {sql}"
                )
                print(format_box("STAGE 2: SQL GENERATION AGENT (qwen2.5:7b)", details, "35"))
                print()

            elif node_name == "validate":
                passed = node_output.get("validation_passed")
                errors = node_output.get("validation_errors", [])
                status_str = "\033[1;32mPASSED (No syntax or RBAC errors)\033[0m" if passed else f"\033[1;31mFAILED ({errors})\033[0m"
                details = (
                    f"Status:         {status_str}\n"
                    f"RBAC Checked:   Role '{role}' authorized for referenced tables\n"
                    f"Action:         Routing to Optimization Agent" if passed else f"Action: Triggering retry loop (#{current_state.get('sql_gen_attempts')})"
                )
                print(format_box("STAGE 3: DETERMINISTIC VALIDATION AGENT", details, "32" if passed else "31"))
                print()

            elif node_name == "optimize":
                opt_sql = node_output.get("optimized_sql", "").strip()
                cost = node_output.get("estimated_cost", "N/A")
                notes = node_output.get("optimization_notes", [])
                details = (
                    f"Estimated Cost: {cost.upper()}\n"
                    f"Review Notes:   {notes if notes else 'No subquery rewrites needed'}\n"
                    f"Optimized SQL:  {opt_sql}"
                )
                print(format_box("STAGE 4: OPTIMIZATION REVIEW AGENT", details, "33"))
                print()

            elif node_name == "post_opt_validate":
                passed = node_output.get("post_optimization_validation_passed")
                errors = node_output.get("post_optimization_validation_errors", [])
                status_str = "\033[1;32mPASSED (Optimized SQL verified safe)\033[0m" if passed else "\033[1;33mREVERTED (Optimizer broke syntax, fell back to safe SQL)\033[0m"
                details = (
                    f"Status:         {status_str}\n"
                    f"Final SQL:      {node_output.get('optimized_sql', '').strip()}"
                )
                print(format_box("STAGE 5: POST-OPTIMIZATION RE-VALIDATION (1 PASS)", details, "36"))
                print()

            elif node_name == "execute":
                err = node_output.get("execution_error")
                count = node_output.get("row_count", 0)
                rows = node_output.get("query_result", [])
                if err:
                    details = f"Runtime Error: \033[1;31m{err}\033[0m\nAction: Triggering runtime feedback loop to SQL Gen"
                    color = "31"
                else:
                    preview = json.dumps(rows[:2], indent=2) if rows else "[]"
                    details = (
                        f"Status:         \033[1;32mSUCCESS\033[0m\n"
                        f"Rows Returned:  {count}\n"
                        f"PII Redaction:  Emails & Phones masked\n"
                        f"Preview Rows:   {preview}"
                    )
                    color = "32"
                print(format_box("STAGE 6: DATABASE QUERY EXECUTION & PII MASKING", details, color))
                print()

            elif node_name == "explain":
                answer = node_output.get("final_answer", "")
                conf = node_output.get("confidence_label", "")
                followups = node_output.get("suggested_followups", [])
                details = (
                    f"Confidence:     {conf}\n"
                    f"Answer:         {answer}\n"
                    f"Follow-up 1:    {followups[0] if len(followups) > 0 else 'N/A'}\n"
                    f"Follow-up 2:    {followups[1] if len(followups) > 1 else 'N/A'}"
                )
                print(format_box("STAGE 7: BUSINESS EXPLANATION AGENT", details, "37"))
                print()

    total_time = round(time.time() - start_total, 2)
    print("═" * 75)
    print(f"  \033[1;32mPIPELINE FINISHED SUCCESSFULLY IN {total_time}s\033[0m")
    print("═" * 75 + "\n")


if __name__ == "__main__":
    # Test query requiring joins, aggregations, and categorical filtering
    test_question = "Which customers placed orders with Delivered status and what was their total order amount?"
    run_pipeline_demo(test_question, role="admin")
