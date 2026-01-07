"""Fact checker agent for verifying citations and claims."""

from typing import Any

from .base import BaseAgent, AgentContext, AgentResult, AgentRole
from backend.core.providers import BaseProvider


FACT_CHECKER_PROMPT = """You are a meticulous fact-checker and provenance auditor.

Your task is to verify that every claim in an essay is properly supported:

1. **Citation Coverage**: What % of paragraphs have citations?
2. **Quote Accuracy**: Are quotes exact and properly attributed?
3. **Claim Support**: Is each claim backed by evidence or labeled speculative?
4. **Source Validity**: Are all sources from the allowed list?
5. **Misattribution**: Are any claims attributed to wrong sources?

Output Format (JSON):
{
  "citation_coverage": 0.0-1.0,
  "paragraphs_checked": N,
  "paragraphs_with_citations": N,
  "unsupported_claims": [
    {
      "paragraph": N,
      "claim": "The claim text",
      "issue": "Why it's unsupported"
    }
  ],
  "inaccurate_quotes": [
    {
      "claimed_quote": "What the essay says",
      "actual_quote": "What the source says",
      "location": "Where in essay"
    }
  ],
  "speculative_claims_unlabeled": [
    {
      "paragraph": N,
      "claim": "Text",
      "note": "Should be labeled speculative"
    }
  ],
  "overall_provenance_score": 0.0-1.0
}

Be thorough and precise."""


class FactCheckerAgent(BaseAgent):
    """
    Fact checker agent verifies citations and claim support.

    This agent:
    - Checks citation coverage
    - Verifies quote accuracy
    - Flags unsupported claims
    - Ensures provenance
    """

    def __init__(self, provider: BaseProvider):
        super().__init__(
            role=AgentRole.FACT_CHECKER,
            provider=provider,
            system_prompt=FACT_CHECKER_PROMPT,
            tools=["verify_quote", "check_citation", "get_passage"]
        )

    async def execute(self, context: AgentContext) -> AgentResult:
        """
        Execute fact-checking task.

        Args:
            context: Agent context with draft and evidence

        Returns:
            Agent result with fact-check report
        """
        # Get draft from artifacts
        draft_data = context.artifacts.get("revise", context.artifacts.get("draft", {}))
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
        import json
        response = await self._call_llm(
            prompt=prompt,
            temperature=0.3,  # Low temp for precision
            json_schema={"type": "object"}
        )

        # Parse response
        try:
            report = json.loads(response)
            success = True
            error = None
        except json.JSONDecodeError as e:
            report = {"raw_text": response}
            success = False
            error = f"Failed to parse JSON: {e}"

        return AgentResult(
            success=success,
            output=report,
            error=error,
            metadata={
                "model": self.provider.config.model,
                "citation_coverage": report.get("citation_coverage", 0.0),
                "provenance_score": report.get("overall_provenance_score", 0.0)
            }
        )

    def _build_prompt(self, context: AgentContext, draft: str) -> str:
        """Build fact-checking prompt."""
        prompt_parts = [
            f"Task: {context.task}",
            "",
            "## Essay Draft",
            draft,
            "",
            "## Instructions",
            "Perform a thorough fact-check and provenance audit.",
            "Check every paragraph for proper citation or speculation labels.",
            "Verify that claims match evidence from allowed sources.",
            "Output detailed report in JSON format."
        ]

        # Add minimum citation coverage requirement
        min_coverage = context.constraints.get("min_citation_coverage", 0.7)
        prompt_parts.append(f"\nMinimum required citation coverage: {min_coverage:.0%}")

        return "\n".join(prompt_parts)

    def get_required_tools(self) -> list[str]:
        """Fact checker needs verification tools."""
        return ["verify_quote", "check_citation"]

    def requires_sources(self) -> bool:
        """Fact checker requires sources to verify against."""
        return True
