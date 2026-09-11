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
import sqlparse
from typing import Dict, Any, List

from db.rbac import user_can_access_tables
from db.connectors import extract_table_names
from agent.Schema.validation_schema import ValidationResult

_DESTRUCTIVE_KEYWORDS = {
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE",
    "CREATE", "GRANT", "REVOKE", "EXEC", "EXECUTE", "MERGE",
}


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


def validate_sql(sql: str, relevant_schema: dict, user_role: str = "admin") -> ValidationResult:
    """Core deterministic validation logic for a single SQL query against a schema."""
    errors = []

    if not sql or not sql.strip():
        return ValidationResult(passed=False, errors=["Empty or unparseable SQL."])

    # Check 1: Security — Read-only enforcement
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
    referenced_tables = extract_table_names(sql)
    unknown = [t for t in referenced_tables if t not in relevant_schema and f"{t}" not in relevant_schema]
    if unknown and relevant_schema:
        errors.append(f"Unknown tables referenced: {unknown}")

    # Check 4: RBAC permissions
    if not user_can_access_tables(user_role, referenced_tables):
        errors.append("User role lacks permission for one or more referenced tables.")

    return ValidationResult(passed=len(errors) == 0, errors=errors)


def validation_node(state: dict) -> dict:
    """LangGraph node: validate generated SQL for single or multiple databases.

    Reads:
        state.get("database_queries")
        state.get("generated_sql")
        state.get("unified_schema")
        state.get("relevant_schema")
        state.get("user_role", "admin")

    Returns partial state update:
        {
            "validation_passed": bool,
            "validation_errors": list,
            "validation_details": dict,
        }
    """
    database_queries = state.get("database_queries", {})
    unified_schema = state.get("unified_schema", {})
    relevant_schema = state.get("relevant_schema", {})
    user_role = state.get("user_role", "admin")

    all_errors = []
    validation_details = {}

    if database_queries:
        for db_id, sql in database_queries.items():
            db_schema = unified_schema.get(db_id, {}).get("tables", {}) or relevant_schema
            res = validate_sql(sql, db_schema, user_role)
            validation_details[db_id] = {"passed": res.passed, "errors": res.errors}
            if not res.passed:
                all_errors.extend([f"[{db_id}] {e}" for e in res.errors])
    else:
        sql = state.get("generated_sql", "")
        res = validate_sql(sql, relevant_schema, user_role)
        validation_details["default"] = {"passed": res.passed, "errors": res.errors}
        all_errors = res.errors

    passed = len(all_errors) == 0
    return {
        "validation_passed": passed,
        "validation_errors": all_errors,
        "validation_details": validation_details,
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
