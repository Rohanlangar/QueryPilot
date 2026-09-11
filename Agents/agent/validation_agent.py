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

import sqlparse

from db.rbac import user_can_access_tables
from db.connectors import extract_table_names
from agent.Schema.validation_schema import ValidationResult


def validate_sql(sql: str, relevant_schema: dict, user_role: str) -> ValidationResult:
    """Core deterministic validation logic for any SQL query."""
    errors = []

    # Check 1: SQL is parseable
    try:
        parsed = sqlparse.parse(sql)
        if not parsed or not sql.strip():
            errors.append("Empty or unparseable SQL.")
    except Exception as e:
        errors.append(f"Syntax error: {e}")

    # Check 2: All referenced tables exist in the selected schema
    referenced_tables = extract_table_names(sql)
    unknown = [t for t in referenced_tables if t not in relevant_schema]
    if unknown:
        errors.append(f"Unknown tables referenced: {unknown}")

    # Check 3: RBAC — user role can access all referenced tables
    if not user_can_access_tables(user_role, referenced_tables):
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
