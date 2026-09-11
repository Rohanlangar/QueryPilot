"""
QueryPilot — Connection Management Tests
"""

import pytest
from httpx import AsyncClient
from app.core.security import decrypt_credential


@pytest.mark.asyncio
async def test_create_connection(client: AsyncClient, auth_headers):
    payload = {
        "name": "Analytics PG",
        "db_type": "postgresql",
        "host": "postgres.internal.net",
        "port": 5432,
        "database_name": "analytics_db",
        "username": "readonly_user",
        "password": "SuperSecretPassword123!",
    }
    response = await client.post("/api/connections", json=payload, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Analytics PG"
    assert data["db_type"] == "postgresql"
    assert data["host"] == "postgres.internal.net"
    assert "password" not in data  # Ensure plaintext password is never returned
    conn_id = data["id"]

    # Retrieve connections
    list_resp = await client.get("/api/connections", headers=auth_headers)
    assert list_resp.status_code == 200
    items = list_resp.json()
    assert len(items) >= 1
    assert any(c["id"] == conn_id for c in items)


@pytest.mark.asyncio
async def test_delete_connection(client: AsyncClient, auth_headers):
    # First create
    create_resp = await client.post(
        "/api/connections",
        json={
            "name": "Temp DB",
            "db_type": "mysql",
            "host": "mysql.internal.net",
            "port": 3306,
            "database_name": "test_db",
            "username": "root",
            "password": "Password123",
        },
        headers=auth_headers,
    )
    conn_id = create_resp.json()["id"]

    # Delete
    del_resp = await client.delete(f"/api/connections/{conn_id}", headers=auth_headers)
    assert del_resp.status_code == 204

    # Verify not found
    get_resp = await client.get(f"/api/connections/{conn_id}", headers=auth_headers)
    assert get_resp.status_code == 404
