"""
QueryPilot — Agent Pipeline Orchestrator

Orchestrates the 5-agent pipeline:
  1. Schema Understanding → 2. SQL Generation → 3. Validation
  (with retry loop back to 2) → 4. Optimization → 5. Query Execution
  → 6. Explanation

Designed so real agent implementations can be dropped in by simply
replacing the stub agents.
"""

import json
import logging
from typing import List, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import AgentContext
from app.agents.schema_agent import SchemaAgent
from app.agents.generation_agent import GenerationAgent
from app.agents.validation_agent import ValidationAgent
from app.agents.optimization_agent import OptimizationAgent
from app.agents.explanation_agent import ExplanationAgent
from app.core.query_executor import query_executor
from app.core.viz_suggester import viz_suggester
from app.services.connection_manager import connection_manager
from app.services.schema_introspector import schema_introspector

logger = logging.getLogger(__name__)


# Ensure Agents package is accessible in sys.path
import os
import sys

_agents_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "Agents")
if _agents_dir not in sys.path:
    sys.path.insert(0, _agents_dir)

try:
    from graph.build_graph import build_graph
    from graph.state import AgentState
    _langgraph_pipeline = build_graph()
except Exception as e:
    logger.warning(f"LangGraph initialization deferred: {e}")
    _langgraph_pipeline = None


class AgentPipeline:
    """
    Orchestrates the 5-agent pipeline with validation retry loop
    powered by LangGraph.
    """

    def __init__(self):
        self.schema_agent = SchemaAgent()
        self.generation_agent = GenerationAgent()
        self.validation_agent = ValidationAgent()
        self.optimization_agent = OptimizationAgent()
        self.explanation_agent = ExplanationAgent()

    async def run(
        self,
        query: str,
        connection_id: str,
        db_type: str,
        conversation_history: List[Dict[str, str]] = None,
        schema_context: Dict = None,
        db: AsyncSession = None,
        on_status: callable = None,
    ) -> AgentContext:
        """
        Execute the full LangGraph agent pipeline.
        """
        context = AgentContext(
            natural_language_query=query,
            connection_id=connection_id,
            db_type=db_type,
            conversation_history=conversation_history or [],
        )

        try:
            if on_status:
                await on_status("Analyzing schema & synthesizing SQL with AI agents...")

            global _langgraph_pipeline
            if _langgraph_pipeline is None:
                _langgraph_pipeline = build_graph()

            initial_state: AgentState = {
                "user_id": "chat_user",
                "user_role": "admin",
                "question": query,
                "db_dialect": db_type or "sqlite",
                "connection_id": connection_id,
                "conversation_history": conversation_history or [],
                "sql_gen_attempts": 0,
            }

            # Invoke compiled LangGraph pipeline
            final_state = _langgraph_pipeline.invoke(initial_state)

            # Extract outputs from LangGraph state into AgentContext
            context.relevant_tables = list(final_state.get("relevant_schema", {}).keys())
            context.generated_sql = final_state.get("generated_sql") or ""
            context.optimized_sql = final_state.get("optimized_sql") or ""
            context.optimization_notes = final_state.get("optimization_notes") or []
            context.explanation = final_state.get("final_answer") or final_state.get("explanation") or ""
            context.follow_up_suggestions = final_state.get("suggested_followups") or []
            context.error = final_state.get("error")

            # Process query execution rows into columns & rows structure
            raw_results = final_state.get("query_result") or []
            if raw_results and isinstance(raw_results, list) and isinstance(raw_results[0], dict):
                cols = list(raw_results[0].keys())
                rows = raw_results
                context.query_results = {
                    "columns": cols,
                    "rows": rows,
                    "row_count": len(rows),
                }
            elif raw_results and isinstance(raw_results, list) and isinstance(raw_results[0], (list, tuple)):
                cols = [f"col_{i+1}" for i in range(len(raw_results[0]))]
                rows = [dict(zip(cols, r)) for r in raw_results]
                context.query_results = {
                    "columns": cols,
                    "rows": rows,
                    "row_count": len(rows),
                }
            else:
                context.query_results = {"columns": [], "rows": [], "row_count": 0}

            # Generate visualization suggestions if rows exist
            if context.query_results.get("columns") and context.query_results.get("rows"):
                try:
                    context.chart_suggestion = viz_suggester.suggest(
                        columns=context.query_results["columns"],
                        rows=context.query_results["rows"],
                        sql=context.optimized_sql or context.generated_sql,
                    )
                except Exception as viz_err:
                    logger.warning(f"Viz suggestion failed: {viz_err}")
                    context.chart_suggestion = {"chart_type": "table", "x_axis": None, "y_axis": None, "config": {}}

            return context

        except Exception as e:
            logger.error(f"Pipeline error: {e}", exc_info=True)
            context.error = f"Pipeline error: {str(e)}"
            return context


# Singleton instance
agent_pipeline = AgentPipeline()
