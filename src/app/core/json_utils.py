"""
QueryPilot — JSON Utilities

Robust JSON serialization supporting datetime, date, Decimal, UUID, bytes, etc.
"""

import json
from datetime import date, datetime, time
from decimal import Decimal
import uuid
from typing import Any


def json_serial(obj: Any) -> Any:
    """Fallback JSON serializer for types not handled by standard json."""
    if isinstance(obj, (datetime, date, time)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, uuid.UUID):
        return str(obj)
    if isinstance(obj, (bytes, bytearray)):
        return obj.hex()
    if hasattr(obj, "__dict__"):
        return obj.__dict__
    return str(obj)


def safe_json_dumps(obj: Any, **kwargs) -> str:
    """Safely dump an object to JSON, converting non-standard types."""
    kwargs.setdefault("default", json_serial)
    return json.dumps(obj, **kwargs)
