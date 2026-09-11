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


def user_can_access_tables(user_role: str, tables: List[str]) -> bool:
    """Check if a user role has permission to access all referenced tables.

    Args:
        user_role: Role name (e.g. 'admin', 'analyst', 'viewer')
        tables: List of table names referenced in the query

    Returns:
        True if the user has permission for every table, False otherwise.
    """
    normalized_role = (user_role or "").strip().lower()
    if normalized_role not in ROLE_TABLE_PERMISSIONS:
        return False

    allowed_tables = ROLE_TABLE_PERMISSIONS[normalized_role]
    if allowed_tables is None:
        return True

    # Check case-insensitively
    allowed_lower = {t.lower() for t in allowed_tables}
    return all(table.strip().lower() in allowed_lower for table in tables)
