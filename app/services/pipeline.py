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


class AgentPipeline:
    """
    Orchestrates the 5-agent pipeline with validation retry loop.
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
        Execute the full agent pipeline.

        Args:
            query: Natural language question
            connection_id: Target database connection ID
            db_type: Database dialect (postgresql, mysql, etc.)
            conversation_history: Previous messages for context
            schema_context: Pre-loaded schema (optional)
            db: Async database session (for schema introspector)
            on_status: Callback for status updates (for WebSocket streaming)

        Returns:
            AgentContext with all pipeline outputs populated
        """
        context = AgentContext(
            natural_language_query=query,
            connection_id=connection_id,
            db_type=db_type,
            conversation_history=conversation_history or [],
        )

        if schema_context:
            context.schema_context = schema_context

        try:
            # ── Step 1: Schema Understanding ──────────────────
            if on_status:
                await on_status("Understanding database schema...")

            # Load schema if not pre-loaded
            if not context.schema_context and db:
                schema_data = await schema_introspector.get_schema_context(
                    connection_id, None, db
                )
                context.schema_context = schema_data

            result = await self.schema_agent.execute(context)
            if not result.success:
                context.error = f"Schema agent failed: {result.message}"
                return context

            logger.info(f"Schema agent: {result.message}")

            # ── Step 2–3: Generation → Validation Loop ────────
            for attempt in range(context.max_retries):
                if on_status:
                    await on_status(
                        f"Generating SQL...{' (retry ' + str(attempt) + ')' if attempt > 0 else ''}"
                    )

                gen_result = await self.generation_agent.execute(context)
                if not gen_result.success:
                    context.error = f"Generation agent failed: {gen_result.message}"
                    return context

                logger.info(f"Generation agent (attempt {attempt + 1}): {gen_result.message}")

                if on_status:
                    await on_status("Validating query...")

                val_result = await self.validation_agent.execute(context)
                if context.is_valid:
                    logger.info("Validation passed")
                    break

                context.validation_retries = attempt + 1
                logger.warning(
                    f"Validation failed (attempt {attempt + 1}): {context.validation_errors}"
                )

                if attempt == context.max_retries - 1:
                    context.error = (
                        f"Query validation failed after {context.max_retries} attempts: "
                        + "; ".join(context.validation_errors)
                    )
                    return context

            # ── Step 4: Optimization ──────────────────────────
            if on_status:
                await on_status("Optimizing query...")

            opt_result = await self.optimization_agent.execute(context)
            logger.info(f"Optimization agent: {opt_result.message}")

            # ── Step 5: Query Execution ───────────────────────
            if on_status:
                await on_status("Executing query...")

            engine = connection_manager.get_engine(connection_id)
            if engine is None:
                context.error = "Database engine not found. Connection may need to be re-established."
                return context

            sql_to_execute = context.optimized_sql or context.generated_sql

            try:
                results = await query_executor.execute(engine, sql_to_execute)
                context.query_results = results
                context.execution_time_ms = results.get("execution_time_ms", 0)
            except Exception as e:
                context.error = f"Query execution failed: {str(e)}"
                return context

            # ── Step 6: Explanation ────────────────────────────
            if on_status:
                await on_status("Generating explanation...")

            exp_result = await self.explanation_agent.execute(context)
            logger.info(f"Explanation agent: {exp_result.message}")

            # ── Step 7: Visualization Suggestion ──────────────
            if context.query_results.get("columns") and context.query_results.get("rows"):
                context.chart_suggestion = viz_suggester.suggest(
                    columns=context.query_results["columns"],
                    rows=context.query_results["rows"],
                    sql=sql_to_execute,
                )

            return context

        except Exception as e:
            logger.error(f"Pipeline error: {e}", exc_info=True)
            context.error = f"Pipeline error: {str(e)}"
            return context


# Singleton instance
agent_pipeline = AgentPipeline()
