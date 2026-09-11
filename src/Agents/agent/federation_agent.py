"""Federation / Join Agent — LangGraph Node.

Combines query results from multiple independent databases at the application level.
Performs in-memory hash joins, column disambiguation, filtering, and aggregation.
Generates an execution plan diagram and attributes sources used.
"""

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("querypilot.federation")


def _build_execution_diagram(required_dbs: List[str], join_keys: List[Dict[str, str]]) -> str:
    """Generate an ASCII visual representation of the cross-database execution plan."""
    if len(required_dbs) < 2:
        db = required_dbs[0] if required_dbs else "primary_db"
        return f"{db} (Direct Query Execution)"

    lines = []
    if join_keys:
        for i, jk in enumerate(join_keys):
            db1 = jk.get("db1", "Database A")
            col1 = jk.get("col1", "id")
            db2 = jk.get("db2", "Database B")
            col2 = jk.get("col2", "id")
            lines.append(f"{db1}")
            lines.append(f"  │")
            lines.append(f"  │ {col1} == {col2}")
            lines.append(f"  ▼")
            lines.append(f"{db2}")
    else:
        for i, db in enumerate(required_dbs):
            lines.append(f"[{db}]")
            if i < len(required_dbs) - 1:
                lines.append("  │")
                lines.append("  ▼ (application merge)")

    return "\n".join(lines)


def _hash_join_datasets(
    left_rows: List[Dict[str, Any]],
    right_rows: List[Dict[str, Any]],
    left_col: str,
    right_col: str,
    join_type: str = "inner",
    left_db: str = "db1",
    right_db: str = "db2",
) -> List[Dict[str, Any]]:
    """Perform in-memory hash join between two row sets."""
    # Build hash table on right dataset: key -> list of rows
    hash_table: Dict[str, List[Dict[str, Any]]] = {}
    for r_row in right_rows:
        val = r_row.get(right_col)
        if val is not None:
            norm_key = str(val).strip().lower()
            hash_table.setdefault(norm_key, []).append(r_row)

    merged: List[Dict[str, Any]] = []

    for l_row in left_rows:
        l_val = l_row.get(left_col)
        norm_key = str(l_val).strip().lower() if l_val is not None else None
        matches = hash_table.get(norm_key, [])

        if matches:
            for r_row in matches:
                combined = dict(l_row)
                for k, v in r_row.items():
                    if k in combined and k != right_col:
                        combined[f"{right_db}_{k}"] = v
                    else:
                        combined[k] = v
                merged.append(combined)
        elif join_type in ("left", "outer"):
            combined = dict(l_row)
            merged.append(combined)

    return merged


def _apply_heuristic_post_filters(rows: List[Dict[str, Any]], question: str) -> List[Dict[str, Any]]:
    """Apply question-driven post-join sorting and filtering (e.g. high demand & low inventory)."""
    if not rows:
        return rows

    q_lower = question.lower()
    first = rows[0]

    # Find demand/quantity and stock/inventory columns if present
    demand_col = next((c for c in first.keys() if any(w in c.lower() for w in ("demand", "qty", "quantity", "total_orders"))), None)
    stock_col = next((c for c in first.keys() if any(w in c.lower() for w in ("stock", "inventory", "stock_quantity"))), None)

    # Filter: "below X" or "less than X"
    import re
    below_match = re.search(r'\b(?:below|under|less than|<)\s+(\d+)', q_lower)
    if below_match and stock_col:
        threshold = float(below_match.group(1))
        filtered = []
        for r in rows:
            try:
                if float(r.get(stock_col, 0)) < threshold:
                    filtered.append(r)
            except (ValueError, TypeError):
                filtered.append(r)
        if filtered:
            return filtered

    # Filter: "high demand but low inventory"
    if ("high demand" in q_lower or "demand" in q_lower) and ("low inventory" in q_lower or "low stock" in q_lower):
        if demand_col and stock_col:
            scored = []
            for r in rows:
                try:
                    dem = float(r.get(demand_col, 0) or 0)
                    stk = float(r.get(stock_col, 0) or 0)
                    # ratio or difference: higher demand relative to stock
                    ratio = dem / max(stk, 1)
                    scored.append((ratio, r))
                except (ValueError, TypeError):
                    scored.append((0, r))
            scored.sort(key=lambda x: -x[0])
            return [item[1] for item in scored]

    return rows


