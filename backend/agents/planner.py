"""Planner agent for creating essay outlines and argument maps."""

import json
from typing import Any

from .base import BaseAgent, AgentContext, AgentResult, AgentRole, ToolUse
from backend.core.providers import BaseProvider


PLANNER_SYSTEM_PROMPT = """You are an expert essay planner and argumentative strategist.

Your task is to create a clear, well-structured outline for an essay that:
1. Has a single, controlling thesis
2. Organizes arguments logically
3. Anticipates objections
4. Maps claims to required evidence

Guidelines:
- The thesis should be specific and defensible
- Each section should have a clear goal
- Include what evidence would be needed (without making it up)
- Anticipate at least one major objection
- Ensure logical flow between sections

Output Format (JSON):
{
  "thesis": "The controlling thesis statement",
  "sections": [
    {
      "heading": "Section title",
      "goal": "What this section achieves",
      "claims": ["Claim 1", "Claim 2"],
      "evidence_needed": "What kind of evidence would support this",
      "objection": "Potential counter-argument",
      "rebuttal": "How to address it"
    }
  ]
}

Be specific and concrete. Avoid generic structure."""


class PlannerAgent(BaseAgent):
    """
    Planner agent creates essay outlines and argument maps.

    This agent:
    - Generates thesis candidates
    - Creates section-by-section outlines
    - Maps claims to needed evidence
    - Anticipates objections
    """

    def __init__(self, provider: BaseProvider):
        super().__init__(
            role=AgentRole.PLANNER,
            provider=provider,
            system_prompt=PLANNER_SYSTEM_PROMPT,
            tools=[]
        )

    async def execute(self, context: AgentContext) -> AgentResult:
        """
        Execute planning task.

        Args:
            context: Agent context with task and constraints

        Returns:
            Agent result with outline
        """
        # Build prompt
        prompt = self._build_prompt(context)

        # Call LLM
        response = await self._call_llm(
            prompt=prompt,
            temperature=0.7,
            json_schema={"type": "object"}
        )

        # Parse response
        try:
            outline = json.loads(response)
            success = True
            error = None
        except json.JSONDecodeError as e:
            outline = {"raw_text": response}
            success = False
            error = f"Failed to parse JSON: {e}"

        return AgentResult(
            success=success,
            output=outline,
            error=error,
            metadata={
                "model": self.provider.config.model,
                "thesis": outline.get("thesis"),
                "section_count": len(outline.get("sections", []))
            }
        )

    def _build_prompt(self, context: AgentContext) -> str:
        """Build the prompt for planning."""
        prompt_parts = [
            f"Task: {context.task}",
            ""
        ]

        # Add constraints
        if context.constraints:
            prompt_parts.append("Constraints:")
            if "wordcount" in context.constraints:
                prompt_parts.append(f"- Target length: {context.constraints['wordcount']} words")
            if "tone" in context.constraints:
                prompt_parts.append(f"- Tone: {context.constraints['tone']}")
            if "audience" in context.constraints:
                prompt_parts.append(f"- Audience: {context.constraints['audience']}")
            prompt_parts.append("")

        # Add source information
        if context.allowed_sources:
            prompt_parts.append(f"Available sources: {len(context.allowed_sources)} documents")
            if context.strict_mode:
                prompt_parts.append("(Strict mode: only use these sources)")
            prompt_parts.append("")

        prompt_parts.append("Create a detailed outline following the JSON format specified.")

        return "\n".join(prompt_parts)

    def get_required_tools(self) -> list[str]:
        """Planner doesn't need tools."""
        return []

    def requires_sources(self) -> bool:
        """Planner should know about sources but doesn't require them."""
        return False
