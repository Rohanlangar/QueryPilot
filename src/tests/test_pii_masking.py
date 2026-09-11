"""
QueryPilot — PII Masking Engine Tests
"""

import pytest
from app.core.pii_masking import (
    mask_email,
    mask_ssn,
    mask_phone,
    mask_name,
    PIIMaskingEngine,
)


def test_mask_email():
    assert mask_email("john.doe@example.com") == "j***@example.com"
    assert mask_email("a@example.com") == "*@example.com"
    assert mask_email("") == "[REDACTED]"
    assert mask_email(None) == "[REDACTED]"


def test_mask_ssn():
    assert mask_ssn("123-45-6789") == "***-**-6789"
    assert mask_ssn("123456789") == "***-**-6789"
    assert mask_ssn("12") == "[REDACTED]"


def test_mask_phone():
    assert mask_phone("+1 (555) 234-5678") == "***-***-5678"
    assert mask_phone("5551234567") == "***-***-4567"
    assert mask_phone("12") == "[REDACTED]"


def test_mask_name():
    assert mask_name("John Doe") == "J*** D***"
    assert mask_name("Alice") == "A***"
    assert mask_name("") == "[REDACTED]"


def test_mask_results_engine():
    engine = PIIMaskingEngine()
    columns = ["id", "full_name", "email", "ssn", "internal_secret"]
    rows = [
        {
            "id": 1,
            "full_name": "Bruce Wayne",
            "email": "bruce@waynecorp.com",
            "ssn": "111-22-3333",
            "internal_secret": "top_secret_code",
        },
        {
            "id": 2,
            "full_name": "Clark Kent",
            "email": "clark@dailyplanet.com",
            "ssn": "999-88-7777",
            "internal_secret": "krypton",
        },
    ]

    sensitive = {"email": "email", "ssn": "ssn", "full_name": "name"}
    blocked = ["internal_secret"]

    filtered_cols, masked_rows = engine.mask_results(
        columns=columns,
        rows=rows,
        sensitive_columns=sensitive,
        blocked_columns=blocked,
    )

    assert "internal_secret" not in filtered_cols
    assert "email" in filtered_cols
    assert len(masked_rows) == 2

    # Check Bruce Wayne row
    row0 = masked_rows[0]
    assert row0["id"] == 1
    assert row0["full_name"] == "B*** W***"
    assert row0["email"] == "b***@waynecorp.com"
    assert row0["ssn"] == "***-**-3333"
    assert "internal_secret" not in row0
