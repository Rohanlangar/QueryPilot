# agent/validation_agent.py
"""Validation Agent — Graph Node (Deterministic).

This is the reliability backbone of the pipeline. It NEVER calls an LLM:
SQL syntax, schema compliance, and RBAC are exact-match problems, not
judgment calls.

Checks:
  1. SQL is parseable (sqlparse)
  2. All referenced tables exist in the relevant schema
  3. User role has RBAC permission for all referenced tables
"""

import re
from typing import Optional
import sqlparse

from db.rbac import user_can_access_tables
from db.connectors import extract_table_names
from agent.Schema.validation_schema import ValidationResult

WRITE_PATTERNS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|GRANT|REVOKE|EXEC|EXECUTE)\b",
    re.IGNORECASE,
)


def validate_sql(
    sql: str,
    relevant_schema: dict,
    user_role: str,
    connection_id: Optional[str] = None,
) -> ValidationResult:
    """Core deterministic validation logic for any SQL query."""
    errors = []

    # Check 1: SQL is parseable and single statement
    try:
        parsed = sqlparse.parse(sql)
        if not parsed or not sql.strip():
            errors.append("Empty or unparseable SQL.")
        elif len([s for s in parsed if str(s).strip()]) > 1:
            errors.append("Multiple statements are not permitted for security reasons.")
    except Exception as e:
        errors.append(f"Syntax error: {e}")

    # Check 2: Strictly read-only query check (no DML/DDL)
    cleaned_sql = re.sub(r"--.*$", "", sql, flags=re.MULTILINE)
    cleaned_sql = re.sub(r"/\*.*?\*/", "", cleaned_sql, flags=re.DOTALL)
    if WRITE_PATTERNS.search(cleaned_sql):
        errors.append(
            "Write operations (INSERT, UPDATE, DELETE, DROP, etc.) are strictly prohibited. Only SELECT queries are permitted."
        )

    # Check 3: All referenced tables exist in the selected schema
    referenced_tables = extract_table_names(sql)
    unknown = [t for t in referenced_tables if t not in relevant_schema]
    if unknown:
        errors.append(f"Unknown tables referenced: {unknown}")

    # Check 4: RBAC — user role can access all referenced tables
    if not user_can_access_tables(user_role, referenced_tables, connection_id=connection_id):
        errors.append(
            "User role lacks permission for one or more referenced tables."
        )

    return ValidationResult(passed=len(errors) == 0, errors=errors)


def validation_node(state: dict) -> dict:
    """LangGraph node: deterministic validation of initially generated SQL."""
    result = validate_sql(
        sql=state.get("generated_sql", ""),
        relevant_schema=state.get("relevant_schema", {}),
        user_role=state.get("user_role", "admin"),
        connection_id=state.get("connection_id"),
    )
    return {
        "validation_passed": result.passed,
        "validation_errors": result.errors,
    }


def post_optimization_validation_node(state: dict) -> dict:
    """LangGraph node: re-validate the SQL after the Optimization Agent has modified it.

    If the optimized SQL passes validation, it proceeds.
    If the optimizer introduced syntax errors or unauthorized tables, it logs
    the error and safely reverts to the validated generated_sql.
    """
    optimized_sql = state.get("optimized_sql", "").strip()
    fallback_sql = state.get("generated_sql", "")

    if not optimized_sql:
        optimized_sql = fallback_sql

    result = validate_sql(
        sql=optimized_sql,
        relevant_schema=state.get("relevant_schema", {}),
        user_role=state.get("user_role", "admin"),
        connection_id=state.get("connection_id"),
    )

    if result.passed:
        return {
            "post_optimization_validation_passed": True,
            "post_optimization_validation_errors": [],
            "optimized_sql": optimized_sql,
        }
    else:
        # Fallback to generated_sql to protect execution
        return {
            "post_optimization_validation_passed": False,
            "post_optimization_validation_errors": result.errors,
            "optimized_sql": fallback_sql,  # Revert to safe generated SQL
        }
