"""Curator agent for culture watch digests."""

from typing import Any

from .base import BaseAgent, AgentContext, AgentResult, AgentRole
from backend.core.providers import BaseProvider


CURATOR_PROMPT = """You are a cultural curator and digest writer.

Your task is to synthesize cultural scene activity into readable digests:

1. **Clustering**: Group related items into storylines
2. **Theme Extraction**: Identify recurring motifs
3. **Entity Tracking**: Note who's mentioned where
4. **Trend Analysis**: What's changing over time
5. **Highlight Selection**: Pick most notable items

Quality Standards:
- Deduplication (don't repeat same item)
- Novel > repetitive
- Specific names, venues, publications
- Clear storylines, not random collections
- Digestible summaries

Output Format (JSON):
{
  "period": "Date range",
  "summary": "Overall summary paragraph",
  "clusters": [
    {
      "title": "Storyline title",
      "description": "What's happening",
      "items": ["doc_id_1", "doc_id_2"],
      "keywords": ["keyword1", "keyword2"]
    }
  ],
  "highlights": [
    {
      "doc_id": "uuid",
      "title": "Item title",
      "reason": "Why this is notable",
      "excerpt": "Brief excerpt"
    }
  ],
  "emerging_themes": [
    "Theme description"
  ],
  "notable_entities": {
    "people": ["Name1", "Name2"],
    "venues": ["Venue1"],
    "publications": ["Pub1"]
  }
}"""


class CuratorAgent(BaseAgent):
    """
    Curator agent creates culture watch digests.

    This agent:
    - Clusters related items
    - Extracts themes and entities
    - Highlights notable content
    - Tracks trends
    """

    def __init__(self, provider: BaseProvider):
        super().__init__(
            role=AgentRole.CURATOR,
            provider=provider,
            system_prompt=CURATOR_PROMPT,
            tools=["cluster_documents", "extract_entities", "deduplicate"]
        )

    async def execute(self, context: AgentContext) -> AgentResult:
        """
        Execute curation task.

        Args:
            context: Agent context with documents to curate

        Returns:
            Agent result with digest
        """
        # Get documents from artifacts
        documents = context.artifacts.get("documents", [])

        if not documents:
            return AgentResult(
                success=False,
                output={},
                error="No documents found in artifacts"
            )

        # Build prompt
        prompt = self._build_prompt(context, documents)

        # Call LLM
        import json
        response = await self._call_llm(
            prompt=prompt,
            temperature=0.6,
            json_schema={"type": "object"}
        )

        # Parse response
        try:
            digest = json.loads(response)
            success = True
            error = None
        except json.JSONDecodeError as e:
            digest = {"raw_text": response}
            success = False
            error = f"Failed to parse JSON: {e}"

        return AgentResult(
            success=success,
            output=digest,
            error=error,
            metadata={
                "model": self.provider.config.model,
                "documents_processed": len(documents),
                "clusters_created": len(digest.get("clusters", [])),
                "highlights_selected": len(digest.get("highlights", []))
            }
        )

    def _build_prompt(self, context: AgentContext, documents: list) -> str:
        """Build curation prompt."""
        prompt_parts = [
            f"Task: {context.task}",
            "",
            f"## Documents to Curate ({len(documents)} items)",
            ""
        ]

        # Add document summaries
        for i, doc in enumerate(documents[:50], 1):  # Limit to 50 for prompt size
            title = doc.get("title", "Untitled")
            author = doc.get("author", "Unknown")
            date = doc.get("date", "")
            excerpt = doc.get("excerpt", "")[:200]

            prompt_parts.append(f"{i}. **{title}** by {author} ({date})")
            prompt_parts.append(f"   {excerpt}...")
            prompt_parts.append("")

        # Add instructions
        prompt_parts.extend([
            "## Instructions",
            "Create a comprehensive digest following the JSON format.",
            "Focus on:",
            "- Grouping related items into coherent storylines",
            "- Identifying recurring themes and names",
            "- Highlighting most notable/novel content",
            "- Avoiding duplication",
            "",
            "Generate the digest now:"
        ])

        return "\n".join(prompt_parts)

    def get_required_tools(self) -> list[str]:
        """Curator needs clustering tools."""
        return ["cluster_documents", "extract_entities"]
