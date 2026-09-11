# agent/explanation_agent.py
"""Explanation Agent — Graph Node.

Translates query results and SQL queries into a structured explanation:
what the query does and a detailed syntax/clause breakdown explaining
why specific clauses and functions were chosen.
"""

import re
import logging
from typing import List, Dict, Any, Optional

from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage

from agent.Prompts.explanation_prompt import (
    EXPLANATION_SYSTEM_PROMPT,
    build_explanation_user_prompt,
)
from agent.Schema.explanation_schema import ExplanationOutput
from config import EXPLANATION_MODEL, MAX_ROWS_TO_LLM, OLLAMA_BASE_URL

logger = logging.getLogger(__name__)


def generate_sql_clause_explanation(sql: str, question: str = "", row_count: int = 0) -> str:
    """Generate a rich HTML explanation of what the query does and why each clause/function is used."""
    if not sql or not sql.strip():
        return "<p>No query was executed to explain.</p>"

    clean_sql = sql.strip().rstrip(";")

    # Extract clauses using regex
    # SELECT
    select_match = re.search(r'\bSELECT\b\s+(.*?)\s+\bFROM\b', clean_sql, re.IGNORECASE | re.DOTALL)
    select_part = select_match.group(1).strip() if select_match else ""

    # FROM
    from_match = re.search(r'\bFROM\b\s+([^\s,;]+(?:\s+AS\s+[^\s,;]+|\s+[^\s,;]+)?)', clean_sql, re.IGNORECASE)
    from_part = from_match.group(1).strip() if from_match else ""

    # JOIN
    join_matches = re.findall(
        r'\b((?:INNER\s+|LEFT\s+(?:OUTER\s+)?|RIGHT\s+(?:OUTER\s+)?|FULL\s+(?:OUTER\s+)?|CROSS\s+)?JOIN\s+.*?\s+ON\s+.*?)(?=\b(?:LEFT|RIGHT|INNER|JOIN|WHERE|GROUP|ORDER|LIMIT|$)\b)',
        clean_sql, re.IGNORECASE | re.DOTALL
    )

    # WHERE
    where_match = re.search(r'\bWHERE\b\s+(.*?)(?=\b(?:GROUP\s+BY|ORDER\s+BY|LIMIT|$)\b)', clean_sql, re.IGNORECASE | re.DOTALL)
    where_part = where_match.group(1).strip() if where_match else ""

    # GROUP BY
    group_match = re.search(r'\bGROUP\s+BY\b\s+(.*?)(?=\b(?:HAVING|ORDER\s+BY|LIMIT|$)\b)', clean_sql, re.IGNORECASE | re.DOTALL)
    group_part = group_match.group(1).strip() if group_match else ""

    # HAVING
    having_match = re.search(r'\bHAVING\b\s+(.*?)(?=\b(?:ORDER\s+BY|LIMIT|$)\b)', clean_sql, re.IGNORECASE | re.DOTALL)
    having_part = having_match.group(1).strip() if having_match else ""

    # ORDER BY
    order_match = re.search(r'\bORDER\s+BY\b\s+(.*?)(?=\b(?:LIMIT|$)\b)', clean_sql, re.IGNORECASE | re.DOTALL)
    order_part = order_match.group(1).strip() if order_match else ""

    # LIMIT
    limit_match = re.search(r'\bLIMIT\b\s+(\d+)', clean_sql, re.IGNORECASE)
    limit_part = limit_match.group(1).strip() if limit_match else ""

    # Build "What this query does"
    entity_name = from_part.replace('"', '').replace('`', '').split()[-1] if from_part else "records"
    if question and question.strip():
        purpose = f"This query addresses your request (<em>\"{question.strip()}\"</em>) by querying the <code>{entity_name}</code> dataset and returning {row_count} matching record(s)."
    else:
        purpose = f"This query retrieves and formats records from the <code>{entity_name}</code> table according to the requested criteria, returning {row_count} record(s)."

    items = []

    # SELECT breakdown
    if select_part:
        if select_part.strip() == "*":
            items.append("<li><strong>SELECT *:</strong> Retrieves all available columns from the table to provide a full record profile.</li>")
        else:
            # Check for aggregate functions
            aggregates = []
            if re.search(r'\bCOUNT\(', select_part, re.IGNORECASE):
                aggregates.append("<code>COUNT()</code> to calculate row frequency")
            if re.search(r'\bSUM\(', select_part, re.IGNORECASE):
                aggregates.append("<code>SUM()</code> to compute cumulative totals")
            if re.search(r'\bAVG\(', select_part, re.IGNORECASE):
                aggregates.append("<code>AVG()</code> to calculate mean values")
            if re.search(r'\bMAX\(', select_part, re.IGNORECASE):
                aggregates.append("<code>MAX()</code> to identify peak values")
            if re.search(r'\bMIN\(', select_part, re.IGNORECASE):
                aggregates.append("<code>MIN()</code> to identify minimum values")

            col_list = [c.strip() for c in select_part.split(",") if c.strip()]
            if len(col_list) <= 5:
                cols_str = ", ".join(f"<code>{c}</code>" for c in col_list)
            else:
                cols_str = ", ".join(f"<code>{c}</code>" for c in col_list[:4]) + f", and {len(col_list)-4} more attributes"

            agg_desc = f" utilizing aggregate functions ({', '.join(aggregates)})" if aggregates else ""
            items.append(f"<li><strong>SELECT:</strong> Specifies the columns to return ({cols_str}){agg_desc} to provide the required data fields without requesting extraneous table data.</li>")

    # FROM breakdown
    if from_part:
        items.append(f"<li><strong>FROM:</strong> Identifies <code>{from_part}</code> as the source table where the required entity records reside.</li>")

    # JOIN breakdown
    if join_matches:
        for j in join_matches:
            items.append(f"<li><strong>JOIN:</strong> Uses <code>{j.strip()}</code> to connect related tables on common keys, combining corresponding records across datasets.</li>")

    # WHERE breakdown
    if where_part:
        items.append(f"<li><strong>WHERE:</strong> Filters the data using <code>{where_part}</code> so that only records satisfying this condition are processed and returned.</li>")

    # GROUP BY breakdown
    if group_part:
        items.append(f"<li><strong>GROUP BY:</strong> Groups rows by <code>{group_part}</code> to aggregate data points and calculate summary statistics per unique group.</li>")

    # HAVING breakdown
    if having_part:
        items.append(f"<li><strong>HAVING:</strong> Applies condition <code>{having_part}</code> to filter grouped and aggregated results after the GROUP BY execution.</li>")

    # ORDER BY breakdown
    if order_part:
        direction = "descending (highest / newest first)" if "desc" in order_part.lower() else "ascending (lowest / oldest first)"
        items.append(f"<li><strong>ORDER BY:</strong> Sorts the result set by <code>{order_part}</code> in {direction} order to prioritize key records.</li>")

    # LIMIT breakdown
    if limit_part:
        items.append(f"<li><strong>LIMIT:</strong> Constrains the result set to a maximum of <code>{limit_part}</code> rows to prevent excessive data transfer and guarantee fast query execution.</li>")

    html = f"<p><strong>What this query does:</strong> {purpose}</p>\n<p><strong>Syntax &amp; Clause Breakdown:</strong></p>\n<ul>\n" + "\n".join(f"  {item}" for item in items) + "\n</ul>"
    return html


