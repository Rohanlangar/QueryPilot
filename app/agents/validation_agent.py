"""
QueryPilot — Validation Agent (Stub)

Agent 3 in the pipeline. Validates generated SQL for:
  (a) Syntax correctness
  (b) Schema compliance (all tables/columns exist)
  (c) RBAC policy enforcement

If validation fails, sends query back to Agent 2 for correction.

TODO: Implement SQL parsing (sqlparse), schema cross-reference, RBAC checks.
"""

from app.agents.base import BaseAgent, AgentContext, AgentResult


class ValidationAgent(BaseAgent):
    """
    Validation Agent — validates SQL before it touches the database.

    Input (from context):
      - generated_sql
      - schema_context
      - relevant_tables
      - connection_id

    Output (to context):
      - is_valid: bool
      - validation_errors: list of error messages
    """

    @property
    def name(self) -> str:
        return "Validation Agent"

    async def execute(self, context: AgentContext) -> AgentResult:
        # STUB: In production, this would:
        # 1. Parse SQL with sqlparse
        # 2. Extract referenced tables and columns
        # 3. Cross-reference against schema_context
        # 4. Check RBAC policies
        # 5. Return validation result

        context.is_valid = True  # Stub: assume valid
        context.validation_errors = []

        return AgentResult(
            success=True,
            context=context,
            message="[STUB] Validation agent — all queries pass (not implemented)",
        )

    async def validate_input(self, context: AgentContext):
        if not context.generated_sql:
            return "No SQL to validate"
        return None
