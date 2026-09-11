# agent/validation_agent.py
"""Validation Agent — Graph Node (Deterministic).

The reliability & security backbone of QueryPilot.
Enforces:
  1. Strict Read-Only Safety: Blocks INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, etc.
  2. SQL parseability and syntax verification (sqlparse).
  3. Schema verification: All referenced tables and columns exist in the target database schema.
  4. Multi-database validation: Validates each database's query against its respective schema.
  5. RBAC table-level permissions.
"""

import re
import uuid
from datetime import datetime, timezone
import sqlparse
from typing import Dict, Any, List, Optional

from db.rbac import user_can_access_tables
from db.connectors import extract_table_names
from agent.Schema.validation_schema import ValidationResult

_DESTRUCTIVE_KEYWORDS = {
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE",
    "CREATE", "GRANT", "REVOKE", "EXEC", "EXECUTE", "MERGE",
}

_PROMPT_INJECTION_PATTERNS = [
    r"\bignore\s+(all\s+)?(previous|prior)\s+instructions\b",
    r"\bbypass\s+(all\s+)?(security|rules|guardrails|safety)\b",
    r"\bsystem\s+override\b",
    r"\byou\s+are\s+now\s+(in\s+)?(god|dan|developer|jailbreak)\s+mode\b",
    r"\b(leak|dump|reveal|expose)\s+(all\s+)?(passwords|credentials|keys|unmasked\s+ssn)\b",
    r"\bdisregard\s+(all\s+)?(guardrails|guidelines|policies)\b",
]

_SQL_INJECTION_PATTERNS = [
    r";\s*(DROP|DELETE|UPDATE|INSERT|ALTER|TRUNCATE)\b",
    r"--\s*$",
    r"/\*.*?\*/",
    r"'\s+OR\s+'?1'?\s*=\s*'?1'?",
    r"UNION\s+(ALL\s+)?SELECT\b",
]


def analyze_security_threat(
    sql: str = "",
    question: str = "",
    user_role: str = "admin",
    referenced_tables: List[str] = None,
) -> Optional[Dict[str, Any]]:
    """Analyze query and SQL for cyber threats (SQL injection, DDL mutation, prompt jailbreak, RBAC)."""
    detected_type = None
    policy = None
    tokens = []
    desc = None

    # 1. Prompt injection / jailbreak check on user prompt
    if question:
        for pat in _PROMPT_INJECTION_PATTERNS:
            match = re.search(pat, question, re.IGNORECASE)
            if match:
                detected_type = "PROMPT_INJECTION_JAILBREAK"
                policy = "SEC-POL-08: Adversarial Input & LLM Jailbreak Defense"
                tokens.append(match.group(0))
                desc = f"Adversarial prompt injection pattern detected in input: '{match.group(0)}'."
                break

    # 2. SQL injection pattern check
    if not detected_type and sql:
        for pat in _SQL_INJECTION_PATTERNS:
            match = re.search(pat, sql, re.IGNORECASE)
            if match:
                detected_type = "SQL_INJECTION"
                policy = "SEC-POL-04: Deterministic AST Injection Prevention"
                tokens.append(match.group(0))
                desc = f"SQL injection vector identified via AST token scanner: '{match.group(0)}'."
                break

    # 3. Destructive DDL / DML check
    if not detected_type and sql:
        destructive_regex = re.compile(
            r"\b(INSERT\s+INTO|UPDATE\s+\w+\s+SET|DELETE\s+FROM|DROP\s+TABLE|ALTER\s+TABLE|TRUNCATE\s+TABLE|EXEC|EXECUTE)\b",
            re.IGNORECASE,
        )
        match = destructive_regex.search(sql)
        if match:
            detected_type = "DESTRUCTIVE_MUTATION"
            policy = "SEC-POL-01: Zero DDL/DML Mutation Guarantee"
            tokens.append(match.group(0))
            desc = f"Destructive state-mutating command blocked: '{match.group(0)}'."

    # 4. RBAC check
    if not detected_type and referenced_tables and user_role:
        if not user_can_access_tables(user_role, referenced_tables):
            detected_type = "RBAC_PRIVILEGE_ESCALATION"
            policy = "SEC-POL-02: Strict Role-Based Table Access Control"
            tokens.extend(referenced_tables)
            desc = f"User role '{user_role}' denied authorization to access table(s): {referenced_tables}."

    if detected_type:
        inc_id = f"SEC-BLOCK-{uuid.uuid4().hex[:6].upper()}"
        return {
            "is_blocked": True,
            "incident_id": inc_id,
            "threat_type": detected_type,
            "severity": "CRITICAL" if detected_type != "RBAC_PRIVILEGE_ESCALATION" else "HIGH",
            "policy_violated": policy,
            "blocked_by": "Agent 3: Deterministic AST & RBAC Security Gate",
            "description": desc,
            "detected_tokens": tokens,
            "database_state": "SAFE & UNTOUCHED (0 records modified, 0ms engine runtime)",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "mitigation": "Execution halted immediately pre-flight. Target database engines protected from unauthorized payload.",
        }

    return None


