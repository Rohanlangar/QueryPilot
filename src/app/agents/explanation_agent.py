"""
QueryPilot — Explanation Agent (Stub)

Agent 5 in the pipeline. Translates query results into plain English:
  - Identifies key insights
  - Flags anomalies
  - Explains WHY the query answered the question
  - Suggests follow-up questions

TODO: Implement with LLM for natural language explanation generation.
"""

from app.agents.base import BaseAgent, AgentContext, AgentResult


class ExplanationAgent(BaseAgent):
    """
    Explanation Agent — translates results into plain English insights.

    Input (from context):
      - natural_language_query
      - optimized_sql (or generated_sql)
      - query_results: {columns, rows, row_count, ...}

    Output (to context):
      - explanation: plain English summary of results
      - key_insights: list of notable observations
      - follow_up_suggestions: 2-3 related questions
      - confidence_score: overall confidence in the answer
      - confidence_reason: why this confidence level
    """

    @property
    def name(self) -> str:
        return "Explanation Agent"

    async def execute(self, context: AgentContext) -> AgentResult:
        # STUB: In production, this would:
        # 1. Analyze the result set
        # 2. Generate a natural language explanation
        # 3. Identify insights and anomalies
        # 4. Suggest follow-up questions

        row_count = context.query_results.get("row_count", 0)
        context.explanation = (
            f"[STUB] Query returned {row_count} rows. "
            f"Explanation agent not yet implemented."
        )
        context.key_insights = []
        context.follow_up_suggestions = [
            "Try filtering by a specific date range",
            "Break this down by category",
            "Compare with the previous period",
        ]
        context.confidence_score = 0.5
        context.confidence_reason = "Stub agent — no real confidence assessment"

        return AgentResult(
            success=True,
            context=context,
            message="[STUB] Explanation agent — placeholder response",
        )

    async def validate_input(self, context: AgentContext):
        if not context.query_results:
            return "No query results to explain"
        return None
