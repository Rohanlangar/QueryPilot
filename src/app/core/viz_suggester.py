"""
QueryPilot — Visualization Suggester

Infers the best chart type from query result shape:
column types, cardinality, GROUP BY patterns, and date detection.
"""

import re
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, date

logger = logging.getLogger(__name__)

# ── Date/Time detection patterns ──────────────────────────────
DATE_PATTERNS = [
    r"date", r"time", r"timestamp", r"created", r"updated",
    r"day", r"month", r"year", r"week", r"quarter", r"period",
]

GEO_PATTERNS = [
    r"country", r"state", r"province", r"city", r"region",
    r"district", r"zip", r"postal", r"county", r"territory",
    r"lat", r"lon", r"latitude", r"longitude",
]


class VizSuggester:
    """Infers optimal chart type from query results."""

    def _classify_column(self, col_name: str, values: List[Any]) -> str:
        """
        Classify a column as: 'date', 'numeric', 'geographic', 'categorical'.
        """
        col_lower = col_name.lower()

        # Check for date patterns
        for pattern in DATE_PATTERNS:
            if re.search(pattern, col_lower):
                return "date"

        # Check for geographic patterns
        for pattern in GEO_PATTERNS:
            if re.search(pattern, col_lower):
                return "geographic"

        # Check actual values
        if not values:
            return "categorical"

        # Sample non-None values
        sample = [v for v in values[:20] if v is not None]
        if not sample:
            return "categorical"

        # Check if numeric
        numeric_count = sum(1 for v in sample if isinstance(v, (int, float)))
        if numeric_count / len(sample) > 0.8:
            return "numeric"

        # Check if date-like strings
        date_count = 0
        for v in sample:
            if isinstance(v, (datetime, date)):
                date_count += 1
            elif isinstance(v, str):
                try:
                    # Try common date formats
                    for fmt in ["%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%m/%d/%Y"]:
                        try:
                            datetime.strptime(v[:19], fmt)
                            date_count += 1
                            break
                        except ValueError:
                            continue
                except Exception:
                    pass

        if date_count / len(sample) > 0.5:
            return "date"

        return "categorical"

    def suggest(
        self,
        columns: List[str],
        rows: List[Dict[str, Any]],
        sql: str = "",
    ) -> Dict[str, Any]:
        """
        Suggest the best chart type based on result shape.

        Returns:
            {
                "chart_type": "bar" | "line" | "pie" | "scatter" | "table" | "kpi" | "map",
                "x_axis": "column_name",
                "y_axis": "column_name",
                "config": {...}
            }
        """
        if not columns or not rows:
            return {"chart_type": "table", "x_axis": None, "y_axis": None, "config": {}}

        try:
            # Normalize rows: convert list-of-lists/tuples/etc. to list-of-dicts
            normalized_rows = []
            for r in rows:
                if isinstance(r, dict):
                    normalized_rows.append(r)
                elif isinstance(r, (list, tuple)):
                    normalized_rows.append(dict(zip(columns, r)))
                elif hasattr(r, "_asdict"):
                    normalized_rows.append(r._asdict())
                elif hasattr(r, "keys"):
                    normalized_rows.append(dict(r))
                else:
                    try:
                        normalized_rows.append(dict(zip(columns, list(r))))
                    except Exception:
                        normalized_rows.append({})
            rows = normalized_rows

            num_rows = len(rows)
            num_cols = len(columns)

            # Single scalar value → KPI card
            if num_rows == 1 and num_cols == 1:
                return {
                    "chart_type": "kpi",
                    "x_axis": None,
                    "y_axis": columns[0],
                    "config": {"value": rows[0].get(columns[0])},
                }

            # Classify each column
            col_types = {}
            for col in columns:
                values = [row.get(col) for row in rows]
                col_types[col] = self._classify_column(col, values)

            # Separate by type
            date_cols = [c for c, t in col_types.items() if t == "date"]
            numeric_cols = [c for c, t in col_types.items() if t == "numeric"]
            categorical_cols = [c for c, t in col_types.items() if t == "categorical"]
            geo_cols = [c for c, t in col_types.items() if t == "geographic"]

            # ── Decision Tree ─────────────────────────────────────

            # Geographic + numeric → Choropleth map
            if geo_cols and numeric_cols:
                return {
                    "chart_type": "map",
                    "x_axis": geo_cols[0],
                    "y_axis": numeric_cols[0],
                    "config": {"geo_column": geo_cols[0]},
                }

            # Date + numeric → Line chart (time series)
            if date_cols and numeric_cols:
                return {
                    "chart_type": "line",
                    "x_axis": date_cols[0],
                    "y_axis": numeric_cols[0],
                    "config": {
                        "additional_y": numeric_cols[1:] if len(numeric_cols) > 1 else [],
                    },
                }

            # 1 categorical + 1 numeric → Bar chart (or Pie if percentage/share)
            if len(categorical_cols) == 1 and len(numeric_cols) == 1:
                values = [row.get(numeric_cols[0]) for row in rows if row.get(numeric_cols[0]) is not None]
                total = sum(v for v in values if isinstance(v, (int, float)))
                num_col_lower = numeric_cols[0].lower()
                is_share = any(w in num_col_lower for w in ["percent", "pct", "share", "ratio", "proportion"])

                if num_rows <= 7 and (is_share or (98 <= total <= 102)):
                    return {
                        "chart_type": "pie",
                        "x_axis": categorical_cols[0],
                        "y_axis": numeric_cols[0],
                        "config": {},
                    }

                return {
                    "chart_type": "bar",
                    "x_axis": categorical_cols[0],
                    "y_axis": numeric_cols[0],
                    "config": {},
                }

            # 1 categorical + multiple numeric → Grouped bar
            if len(categorical_cols) >= 1 and len(numeric_cols) >= 2:
                return {
                    "chart_type": "bar",
                    "x_axis": categorical_cols[0],
                    "y_axis": numeric_cols[0],
                    "config": {
                        "grouped": True,
                        "additional_y": numeric_cols[1:],
                    },
                }

            # 2 numeric columns → Scatter plot
            if len(numeric_cols) >= 2 and num_rows > 5:
                return {
                    "chart_type": "scatter",
                    "x_axis": numeric_cols[0],
                    "y_axis": numeric_cols[1],
                    "config": {},
                }

            # Fallback → data table
            return {
                "chart_type": "table",
                "x_axis": None,
                "y_axis": None,
                "config": {"columns": columns},
            }

        except Exception as e:
            logger.warning(f"Error suggesting visualization: {e}")
            return {
                "chart_type": "table",
                "x_axis": None,
                "y_axis": None,
                "config": {"columns": columns if columns else []},
            }


# Singleton instance
viz_suggester = VizSuggester()
