"""
QueryPilot — Schema Understanding Agent (Stub)

Agent 1 in the pipeline. Identifies which tables are relevant to the
user's question and builds a compressed schema context.

TODO: Implement with embedding-based similarity search over
table/column descriptions for large schemas.
"""

from app.agents.base import BaseAgent, AgentContext, AgentResult


class SchemaAgent(BaseAgent):
    """
    Schema Understanding Agent — identifies relevant tables and builds
    schema context for downstream SQL generation.

    Input (from context):
      - natural_language_query
      - connection_id

    Output (to context):
      - schema_context: dict of relevant table/column metadata
      - relevant_tables: list of table names
    """

    @property
    def name(self) -> str:
        return "Schema Understanding Agent"

    async def execute(self, context: AgentContext) -> AgentResult:
        # STUB: In production, this would:
        # 1. Load schema metadata from DB
        # 2. Use embeddings or keyword matching to find relevant tables
        # 3. Build compressed schema context
        return AgentResult(
            success=True,
            context=context,
            message="[STUB] Schema agent — pass-through, no table selection performed",
        )

    async def validate_input(self, context: AgentContext):
        if not context.natural_language_query:
            return "No natural language query provided"
        if not context.connection_id:
            return "No connection ID provided"
        return None
