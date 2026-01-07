"""
Multi-agent system for essay writing, philosophy reading, and culture monitoring.

Each agent is specialized for a specific task and uses tools to accomplish its goals.
"""

from .base import BaseAgent, AgentContext, AgentResult, ToolUse
from .planner import PlannerAgent
from .writer import WriterAgent
from .critic import CriticAgent, StructuralCriticAgent, StyleCriticAgent
from .fact_checker import FactCheckerAgent
from .curator import CuratorAgent
from .philosophy_tutor import PhilosophyTutorAgent
from .research import ResearchAgent

__all__ = [
    "BaseAgent",
    "AgentContext",
    "AgentResult",
    "ToolUse",
    "PlannerAgent",
    "WriterAgent",
    "CriticAgent",
    "StructuralCriticAgent",
    "StyleCriticAgent",
    "FactCheckerAgent",
    "CuratorAgent",
    "PhilosophyTutorAgent",
    "ResearchAgent",
]
