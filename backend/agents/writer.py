"""Writer agent for drafting essay sections."""

from typing import Any

from .base import BaseAgent, AgentContext, AgentResult, AgentRole
from backend.core.providers import BaseProvider


WRITER_SYSTEM_PROMPT = """You are an expert essay writer focused on clarity, specificity, and evidence-based argumentation.

Writing Principles:
1. **Argumentative Spine**: Every paragraph advances the thesis
2. **Concrete Anchors**: Use specific names, dates, passages, examples
3. **Evidence Integration**: Support claims with citations
4. **Voice Consistency**: Maintain consistent tone and style
5. **Varied Rhythm**: Mix sentence lengths (15-35 words, avg ~22)

Quality Standards:
- NO filler phrases ("In today's world", "Throughout history", "It is important to note")
- NO unsupported claims (everything must cite a source or be labeled speculative)
- At least ONE concrete example per 500-700 words
- At least ONE counterargument addressed per essay
- Verbatim quotes only when highly relevant (with citations)

Citation Format:
- Inline: (Author, Title, p. X)
- Always include page/location when available
- Use "speculative" label if no source supports the claim

Your task is to draft sections following the provided outline and using only the provided evidence."""


class WriterAgent(BaseAgent):
    """
    Writer agent drafts essay text.

    This agent:
    - Writes section-by-section based on outline
    - Integrates evidence with citations
    - Maintains voice and style consistency
    - Ensures concrete, specific writing
    """

    def __init__(self, provider: BaseProvider):
        super().__init__(
            role=AgentRole.WRITER,
            provider=provider,
            system_prompt=WRITER_SYSTEM_PROMPT,
            tools=["retrieve_evidence", "get_citation"]
        )

    async def execute(self, context: AgentContext) -> AgentResult:
        """
        Execute writing task.

        Args:
            context: Agent context with outline and evidence

        Returns:
            Agent result with draft
        """
        # Get outline from artifacts
        outline = context.artifacts.get("plan", {})
        evidence_table = context.artifacts.get("research", {})

        # Build prompt
        prompt = self._build_prompt(context, outline, evidence_table)

        # Call LLM (use higher max_tokens for long-form writing)
        draft = await self._call_llm(
            prompt=prompt,
            temperature=0.7,
            max_tokens=context.constraints.get("wordcount", 2000) * 2  # ~2 tokens per word
        )

        # Extract metadata
        word_count = len(draft.split())
        paragraph_count = len([p for p in draft.split("\n\n") if p.strip()])

        return AgentResult(
            success=True,
            output={
                "draft": draft,
                "word_count": word_count,
                "paragraph_count": paragraph_count
            },
            metadata={
                "model": self.provider.config.model,
                "word_count": word_count,
                "paragraph_count": paragraph_count
            }
        )

    def _build_prompt(
        self,
        context: AgentContext,
        outline: dict,
        evidence_table: dict
    ) -> str:
        """Build the writing prompt."""
        prompt_parts = [
            f"Task: {context.task}",
            "",
            "## Outline",
            f"Thesis: {outline.get('thesis', 'N/A')}",
            ""
        ]

        # Add sections from outline
        for i, section in enumerate(outline.get("sections", []), 1):
            prompt_parts.append(f"### Section {i}: {section.get('heading')}")
            prompt_parts.append(f"Goal: {section.get('goal')}")
            prompt_parts.append(f"Claims: {', '.join(section.get('claims', []))}")
            prompt_parts.append("")

        # Add available evidence
        if evidence_table:
            prompt_parts.append("## Available Evidence")
            for claim_id, claim_data in evidence_table.items():
                claim_text = claim_data.get("claim_text", "")
                passages = claim_data.get("supporting_passages", [])

                prompt_parts.append(f"**Claim**: {claim_text}")
                for passage in passages:
                    quote = passage.get("quote", "")
                    location = passage.get("location", "")
                    prompt_parts.append(f"  - \"{quote}\" ({location})")
                prompt_parts.append("")

        # Add constraints
        if context.constraints.get("wordcount"):
            prompt_parts.append(f"Target length: {context.constraints['wordcount']} words")

        if context.constraints.get("tone"):
            prompt_parts.append(f"Tone: {context.constraints['tone']}")

        # Add instructions
        prompt_parts.extend([
            "",
            "## Instructions",
            "1. Write the full essay following the outline",
            "2. Use ONLY the provided evidence",
            "3. Include inline citations for all claims",
            "4. Label any speculative claims as [SPECULATIVE]",
            "5. Vary sentence length and structure",
            "6. Avoid forbidden filler phrases",
            "7. Include at least one counterargument and rebuttal",
            "",
            "Write the complete essay now:"
        ])

        return "\n".join(prompt_parts)

    def get_required_tools(self) -> list[str]:
        """Writer needs evidence retrieval tools."""
        return ["retrieve_evidence"]

    def requires_sources(self) -> bool:
        """Writer requires sources in strict mode."""
        return True
