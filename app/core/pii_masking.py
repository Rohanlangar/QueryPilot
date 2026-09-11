"""
QueryPilot — PII Masking Engine

Masks sensitive data (emails, SSNs, phone numbers, names, etc.)
in query results based on column PII tags and RBAC policies.
"""

import re
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


# ── Masking Strategies ────────────────────────────────────────

def mask_email(value: str) -> str:
    """Mask email: j***@example.com"""
    if not value or "@" not in str(value):
        return "[REDACTED]"
    value = str(value)
    local, domain = value.split("@", 1)
    if len(local) <= 1:
        return f"*@{domain}"
    return f"{local[0]}***@{domain}"


def mask_ssn(value: str) -> str:
    """Mask SSN: ***-**-1234"""
    value = str(value)
    # Extract last 4 digits
    digits = re.sub(r"\D", "", value)
    if len(digits) >= 4:
        return f"***-**-{digits[-4:]}"
    return "[REDACTED]"


def mask_phone(value: str) -> str:
    """Mask phone: ***-***-5678"""
    value = str(value)
    digits = re.sub(r"\D", "", value)
    if len(digits) >= 4:
        return f"***-***-{digits[-4:]}"
    return "[REDACTED]"


def mask_name(value: str) -> str:
    """Mask name: J*** D***"""
    if not value:
        return "[REDACTED]"
    value = str(value)
    parts = value.split()
    masked_parts = []
    for part in parts:
        if len(part) <= 1:
            masked_parts.append("*")
        else:
            masked_parts.append(f"{part[0]}***")
    return " ".join(masked_parts)


def mask_address(value: str) -> str:
    """Mask address: show only city/state portion."""
    if not value:
        return "[REDACTED]"
    value = str(value)
    # Show last portion (likely city/state/zip)
    parts = value.split(",")
    if len(parts) > 1:
        return f"***, {parts[-1].strip()}"
    return "[REDACTED]"


def mask_default(value: Any) -> str:
    """Default masking — full redaction."""
    return "[REDACTED]"


# ── Masking Strategy Map ──────────────────────────────────────
MASKING_STRATEGIES = {
    "email": mask_email,
    "ssn": mask_ssn,
    "phone": mask_phone,
    "name": mask_name,
    "address": mask_address,
    "default": mask_default,
}


class PIIMaskingEngine:
    """
    Masks sensitive data in query results based on PII tags and user clearance.
    """

    def mask_results(
        self,
        columns: List[str],
        rows: List[Dict[str, Any]],
        sensitive_columns: Dict[str, str],  # {column_name: pii_type}
        blocked_columns: List[str],
    ) -> tuple:
        """
        Apply PII masking to query results.

        Args:
            columns: List of column names in the result
            rows: List of row dicts
            sensitive_columns: {col_name: pii_type} — columns to mask
            blocked_columns: column names to remove entirely

        Returns:
            (filtered_columns, masked_rows) — columns without blocked,
            rows with sensitive values masked
        """
        # Remove blocked columns
        filtered_columns = [c for c in columns if c not in blocked_columns]

        masked_rows = []
        for row in rows:
            masked_row = {}
            for col in filtered_columns:
                value = row.get(col)

                if col in sensitive_columns:
                    pii_type = sensitive_columns[col]
                    mask_fn = MASKING_STRATEGIES.get(pii_type, mask_default)
                    masked_row[col] = mask_fn(value) if value is not None else None
                else:
                    masked_row[col] = value

            masked_rows.append(masked_row)

        return filtered_columns, masked_rows

    def detect_pii_columns(self, column_names: List[str]) -> Dict[str, str]:
        """
        Auto-detect potentially PII columns based on naming conventions.
        Returns {column_name: pii_type} for suspected PII columns.

        This is a heuristic — flagged columns should be reviewed by an admin.
        """
        detections = {}

        pii_patterns = {
            "email": [r"e[-_]?mail", r"email[-_]?addr"],
            "ssn": [r"ssn", r"social[-_]?sec", r"national[-_]?id"],
            "phone": [r"phone", r"tel", r"mobile", r"cell"],
            "name": [r"first[-_]?name", r"last[-_]?name", r"full[-_]?name", r"customer[-_]?name"],
            "address": [r"address", r"street", r"addr"],
        }

        for col in column_names:
            col_lower = col.lower()
            for pii_type, patterns in pii_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, col_lower):
                        detections[col] = pii_type
                        break
                if col in detections:
                    break

        return detections


# Singleton instance
pii_engine = PIIMaskingEngine()