def federation_agent_node(state: dict) -> dict:
    """LangGraph node: join and synthesize datasets from multiple databases.

    Reads:
        state["database_results"]
        state.get("query_plan", {})
        state.get("is_federated", False)
        state.get("question", "")

    Returns partial state update:
        {
            "federated_result": dict,
            "query_result": list,
            "row_count": int,
            "sources_used": list,
            "execution_plan_diagram": str,
        }
    """
    db_results = state.get("database_results", {})
    query_plan = state.get("query_plan", {})
    is_federated = state.get("is_federated", False)
    question = state.get("question", "")

    required_dbs = query_plan.get("required_databases", list(db_results.keys()))
    join_keys = query_plan.get("join_keys", [])
    join_type = query_plan.get("join_type", "inner")
    required_tables = query_plan.get("required_tables", {})

    # Sources attribution
    sources_used = []
    for db in required_dbs:
        tbls = required_tables.get(db) or []
        if not tbls and db in db_results:
            tbls = ["records"]
        sources_used.append({"database": db, "tables": tbls})

    diagram = _build_execution_diagram(required_dbs, join_keys)

    # If single database query or only one result set exists
    if not is_federated or len(db_results) <= 1:
        target_db = next(iter(db_results.keys())) if db_results else "default"
        res_data = db_results.get(target_db, {"columns": [], "rows": [], "row_count": 0})
        rows = res_data.get("rows", [])
        cols = res_data.get("columns", list(rows[0].keys()) if rows else [])

        logger.info(f"[FEDERATION] Single database result ({target_db}): {len(rows)} rows")
        return {
            "federated_result": {"columns": cols, "rows": rows, "row_count": len(rows)},
            "query_result": rows,
            "row_count": len(rows),
            "sources_used": sources_used,
            "execution_plan_diagram": diagram,
        }

    # ── Multi-Database Application-Level Federation ───────────────────────
    dbs = [db for db in required_dbs if db in db_results]
    if not dbs:
        dbs = list(db_results.keys())

    base_db = dbs[0]
    unified_rows = list(db_results[base_db].get("rows", []))

    for i in range(1, len(dbs)):
        next_db = dbs[i]
        next_rows = db_results[next_db].get("rows", [])

        # Find join key mapping between base_db and next_db
        matching_jk = next(
            (
                jk for jk in join_keys
                if (jk.get("db1") == base_db and jk.get("db2") == next_db)
                or (jk.get("db2") == base_db and jk.get("db1") == next_db)
            ),
            None,
        )

        left_col = None
        right_col = None
        if matching_jk:
            if matching_jk.get("db1") == base_db:
                left_col = matching_jk.get("col1")
                right_col = matching_jk.get("col2")
            else:
                left_col = matching_jk.get("col2")
                right_col = matching_jk.get("col1")
        else:
            # Fallback: look for common column name ending in _id
            if unified_rows and next_rows:
                common_cols = set(unified_rows[0].keys()).intersection(set(next_rows[0].keys()))
                id_col = next((c for c in common_cols if c.endswith("_id") or c == "id"), None)
                if id_col:
                    left_col = id_col
                    right_col = id_col

        if left_col and right_col:
            unified_rows = _hash_join_datasets(
                left_rows=unified_rows,
                right_rows=next_rows,
                left_col=left_col,
                right_col=right_col,
                join_type=join_type,
                left_db=base_db,
                right_db=next_db,
            )
            logger.info(
                f"[FEDERATION] In-memory hash join ({base_db}.{left_col} <-> {next_db}.{right_col}) "
                f"yielded {len(unified_rows)} combined rows"
            )
        else:
            # If no common key, Cartesian / concatenated merge
            logger.warning(f"[FEDERATION] No common join key found between {base_db} and {next_db}")

    # Post-join filtering and sorting
    unified_rows = _apply_heuristic_post_filters(unified_rows, question)
    unified_columns = list(unified_rows[0].keys()) if unified_rows else []

    logger.info(f"[FEDERATION] Final Unified Result: {len(unified_rows)} rows across {dbs}")

    return {
        "federated_result": {
            "columns": unified_columns,
            "rows": unified_rows,
            "row_count": len(unified_rows),
        },
        "query_result": unified_rows,
        "row_count": len(unified_rows),
        "sources_used": sources_used,
        "execution_plan_diagram": diagram,
    }
