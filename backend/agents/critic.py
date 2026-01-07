"""Critic agents for evaluating and improving essay drafts."""

from typing import Any
import json

from .base import BaseAgent, AgentContext, AgentResult, AgentRole
from backend.core.providers import BaseProvider


STRUCTURAL_CRITIC_PROMPT = """You are an expert essay critic specializing in STRUCTURAL analysis.

Your task is to identify structural weaknesses in essays:

1. **Thesis Clarity**: Is there a clear, controlling idea?
2. **Logical Flow**: Do arguments build logically?
3. **Evidence Strength**: Are claims well-supported?
4. **Warrant Quality**: Are connections between evidence and claims clear?
5. **Objection Handling**: Are counterarguments addressed?
6. **Section Coherence**: Does each section achieve its goal?

Output Format (JSON):
{
  "thesis_score": 1-5,
  "flow_score": 1-5,
  "evidence_score": 1-5,
  "structural_issues": [
    "Specific issue description with location"
  ],
  "revision_plan": [
    {
      "section": "Which section",
      "issue": "What's wrong",
      "suggestion": "How to fix"
    }
  ]
}

Be specific and constructive. Point to exact paragraphs or sections."""


STYLE_CRITIC_PROMPT = """You are an expert essay critic specializing in STYLE and VOICE.

Your task is to identify style weaknesses:

1. **Voice Consistency**: Is tone consistent throughout?
2. **Sentence Variety**: Is there varied rhythm and structure?
3. **Specificity**: Are there concrete details and examples?
4. **Clarity**: Is prose clear and direct?
5. **Clichés**: Are there filler phrases or generic language?
6. **Academic Precision**: Is language appropriately formal/informal?

Output Format (JSON):
{
  "voice_score": 1-5,
  "clarity_score": 1-5,
  "specificity_score": 1-5,
  "style_issues": [
    "Specific style problem with example"
  ],
  "forbidden_phrases_found": [
    "List of clichés/filler found"
  ],
  "revision_suggestions": [
    {
      "location": "Paragraph or section",
      "original": "Problematic text",
      "suggested": "Improved version"
    }
  ]
}

Be specific. Quote exact phrases that need revision."""


class CriticAgent(BaseAgent):
    """Base critic agent."""

    async def execute(self, context: AgentContext) -> AgentResult:
        """
        Execute critique task.

        Args:
            context: Agent context with draft to critique

        Returns:
            Agent result with critique
        """
        # Get draft from artifacts
        draft_data = context.artifacts.get("draft", {})
        draft_text = draft_data.get("draft", "")

        if not draft_text:
            return AgentResult(
                success=False,
                output={},
                error="No draft found in artifacts"
            )

        # Build prompt
        prompt = self._build_prompt(context, draft_text)

        # Call LLM
        response = await self._call_llm(
            prompt=prompt,
            temperature=0.5,  # Lower temp for more consistent critique
            json_schema={"type": "object"}
        )

        # Parse response
        try:
            critique = json.loads(response)
            success = True
            error = None
        except json.JSONDecodeError as e:
            critique = {"raw_text": response}
            success = False
            error = f"Failed to parse JSON: {e}"

        return AgentResult(
            success=success,
            output=critique,
            error=error,
            metadata={
                "model": self.provider.config.model,
                "critique_type": self.role.value
            }
        )

    def _build_prompt(self, context: AgentContext, draft: str) -> str:
        """Build critique prompt."""
        prompt_parts = [
            f"Task: {context.task}",
            "",
            "## Essay Draft",
            draft,
            "",
            "## Instructions",
            "Analyze this draft and provide a detailed critique following the JSON format.",
            "Be specific and constructive. Quote exact text when identifying issues."
        ]

        return "\n".join(prompt_parts)


class StructuralCriticAgent(CriticAgent):
    """Critic focused on structural quality."""

    def __init__(self, provider: BaseProvider):
        super().__init__(
            role=AgentRole.CRITIC,
            provider=provider,
            system_prompt=STRUCTURAL_CRITIC_PROMPT,
            tools=[]
        )


class StyleCriticAgent(CriticAgent):
    """Critic focused on style and voice."""

    def __init__(self, provider: BaseProvider):
        super().__init__(
            role=AgentRole.CRITIC,
            provider=provider,
            system_prompt=STYLE_CRITIC_PROMPT,
            tools=[]
        )

    def _build_prompt(self, context: AgentContext, draft: str) -> str:
        """Build style critique prompt with forbidden phrases."""
        base_prompt = super()._build_prompt(context, draft)

        # Add forbidden phrases list if available
        forbidden = context.constraints.get("forbidden_phrases", [
            "In today's world",
            "Throughout history",
            "It is important to note",
            "In conclusion",
            "Since the dawn of time",
            "It goes without saying"
        ])

        additional = [
            "",
            "## Forbidden Phrases to Check",
            *[f"- {phrase}" for phrase in forbidden]
        ]

        return base_prompt + "\n".join(additional)
