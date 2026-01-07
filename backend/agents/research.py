"""Research agent for retrieving evidence from knowledge base."""

from typing import Any

from .base import BaseAgent, AgentContext, AgentResult, AgentRole
from backend.core.providers import BaseProvider


RESEARCH_SYSTEM_PROMPT = """You are a research assistant specialized in finding relevant evidence.

Your task is to:
1. Identify what evidence is needed for each claim
2. Search the knowledge base for relevant passages
3. Select the most appropriate excerpts
4. Format evidence with proper citations

You should:
- Match evidence precisely to claims
- Prefer direct quotes when available
- Include location information (page, section)
- Indicate strength of support (strong, moderate, weak)
- Note when evidence is insufficient

Output should be structured and traceable."""


class ResearchAgent(BaseAgent):
    """
    Research agent retrieves evidence from the knowledge base.

    This agent:
    - Searches for passages relevant to outline claims
    - Ranks and selects best evidence
    - Formats citations
    - Builds evidence tables
    """

    def __init__(self, provider: BaseProvider):
        super().__init__(
            role=AgentRole.RESEARCH,
            provider=provider,
            system_prompt=RESEARCH_SYSTEM_PROMPT,
            tools=["semantic_search", "get_passage", "get_citation"]
        )

    async def execute(self, context: AgentContext) -> AgentResult:
        """
        Execute research task.

        Args:
            context: Agent context with outline

        Returns:
            Agent result with evidence table
        """
        # Get outline from artifacts
        outline = context.artifacts.get("plan", {})

        if not outline:
            return AgentResult(
                success=False,
                output={},
                error="No outline found in artifacts"
            )

        # Build evidence table
        evidence_table = await self._build_evidence_table(
            outline=outline,
            allowed_sources=context.allowed_sources,
            context=context
        )

        return AgentResult(
            success=True,
            output=evidence_table,
            metadata={
                "model": self.provider.config.model,
                "claims_researched": len(evidence_table),
                "total_passages": sum(
                    len(claim.get("supporting_passages", []))
                    for claim in evidence_table.values()
                )
            }
        )

    async def _build_evidence_table(
        self,
        outline: dict,
        allowed_sources: list[str],
        context: AgentContext
    ) -> dict:
        """
        Build an evidence table mapping claims to supporting passages.

        Args:
            outline: Essay outline with claims
            allowed_sources: List of allowed source IDs
            context: Agent context

        Returns:
            Evidence table dictionary
        """
        evidence_table = {}

        # Extract all claims from outline
        sections = outline.get("sections", [])
        claim_id = 0

        for section in sections:
            claims = section.get("claims", [])

            for claim in claims:
                claim_id += 1
                claim_key = f"claim_{claim_id}"

                # For now, create placeholder structure
                # In a full implementation, this would:
                # 1. Use semantic_search tool to find relevant passages
                # 2. Rank by relevance
                # 3. Format with citations

                evidence_table[claim_key] = {
                    "claim_text": claim,
                    "section": section.get("heading"),
                    "supporting_passages": [
                        # This would be populated by actual semantic search
                        # Example structure:
                        # {
                        #     "doc_id": "uuid",
                        #     "passage_id": "uuid",
                        #     "quote": "exact text",
                        #     "location": "p. 42",
                        #     "relevance_score": 0.87
                        # }
                    ],
                    "evidence_strength": "to_be_determined",
                    "notes": "Evidence retrieval pending tool implementation"
                }

        return evidence_table

    def get_required_tools(self) -> list[str]:
        """Research agent needs search tools."""
        return ["semantic_search", "get_passage"]

    def requires_sources(self) -> bool:
        """Research agent requires sources."""
        return True
