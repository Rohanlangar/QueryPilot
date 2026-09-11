"""
QueryPilot — SQL Generation Agent (Stub)

Agent 2 in the pipeline. Takes natural-language + schema context and
generates dialect-aware SQL.

TODO: Implement with LLM (online: API, offline: SQLCoder).
Must handle complex patterns: JOINs, CTEs, window functions, aggregations.
"""

from app.agents.base import BaseAgent, AgentContext, AgentResult


class GenerationAgent(BaseAgent):
    """
    SQL Generation Agent — generates syntactically valid, dialect-aware SQL.

    Input (from context):
      - natural_language_query
      - conversation_history (for follow-ups)
      - schema_context (from Schema Agent)
      - db_type (postgresql, mysql, mssql, oracle)

    Output (to context):
      - generated_sql: the SQL query string
      - generation_confidence: 0.0-1.0
    """

    @property
    def name(self) -> str:
        return "SQL Generation Agent"

    async def execute(self, context: AgentContext) -> AgentResult:
        # STUB: In production, this would:
        # 1. Build a prompt with schema context + conversation history
        # 2. Call the LLM (online or offline)
        # 3. Parse the SQL from the response
        # 4. Ensure dialect compatibility

        # Return a placeholder
        context.generated_sql = "-- STUB: No SQL generated (agent not implemented)"
        context.generation_confidence = 0.0

        return AgentResult(
            success=True,
            context=context,
            message="[STUB] Generation agent — no LLM connected",
        )

    async def validate_input(self, context: AgentContext):
        if not context.natural_language_query:
            return "No natural language query provided"
        return None
