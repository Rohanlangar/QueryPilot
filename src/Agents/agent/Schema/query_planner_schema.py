"""Pydantic schemas for the Query Planning Agent in the Federated SQL pipeline."""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class JoinKeyMapping(BaseModel):
    """Mapping between two database join columns."""
    db1: str = Field(..., description="First database ID / name")
    col1: str = Field(..., description="Column name in first database")
    db2: str = Field(..., description="Second database ID / name")
    col2: str = Field(..., description="Column name in second database")


class QueryPlanOutput(BaseModel):
    """Structured plan produced by the Query Planning Agent."""
    is_federated: bool = Field(
        ...,
        description="True if the question requires data from 2 or more independent databases, False if exactly 1 database suffices"
    )
    required_databases: List[str] = Field(
        ...,
        description="List of database IDs needed to answer the question (e.g. ['order_db', 'inventory_db'])"
    )
    required_tables: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Dictionary mapping each database ID to the specific tables needed from it (e.g. {'order_db': ['orders'], 'inventory_db': ['inventory']})"
    )
    sub_goals: Dict[str, str] = Field(
        default_factory=dict,
        description="Specific query objective for each database (e.g. {'order_db': 'Aggregate total quantity by product_id', 'inventory_db': 'Select product_id, product_name, stock_quantity'})"
    )
    join_keys: List[JoinKeyMapping] = Field(
        default_factory=list,
        description="List of join key mappings between databases"
    )
    join_type: str = Field(
        default="inner",
        description="Join strategy: 'inner', 'left', 'outer'"
    )
    post_join_operations: Dict[str, Any] = Field(
        default_factory=dict,
        description="Post-join operations in the backend (e.g. {'filter': 'high demand and low inventory', 'sort_by': 'demand DESC', 'limit': 50})"
    )
    reasoning: str = Field(
        ...,
        description="Explanation of why these databases and tables were chosen and how the data connects"
    )
