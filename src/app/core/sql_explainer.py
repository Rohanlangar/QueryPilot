"""
QueryPilot — SQL Syntax & Clause Explainer

Provides comprehensive breakdowns of what an SQL query does and explanations
for why specific clauses (SELECT, FROM, JOIN, WHERE, GROUP BY, HAVING, ORDER BY, LIMIT)
and functions are used.
"""

import re
from typing import Dict, List, Any, Optional


def analyze_sql_clauses(sql: str) -> Dict[str, Any]:
    """Parse an SQL query string into constituent clauses."""
    clean_sql = sql.strip().rstrip(";")

    select_match = re.search(r'\bSELECT\b\s+(.*?)\s+\bFROM\b', clean_sql, re.IGNORECASE | re.DOTALL)
    select_part = select_match.group(1).strip() if select_match else ""

    from_match = re.search(r'\bFROM\b\s+([^\s,;]+(?:\s+AS\s+[^\s,;]+|\s+[^\s,;]+)?)', clean_sql, re.IGNORECASE)
    from_part = from_match.group(1).strip() if from_match else ""

    join_matches = re.findall(
        r'\b((?:INNER\s+|LEFT\s+(?:OUTER\s+)?|RIGHT\s+(?:OUTER\s+)?|FULL\s+(?:OUTER\s+)?|CROSS\s+)?JOIN\s+.*?\s+ON\s+.*?)(?=\b(?:LEFT|RIGHT|INNER|JOIN|WHERE|GROUP|ORDER|LIMIT|$)\b)',
        clean_sql, re.IGNORECASE | re.DOTALL
    )

    where_match = re.search(r'\bWHERE\b\s+(.*?)(?=\b(?:GROUP\s+BY|ORDER\s+BY|LIMIT|$)\b)', clean_sql, re.IGNORECASE | re.DOTALL)
    where_part = where_match.group(1).strip() if where_match else ""

    group_match = re.search(r'\bGROUP\s+BY\b\s+(.*?)(?=\b(?:HAVING|ORDER\s+BY|LIMIT|$)\b)', clean_sql, re.IGNORECASE | re.DOTALL)
    group_part = group_match.group(1).strip() if group_match else ""

    having_match = re.search(r'\bHAVING\b\s+(.*?)(?=\b(?:ORDER\s+BY|LIMIT|$)\b)', clean_sql, re.IGNORECASE | re.DOTALL)
    having_part = having_match.group(1).strip() if having_match else ""

    order_match = re.search(r'\bORDER\s+BY\b\s+(.*?)(?=\b(?:LIMIT|$)\b)', clean_sql, re.IGNORECASE | re.DOTALL)
    order_part = order_match.group(1).strip() if order_match else ""

    limit_match = re.search(r'\bLIMIT\b\s+(\d+)', clean_sql, re.IGNORECASE)
    limit_part = limit_match.group(1).strip() if limit_match else ""

    return {
        "select": select_part,
        "from": from_part,
        "joins": [j.strip() for j in join_matches],
        "where": where_part,
        "group_by": group_part,
        "having": having_part,
        "order_by": order_part,
        "limit": limit_part,
    }


def get_clause_breakdown_list(sql: str) -> List[Dict[str, str]]:
    """Return a list of structured clause breakdowns suitable for UI cards."""
    clauses = analyze_sql_clauses(sql)
    breakdown = []

    if clauses["select"]:
        s = clauses["select"]
        if s.strip() == "*":
            exp = "Retrieves all columns from the dataset to examine the full record schema."
        else:
            cols = [c.strip() for c in s.split(",") if c.strip()]
            aggs = []
            if re.search(r'\bCOUNT\(', s, re.IGNORECASE):
                aggs.append("COUNT to compute row counts")
            if re.search(r'\bSUM\(', s, re.IGNORECASE):
                aggs.append("SUM to calculate totals")
            if re.search(r'\bAVG\(', s, re.IGNORECASE):
                aggs.append("AVG to determine averages")
            if aggs:
                exp = f"Computes aggregate metrics ({', '.join(aggs)}) and selects specific fields ({len(cols)} attribute(s)) to summarize the data."
            else:
                exp = f"Specifies the exact fields to retrieve ({', '.join(cols[:4])}{'...' if len(cols) > 4 else ''}) to present relevant record details."
        breakdown.append({"clause": "SELECT", "sql": f"SELECT {s}", "explanation": exp})

    if clauses["from"]:
        f = clauses["from"]
        breakdown.append({"clause": "FROM", "sql": f"FROM {f}", "explanation": f"Designates the primary table ({f}) where the base records are queried from."})

    for j in clauses["joins"]:
        breakdown.append({"clause": "JOIN", "sql": j, "explanation": f"Combines corresponding records across tables based on the join condition ({j}) to enrich the result set."})

    if clauses["where"]:
        w = clauses["where"]
        breakdown.append({"clause": "WHERE", "sql": f"WHERE {w}", "explanation": f"Filters rows using criteria ({w}) so only matching records are included in the result."})

    if clauses["group_by"]:
        g = clauses["group_by"]
        breakdown.append({"clause": "GROUP BY", "sql": f"GROUP BY {g}", "explanation": f"Groups records by ({g}) so aggregate functions can compute summaries per category."})

    if clauses["having"]:
        h = clauses["having"]
        breakdown.append({"clause": "HAVING", "sql": f"HAVING {h}", "explanation": f"Applies post-aggregation filtering ({h}) to keep only groups satisfying this condition."})

    if clauses["order_by"]:
        o = clauses["order_by"]
        direction = "descending (highest/latest first)" if "desc" in o.lower() else "ascending (lowest/earliest first)"
        breakdown.append({"clause": "ORDER BY", "sql": f"ORDER BY {o}", "explanation": f"Sorts the results by ({o}) in {direction} order to prioritize key records."})

    if clauses["limit"]:
        l = clauses["limit"]
        breakdown.append({"clause": "LIMIT", "sql": f"LIMIT {l}", "explanation": f"Restricts output to {l} records to avoid transferring unnecessary rows and ensure fast execution."})

    return breakdown


def generate_sql_explanation_html(sql: str, question: str = "", row_count: Optional[int] = None) -> str:
    """Generate structured HTML explanation with purpose and syntax breakdown."""
    clauses = analyze_sql_clauses(sql)
    entity_name = clauses["from"].replace('"', '').replace('`', '').split()[-1] if clauses["from"] else "records"
    rows_text = f", returning {row_count} record(s)" if row_count is not None else ""

    if question and question.strip():
        purpose = f"This query addresses: <em>\"{question.strip()}\"</em> by querying <code>{entity_name}</code>{rows_text}."
    else:
        purpose = f"This query retrieves and formats records from <code>{entity_name}</code> according to the specified criteria{rows_text}."

    items = []
    for b in get_clause_breakdown_list(sql):
        clause_name = b["clause"]
        explanation = b["explanation"]
        items.append(f"<li><strong>{clause_name}:</strong> {explanation}</li>")

    return (
        f"<p><strong>What this query does:</strong> {purpose}</p>\n"
        f"<p><strong>Syntax &amp; Clause Breakdown:</strong></p>\n"
        f"<ul>\n" + "\n".join(f"  {item}" for item in items) + "\n</ul>"
    )
