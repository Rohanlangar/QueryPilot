"""
QueryPilot — High-Fidelity Schema Sample Provider for ERD Visualization.
Used when external database server is offline or during interactive demos.
"""

from typing import Dict, Any, List


def get_sample_erd_for_connection(database_name: str = "", db_type: str = "postgresql") -> Dict[str, Any]:
    """Return a complete schema with tables, columns, and foreign keys matching real PostgreSQL schemas."""
    tables = [
        {
            "name": "users_user",
            "schema": "public",
            "row_count": 1284,
            "columns": [
                {"name": "id", "type": "bigint (IDENTITY)", "is_primary_key": True, "is_foreign_key": False, "is_nullable": False},
                {"name": "password", "type": "character varying(128)", "is_primary_key": False, "is_foreign_key": False, "is_nullable": False},
                {"name": "last_login", "type": "timestamp with time zone", "is_primary_key": False, "is_foreign_key": False, "is_nullable": True},
                {"name": "is_superuser", "type": "boolean", "is_primary_key": False, "is_foreign_key": False, "is_nullable": False},
                {"name": "username", "type": "character varying(150)", "is_primary_key": False, "is_foreign_key": False, "is_nullable": False},
                {"name": "first_name", "type": "character varying(150)", "is_primary_key": False, "is_foreign_key": False, "is_nullable": True},
                {"name": "last_name", "type": "character varying(150)", "is_primary_key": False, "is_foreign_key": False, "is_nullable": True},
                {"name": "email", "type": "character varying(254)", "is_primary_key": False, "is_foreign_key": False, "is_nullable": True},
                {"name": "is_staff", "type": "boolean", "is_primary_key": False, "is_foreign_key": False, "is_nullable": False},
                {"name": "is_active", "type": "boolean", "is_primary_key": False, "is_foreign_key": False, "is_nullable": False},
                {"name": "date_joined", "type": "timestamp with time zone", "is_primary_key": False, "is_foreign_key": False, "is_nullable": False},
            ],
            "foreign_keys": [],
        },
        {
            "name": "room_room",
            "schema": "public",
            "row_count": 420,
            "columns": [
                {"name": "id", "type": "bigint (IDENTITY)", "is_primary_key": True, "is_foreign_key": False, "is_nullable": False},
                {"name": "name", "type": "character varying(100)", "is_primary_key": False, "is_foreign_key": False, "is_nullable": False},
                {"name": "description", "type": "text", "is_primary_key": False, "is_foreign_key": False, "is_nullable": True},
                {"name": "created_at", "type": "timestamp with time zone", "is_primary_key": False, "is_foreign_key": False, "is_nullable": False},
                {"name": "created_by_id", "type": "bigint", "is_primary_key": False, "is_foreign_key": True, "is_nullable": True},
            ],
            "foreign_keys": [
                {"column": "created_by_id", "references_table": "users_user", "references_column": "id"}
            ],
        },
        {
            "name": "auth_group",
            "schema": "public",
            "row_count": 8,
            "columns": [
                {"name": "id", "type": "integer (IDENTITY)", "is_primary_key": True, "is_foreign_key": False, "is_nullable": False},
                {"name": "name", "type": "character varying(150)", "is_primary_key": False, "is_foreign_key": False, "is_nullable": False},
            ],
            "foreign_keys": [],
        },
        {
            "name": "auth_permission",
            "schema": "public",
            "row_count": 52,
            "columns": [
                {"name": "id", "type": "integer (IDENTITY)", "is_primary_key": True, "is_foreign_key": False, "is_nullable": False},
                {"name": "name", "type": "character varying(255)", "is_primary_key": False, "is_foreign_key": False, "is_nullable": False},
                {"name": "content_type_id", "type": "integer", "is_primary_key": False, "is_foreign_key": True, "is_nullable": False},
                {"name": "codename", "type": "character varying(100)", "is_primary_key": False, "is_foreign_key": False, "is_nullable": False},
            ],
            "foreign_keys": [
                {"column": "content_type_id", "references_table": "django_content_type", "references_column": "id"}
            ],
        },
        {
            "name": "users_user_groups",
            "schema": "public",
            "row_count": 210,
            "columns": [
                {"name": "id", "type": "bigint (IDENTITY)", "is_primary_key": True, "is_foreign_key": False, "is_nullable": False},
                {"name": "user_id", "type": "bigint", "is_primary_key": False, "is_foreign_key": True, "is_nullable": False},
                {"name": "group_id", "type": "integer", "is_primary_key": False, "is_foreign_key": True, "is_nullable": False},
            ],
            "foreign_keys": [
                {"column": "user_id", "references_table": "users_user", "references_column": "id"},
                {"column": "group_id", "references_table": "auth_group", "references_column": "id"},
            ],
        },
        {
            "name": "users_user_user_permissions",
            "schema": "public",
            "row_count": 95,
            "columns": [
                {"name": "id", "type": "bigint (IDENTITY)", "is_primary_key": True, "is_foreign_key": False, "is_nullable": False},
                {"name": "user_id", "type": "bigint", "is_primary_key": False, "is_foreign_key": True, "is_nullable": False},
                {"name": "permission_id", "type": "integer", "is_primary_key": False, "is_foreign_key": True, "is_nullable": False},
            ],
            "foreign_keys": [
                {"column": "user_id", "references_table": "users_user", "references_column": "id"},
                {"column": "permission_id", "references_table": "auth_permission", "references_column": "id"},
            ],
        },
        {
            "name": "auth_group_permissions",
            "schema": "public",
            "row_count": 84,
            "columns": [
                {"name": "id", "type": "bigint (IDENTITY)", "is_primary_key": True, "is_foreign_key": False, "is_nullable": False},
                {"name": "group_id", "type": "integer", "is_primary_key": False, "is_foreign_key": True, "is_nullable": False},
                {"name": "permission_id", "type": "integer", "is_primary_key": False, "is_foreign_key": True, "is_nullable": False},
            ],
            "foreign_keys": [
                {"column": "group_id", "references_table": "auth_group", "references_column": "id"},
                {"column": "permission_id", "references_table": "auth_permission", "references_column": "id"},
            ],
        },
        {
            "name": "authtoken_token",
            "schema": "public",
            "row_count": 650,
            "columns": [
                {"name": "key", "type": "character varying(40)", "is_primary_key": True, "is_foreign_key": False, "is_nullable": False},
                {"name": "created", "type": "timestamp with time zone", "is_primary_key": False, "is_foreign_key": False, "is_nullable": False},
                {"name": "user_id", "type": "bigint", "is_primary_key": False, "is_foreign_key": True, "is_nullable": False},
            ],
            "foreign_keys": [
                {"column": "user_id", "references_table": "users_user", "references_column": "id"}
            ],
        },
        {
            "name": "django_admin_log",
            "schema": "public",
            "row_count": 310,
            "columns": [
                {"name": "id", "type": "integer (IDENTITY)", "is_primary_key": True, "is_foreign_key": False, "is_nullable": False},
                {"name": "action_time", "type": "timestamp with time zone", "is_primary_key": False, "is_foreign_key": False, "is_nullable": False},
                {"name": "object_id", "type": "text", "is_primary_key": False, "is_foreign_key": False, "is_nullable": True},
                {"name": "object_repr", "type": "character varying(200)", "is_primary_key": False, "is_foreign_key": False, "is_nullable": False},
                {"name": "action_flag", "type": "smallint", "is_primary_key": False, "is_foreign_key": False, "is_nullable": False},
                {"name": "change_message", "type": "text", "is_primary_key": False, "is_foreign_key": False, "is_nullable": False},
                {"name": "content_type_id", "type": "integer", "is_primary_key": False, "is_foreign_key": True, "is_nullable": True},
                {"name": "user_id", "type": "bigint", "is_primary_key": False, "is_foreign_key": True, "is_nullable": False},
            ],
            "foreign_keys": [
                {"column": "user_id", "references_table": "users_user", "references_column": "id"},
                {"column": "content_type_id", "references_table": "django_content_type", "references_column": "id"},
            ],
        },
        {
            "name": "django_content_type",
            "schema": "public",
            "row_count": 16,
            "columns": [
                {"name": "id", "type": "integer (IDENTITY)", "is_primary_key": True, "is_foreign_key": False, "is_nullable": False},
                {"name": "app_label", "type": "character varying(100)", "is_primary_key": False, "is_foreign_key": False, "is_nullable": False},
                {"name": "model", "type": "character varying(100)", "is_primary_key": False, "is_foreign_key": False, "is_nullable": False},
            ],
            "foreign_keys": [],
        },
        {
            "name": "django_migrations",
            "schema": "public",
            "row_count": 28,
            "columns": [
                {"name": "id", "type": "bigint (IDENTITY)", "is_primary_key": True, "is_foreign_key": False, "is_nullable": False},
                {"name": "app", "type": "character varying(255)", "is_primary_key": False, "is_foreign_key": False, "is_nullable": False},
                {"name": "name", "type": "character varying(255)", "is_primary_key": False, "is_foreign_key": False, "is_nullable": False},
                {"name": "applied", "type": "timestamp with time zone", "is_primary_key": False, "is_foreign_key": False, "is_nullable": False},
            ],
            "foreign_keys": [],
        },
        {
            "name": "django_session",
            "schema": "public",
            "row_count": 82,
            "columns": [
                {"name": "session_key", "type": "character varying(40)", "is_primary_key": True, "is_foreign_key": False, "is_nullable": False},
                {"name": "session_data", "type": "text", "is_primary_key": False, "is_foreign_key": False, "is_nullable": False},
                {"name": "expire_date", "type": "timestamp with time zone", "is_primary_key": False, "is_foreign_key": False, "is_nullable": False},
            ],
            "foreign_keys": [],
        },
    ]

    relationships = [
        {"id": "users_user_groups.user_id->users_user.id", "from_table": "users_user_groups", "from_column": "user_id", "to_table": "users_user", "to_column": "id"},
        {"id": "users_user_groups.group_id->auth_group.id", "from_table": "users_user_groups", "from_column": "group_id", "to_table": "auth_group", "to_column": "id"},
        {"id": "users_user_user_permissions.user_id->users_user.id", "from_table": "users_user_user_permissions", "from_column": "user_id", "to_table": "users_user", "to_column": "id"},
        {"id": "users_user_user_permissions.permission_id->auth_permission.id", "from_table": "users_user_user_permissions", "from_column": "permission_id", "to_table": "auth_permission", "to_column": "id"},
        {"id": "auth_group_permissions.group_id->auth_group.id", "from_table": "auth_group_permissions", "from_column": "group_id", "to_table": "auth_group", "to_column": "id"},
        {"id": "auth_group_permissions.permission_id->auth_permission.id", "from_table": "auth_group_permissions", "from_column": "permission_id", "to_table": "auth_permission", "to_column": "id"},
        {"id": "authtoken_token.user_id->users_user.id", "from_table": "authtoken_token", "from_column": "user_id", "to_table": "users_user", "to_column": "id"},
        {"id": "room_room.created_by_id->users_user.id", "from_table": "room_room", "from_column": "created_by_id", "to_table": "users_user", "to_column": "id"},
        {"id": "auth_permission.content_type_id->django_content_type.id", "from_table": "auth_permission", "from_column": "content_type_id", "to_table": "django_content_type", "to_column": "id"},
        {"id": "django_admin_log.user_id->users_user.id", "from_table": "django_admin_log", "from_column": "user_id", "to_table": "users_user", "to_column": "id"},
        {"id": "django_admin_log.content_type_id->django_content_type.id", "from_table": "django_admin_log", "from_column": "content_type_id", "to_table": "django_content_type", "to_column": "id"},
    ]

    return {
        "tables": tables,
        "relationships": relationships,
    }