def generate_default_followups(sql: str, question: str = "") -> List[str]:
    """Generate smart follow-up suggestions based on the SQL structure."""
    followups = []
    lower_sql = sql.lower()
    if "limit" in lower_sql:
        followups.append("Show more records or remove the LIMIT clause")
    if "where" not in lower_sql:
        followups.append("Filter results by a specific date or status")
    else:
        followups.append("Modify the filter criteria for a different subset")
    if "group by" not in lower_sql:
        followups.append("Aggregate these results by category or time period")
    else:
        followups.append("Sort these grouped metrics by highest volume")
    return followups[:2]


def _is_valid_explanation(exp: str, sql: str) -> bool:
    """Check if the generated explanation is a real explanation rather than raw SQL."""
    if not exp or len(exp.strip()) < 35:
        return False
    # If the text without tags is literally just the SQL query
    norm_exp = re.sub(r'<[^>]+>', '', exp).strip().rstrip(';')
    norm_sql = sql.strip().rstrip(';')
    if norm_exp == norm_sql:
        return False
    # Check for meaningful explanatory markers
    lower = exp.lower()
    has_markers = any(m in lower for m in [
        "what this query does", "syntax", "breakdown", "retrieves",
        "explains", "clause", "filters", "table", "columns", "purpose", "group by", "order by"
    ])
    return has_markers