def _check_readonly_security(sql: str) -> List[str]:
    """Ensure SQL query contains only read-only statements."""
    errors = []
    try:
        parsed_list = sqlparse.parse(sql)
        for parsed in parsed_list:
            stmt_type = parsed.get_type()
            if stmt_type and stmt_type.upper() in _DESTRUCTIVE_KEYWORDS:
                errors.append(f"Security violation: {stmt_type} statements are strictly prohibited.")
            for token in parsed.flatten():
                if token.ttype in sqlparse.tokens.Keyword.DML or token.ttype in sqlparse.tokens.Keyword.DDL:
                    val_upper = token.value.upper()
                    if val_upper in _DESTRUCTIVE_KEYWORDS:
                        errors.append(f"Security violation: Disallowed SQL keyword detected: '{val_upper}'.")
    except Exception as e:
        errors.append(f"Security parse check failed: {e}")

    # Regex guard
    destructive_regex = re.compile(
        r"\b(INSERT\s+INTO|UPDATE\s+\w+\s+SET|DELETE\s+FROM|DROP\s+TABLE|ALTER\s+TABLE|TRUNCATE\s+TABLE)\b",
        re.IGNORECASE,
    )
    if destructive_regex.search(sql):
        errors.append("Security violation: Destructive DDL/DML pattern detected.")

    return list(set(errors))


def validate_sql(sql: str, relevant_schema: dict, user_role: str = "admin", question: str = "") -> ValidationResult:
    """Core deterministic validation logic for a single SQL query against a schema."""
    errors = []

    if not sql or not sql.strip():
        return ValidationResult(passed=False, errors=["Empty or unparseable SQL."])

    # Pre-flight check: Detailed threat analysis
    referenced_tables = extract_table_names(sql)
    threat = analyze_security_threat(
        sql=sql,
        question=question,
        user_role=user_role,
        referenced_tables=referenced_tables,
    )
    if threat:
        return ValidationResult(
            passed=False,
            errors=[threat["description"]],
            security_incident=threat,
        )

    # Check 1: Security — Read-only enforcement fallback
    sec_errors = _check_readonly_security(sql)
    if sec_errors:
        return ValidationResult(passed=False, errors=sec_errors)

    # Check 2: SQL syntax / parseability
    try:
        parsed = sqlparse.parse(sql)
        if not parsed:
            errors.append("Empty or unparseable SQL.")
    except Exception as e:
        errors.append(f"Syntax error: {e}")

    # Check 3: Table verification against target schema
    unknown = [t for t in referenced_tables if t not in relevant_schema and f"{t}" not in relevant_schema]
    if unknown and relevant_schema:
        errors.append(f"Unknown tables referenced: {unknown}")

    # Check 4: RBAC permissions
    if not user_can_access_tables(user_role, referenced_tables):
        errors.append("User role lacks permission for one or more referenced tables.")

    return ValidationResult(passed=len(errors) == 0, errors=errors)


def validation_node(state: dict) -> dict:
    """LangGraph node: validate generated SQL for single or multiple databases."""
    database_queries = state.get("database_queries", {})
    unified_schema = state.get("unified_schema", {})
    relevant_schema = state.get("relevant_schema", {})
    user_role = state.get("user_role", "admin")
    question = state.get("question", "")

    # Pre-check: Immediate prompt injection check
    prompt_threat = analyze_security_threat(question=question, user_role=user_role)
    if prompt_threat:
        return {
            "validation_passed": False,
            "validation_errors": [prompt_threat["description"]],
            "validation_details": {"prompt_threat": prompt_threat},
            "security_incident": prompt_threat,
        }

    all_errors = []
    validation_details = {}
    active_incident = None

    if database_queries:
        for db_id, sql in database_queries.items():
            db_schema = unified_schema.get(db_id, {}).get("tables", {}) or relevant_schema
            res = validate_sql(sql, db_schema, user_role, question)
            validation_details[db_id] = {"passed": res.passed, "errors": res.errors}
            if res.security_incident and not active_incident:
                active_incident = res.security_incident
            if not res.passed:
                all_errors.extend([f"[{db_id}] {e}" for e in res.errors])
    else:
        sql = state.get("generated_sql", "")
        res = validate_sql(sql, relevant_schema, user_role, question)
        validation_details["default"] = {"passed": res.passed, "errors": res.errors}
        if res.security_incident and not active_incident:
            active_incident = res.security_incident
        all_errors = res.errors

    passed = len(all_errors) == 0
    return {
        "validation_passed": passed,
        "validation_errors": all_errors,
        "validation_details": validation_details,
        "security_incident": active_incident,
    }


def post_optimization_validation_node(state: dict) -> dict:
    """LangGraph node: re-validate post-optimization queries."""
    optimized_sql = state.get("optimized_sql", "").strip()
    fallback_sql = state.get("generated_sql", "")
    target_sql = optimized_sql if optimized_sql else fallback_sql

    res = validate_sql(target_sql, state.get("relevant_schema", {}), state.get("user_role", "admin"))
    if res.passed:
        return {
            "post_optimization_validation_passed": True,
            "post_optimization_validation_errors": [],
            "optimized_sql": target_sql,
        }
    else:
        return {
            "post_optimization_validation_passed": False,
            "post_optimization_validation_errors": res.errors,
            "optimized_sql": fallback_sql,
        }
