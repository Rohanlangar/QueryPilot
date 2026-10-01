"""Role-Based Access Control (RBAC) for table-level permissions.

Defines role allowlists and validates whether a given user role
is authorized to query all requested tables.
"""

from typing import List, Optional, Dict, Set

# Table-level permissions per role
# None indicates unrestricted access (all tables allowed)
ROLE_TABLE_PERMISSIONS: Dict[str, Optional[Set[str]]] = {
    "admin": None,  # Full access to all tables including confidential data
    "analyst": {
        "departments",
        "employees",
        "projects",
        "employee_projects",
        "customers",
        "orders",
        "order_items",
        # Explicitly excludes 'salaries'
    },
    "viewer": {
        "departments",
        "projects",
        "customers",
        "orders",
        "order_items",
        # Excludes 'employees' (PII) and 'salaries'
    },
}


import os
import sqlite3

APP_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "querypilot.db")


def user_can_access_tables(user_role: str, tables: List[str], connection_id: Optional[str] = None) -> bool:
    """Check if a user role has permission to access all referenced tables.

    Args:
        user_role: Role name (e.g. 'admin', 'analyst', 'viewer')
        tables: List of table names referenced in the query
        connection_id: Optional registered database connection ID

    Returns:
        True if the user has permission for every table, False otherwise.
    """
    normalized_role = (user_role or "").strip().lower()
    if normalized_role == "admin":
        return True

    # Check for dynamic database-backed table policies in querypilot.db
    if connection_id and os.path.exists(APP_DB_PATH):
        try:
            with sqlite3.connect(APP_DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT tp.table_name, tp.allowed
                    FROM table_policies tp
                    JOIN roles r ON tp.role_id = r.id
                    WHERE LOWER(r.name) = ? AND tp.connection_id = ?
                    """,
                    (normalized_role, connection_id),
                )
                rows = cur.fetchall()
                if rows:
                    policy_map = {row[0].strip().lower(): bool(row[1]) for row in rows}
                    # If explicit policies exist, check whether any referenced table is blocked
                    for table in tables:
                        t_lower = table.strip().lower()
                        if t_lower in policy_map and not policy_map[t_lower]:
                            return False
                    return True
        except Exception:
            pass

    # Fallback to built-in static table allowlist for company.db / demo
    if normalized_role not in ROLE_TABLE_PERMISSIONS:
        return False

    allowed_tables = ROLE_TABLE_PERMISSIONS[normalized_role]
    if allowed_tables is None:
        return True

    # Check case-insensitively
    allowed_lower = {t.lower() for t in allowed_tables}
    return all(table.strip().lower() in allowed_lower for table in tables)
