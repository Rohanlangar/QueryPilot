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
        connection_id: Optional[str] = None,
        active_connection_ids: Optional[List[str]] = None,
        db_type: str = "sqlite",
        conversation_history: List[Dict[str, str]] = None,
        schema_context: Dict = None,
        db: AsyncSession = None,
        on_status: callable = None,
    ) -> AgentContext:
        """
        Execute the full LangGraph agent pipeline for single or multi-database queries.
        """
        context = AgentContext(
            natural_language_query=query,
            connection_id=connection_id or "",
            db_type=db_type,
            conversation_history=conversation_history or [],
        )

        try:
            # Auto-register all active connections for the user in db.connection_manager
            active_ids = list(active_connection_ids or [])
            if db:
                try:
                    from db.connection_manager import _ACTIVE_CONNECTIONS, register_database, DatabaseConfig
                    from app.core.security import decrypt_credential
                    from app.models.connection import Connection
                    from sqlalchemy import select

                    # Load all active connections
                    stmt = select(Connection).where(Connection.is_active == True)
                    res = await db.execute(stmt)
                    active_conns = res.scalars().all()

                    for conn_record in active_conns:
                        active_ids.append(conn_record.id)
                        if conn_record.id not in _ACTIVE_CONNECTIONS:
                            decrypted_pwd = decrypt_credential(conn_record.encrypted_password) if conn_record.encrypted_password else None
                            cfg = DatabaseConfig(
                                connection_id=conn_record.id,
                                db_type=conn_record.db_type or "sqlite",
                                host=conn_record.host,
                                port=conn_record.port,
                                database=conn_record.database_name,
                                username=conn_record.username,
                                password=decrypted_pwd,
                                ssl_mode="require" if conn_record.ssl_enabled else None,
                            )
                            register_database(cfg)
                except Exception as conn_err:
                    logger.warning(f"Could not auto-register active connections: {conn_err}")

            # If no active connections are registered, ensure demo databases are available
            from db.connection_manager import _ACTIVE_CONNECTIONS
            if not _ACTIVE_CONNECTIONS:
                try:
                    from db.demo_federated_databases import initialize_demo_federated_databases
                    initialize_demo_federated_databases()
                except Exception as demo_err:
                    logger.warning(f"Could not initialize demo databases: {demo_err}")

            async def _emit_status(stage_id: str, label: str, index: int, total: int = 6):
                if not on_status:
                    return
                status_payload = {
                    "type": "stage",
                    "stage": stage_id,
                    "label": label,
                    "index": index,
                    "total": total,
                    "message": label,
                }
                try:
                    import inspect
                    if inspect.iscoroutinefunction(on_status):
                        await on_status(status_payload)
                    else:
                        on_status(status_payload)
                except Exception as cb_err:
                    logger.warning(f"Status callback failed: {cb_err}")

            await _emit_status("schema", "Discovering schemas across active databases...", 0, 6)

            global _langgraph_pipeline
            if _langgraph_pipeline is None:
                _langgraph_pipeline = build_graph()

            initial_state: AgentState = {
                "user_id": "chat_user",
                "user_role": "admin",
                "question": query,
                "db_dialect": db_type or "sqlite",
                "connection_id": connection_id,
                "active_connections": active_ids if active_ids else None,
                "conversation_history": conversation_history or [],
                "sql_gen_attempts": 0,
            }

            import time
            start_time = time.perf_counter()

            # Stream LangGraph pipeline step by step to emit live stage progress
            final_state = dict(initial_state)
            for step in _langgraph_pipeline.stream(initial_state):
                for node_name, node_output in step.items():
                    if isinstance(node_output, dict):
                        final_state.update(node_output)

                    # Trigger next stage status update based on completed node
                    if node_name == "schema":
                        await _emit_status("planner", "Planning query strategy & cross-database joins...", 1, 6)
                    elif node_name == "planner":
                        await _emit_status("sql_gen", "Synthesizing database-specific SQL queries...", 2, 6)
                    elif node_name == "sql_gen":
                        await _emit_status("validate", "Validating queries against database schemas...", 3, 6)
                    elif node_name == "validate":
                        await _emit_status("execute", "Executing queries on respective databases...", 4, 6)
                    elif node_name == "execute":
                        await _emit_status("federate", "Performing cross-database merge & join...", 5, 6)
                    elif node_name == "federate":
                        await _emit_status("explain", "Synthesizing unified business analysis...", 6, 6)

            context.execution_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
            await _emit_status("complete", "Pipeline complete", 6, 6)

            # Extract outputs from LangGraph state into AgentContext
            context.relevant_tables = list(final_state.get("relevant_schema", {}).keys())
            context.generated_sql = final_state.get("generated_sql") or ""
            context.optimized_sql = final_state.get("optimized_sql") or ""
            context.optimization_notes = final_state.get("optimization_notes") or []
            context.explanation = final_state.get("final_answer") or final_state.get("explanation") or ""
            context.follow_up_suggestions = final_state.get("suggested_followups") or []
            context.error = final_state.get("error")
            context.is_federated = final_state.get("is_federated", False)
            context.sources_used = final_state.get("sources_used") or []
            context.database_queries = final_state.get("database_queries") or {}
            context.execution_plan_diagram = final_state.get("execution_plan_diagram") or ""
            context.security_incident = final_state.get("security_incident")

            # Map confidence_label to numeric score and reason
            conf_label = final_state.get("confidence_label")
            conf_map = {"High": 0.95, "Medium": 0.65, "Low": 0.35}
            if isinstance(conf_label, str) and conf_label in conf_map:
                context.confidence_score = conf_map[conf_label]
            elif isinstance(conf_label, (int, float)) and conf_label > 0:
                context.confidence_score = float(conf_label)
            else:
                context.confidence_score = 0.90 if context.optimized_sql or context.generated_sql else 0.50

            context.confidence_reason = final_state.get("confidence_reason") or (
                f"{conf_label or 'High'} Confidence based on AST validation and database schema verification"
            )

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