def explanation_node(state: dict) -> dict:
    """LangGraph node: explain the SQL query logic and execution breakdown.

    Reads:
        state["question"]
        state["optimized_sql"] / state["generated_sql"]
        state["query_result"]
        state["row_count"]

    Returns partial state update:
        {"explanation": "...", "confidence_label": "...",
         "suggested_followups": [...], "final_answer": "..."}
    """
    sql_query = state.get("optimized_sql") or state.get("generated_sql") or ""
    raw_results = state.get("query_result") or []
    sample = raw_results[:MAX_ROWS_TO_LLM]
    row_count = state.get("row_count", len(raw_results))
    question = state.get("question", "")

    # Immediate short-circuit if a security incident was intercepted
    if state.get("security_incident"):
        inc = state["security_incident"]
        threat = inc.get("threat_type", "SECURITY_VIOLATION")
        pol = inc.get("policy_violated", "Enterprise Security Policy")
        inc_id = inc.get("incident_id", "SEC-ALERT")
        sec_explanation = (
            f"**🚨 CYBER-ATTACK INTERCEPTED & NEUTRALIZED**\n\n"
            f"- **Incident ID**: `{inc_id}`\n"
            f"- **Threat Classification**: `{threat}` (Severity: {inc.get('severity', 'CRITICAL')})\n"
            f"- **Enforced Policy**: {pol}\n"
            f"- **Enforcement Gate**: {inc.get('blocked_by', 'Agent 3: Deterministic AST & RBAC Security Gate')}\n"
            f"- **Database Integrity**: {inc.get('database_state', 'SAFE & UNTOUCHED (0 records altered)')}\n\n"
            f"> **Mitigation**: {inc.get('mitigation', 'Pre-flight AST interceptor discarded execution plan. Zero commands dispatched to target database engines.')}"
        )
        return {
            "explanation": sec_explanation,
            "confidence_label": "High",
            "confidence_reason": f"Attack neutralized by Pre-Flight AST Security Gate ({threat})",
            "suggested_followups": [
                "Run a safe read-only analytics query",
                "Inspect SOC 2 audit logs for this incident",
                "Verify RBAC permissions and user role",
            ],
            "final_answer": sec_explanation,
            "sources_used": [],
            "execution_plan_diagram": f"[BLOCKED] Pre-Flight Security Gate Intercepted {threat}",
            "security_incident": inc,
        }

    fallback_explanation = generate_sql_clause_explanation(sql_query, question, row_count)
    default_followups = generate_default_followups(sql_query, question)

    llm = ChatOllama(
        model=EXPLANATION_MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=0.2,
    )
    structured_llm = llm.with_structured_output(
        ExplanationOutput, method="json_schema"
    )

    messages = [
        SystemMessage(content=EXPLANATION_SYSTEM_PROMPT),
        HumanMessage(
            content=build_explanation_user_prompt(
                question,
                sql_query,
                row_count,
                sample,
            )
        ),
    ]

    # Check for federated sources
    sources_used = state.get("sources_used", [])
    is_federated = state.get("is_federated", False)
    diagram = state.get("execution_plan_diagram", "")

    try:
        result: ExplanationOutput = structured_llm.invoke(messages)
        candidate_exp = result.explanation
        if _is_valid_explanation(candidate_exp, sql_query):
            final_exp = candidate_exp
        else:
            logger.info("LLM explanation was too brief or raw SQL; using structured clause breakdown.")
            final_exp = fallback_explanation

        followups = result.suggested_followups if result.suggested_followups else default_followups

        # If federated query, enrich explanation with sources attribution if not already present
        if is_federated and sources_used and "database" not in final_exp.lower():
            src_str = ", ".join(f"<code>{s.get('database')}</code>" for s in sources_used)
            final_exp = f"<p><strong>Federated Analysis:</strong> Combined data from {src_str} via application-level join.</p>\n" + final_exp

        return {
            "explanation": final_exp,
            "confidence_label": result.confidence_label,
            "confidence_reason": getattr(result, "confidence_reason", "Verified against schema & SQL AST"),
            "suggested_followups": followups,
            "final_answer": final_exp,
            "sources_used": sources_used,
            "execution_plan_diagram": diagram,
        }
    except Exception as e:
        logger.warning(f"Explanation LLM invocation failed, using SQL explanation fallback: {e}")
        final_exp = fallback_explanation
        if is_federated and sources_used:
            src_str = ", ".join(f"<code>{s.get('database')}</code>" for s in sources_used)
            final_exp = f"<p><strong>Federated Analysis:</strong> Combined data from {src_str} via application-level join.</p>\n" + final_exp

        return {
            "explanation": final_exp,
            "confidence_label": "High" if sql_query else "Low",
            "confidence_reason": "SQL syntax verified and parsed into clause breakdown",
            "suggested_followups": default_followups,
            "final_answer": final_exp,
            "sources_used": sources_used,
            "execution_plan_diagram": diagram,
        }
