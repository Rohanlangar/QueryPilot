"""
QueryPilot — Base Agent Interface

Abstract base class that all 5 pipeline agents must implement.
Provides a consistent contract for the pipeline orchestrator.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class AgentContext:
    """
    Context object passed through the agent pipeline.
    Each agent reads what it needs and adds its output.
    """

    # ── Input (from user) ─────────────────────────────────────
    natural_language_query: str = ""
    conversation_history: List[Dict[str, str]] = field(default_factory=list)
    connection_id: str = ""
    db_type: str = ""  # postgresql, mysql, mssql, oracle

    # ── Schema Agent Output ───────────────────────────────────
    schema_context: Dict = field(default_factory=dict)
    relevant_tables: List[str] = field(default_factory=list)

    # ── SQL Generation Agent Output ───────────────────────────
    generated_sql: str = ""
    generation_confidence: float = 0.0

    # ── Validation Agent Output ───────────────────────────────
    is_valid: bool = False
    validation_errors: List[str] = field(default_factory=list)
    validation_retries: int = 0
    max_retries: int = 3

    # ── Optimization Agent Output ─────────────────────────────
    optimized_sql: str = ""
    optimization_notes: List[str] = field(default_factory=list)
    estimated_cost: Optional[float] = None

    # ── Query Results ─────────────────────────────────────────
    query_results: Dict = field(default_factory=dict)  # {columns, rows, row_count, ...}
    execution_time_ms: float = 0.0

    # ── Explanation Agent Output ──────────────────────────────
    explanation: str = ""
    key_insights: List[str] = field(default_factory=list)
    follow_up_suggestions: List[str] = field(default_factory=list)
    confidence_score: float = 0.0
    confidence_reason: str = ""

    # ── Visualization ─────────────────────────────────────────
    chart_suggestion: Dict = field(default_factory=dict)

    # ── Error State ───────────────────────────────────────────
    error: Optional[str] = None


@dataclass
class AgentResult:
    """Result returned by each agent."""
    success: bool
    context: AgentContext
    message: str = ""


class BaseAgent(ABC):
    """
    Abstract base class for pipeline agents.

    Each agent:
      1. Receives an AgentContext
      2. Reads the fields it needs
      3. Performs its task
      4. Writes its outputs to the context
      5. Returns an AgentResult
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable agent name."""
        pass

    @abstractmethod
    async def execute(self, context: AgentContext) -> AgentResult:
        """
        Execute this agent's task.

        Args:
            context: The shared pipeline context

        Returns:
            AgentResult with updated context
        """
        pass

    async def validate_input(self, context: AgentContext) -> Optional[str]:
        """
        Validate that the context has the required inputs for this agent.
        Returns an error message if validation fails, None if valid.
        """
        return None
