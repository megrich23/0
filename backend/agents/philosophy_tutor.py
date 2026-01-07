"""Philosophy tutor agent for reading and absorbing philosophical texts."""

from typing import Any

from .base import BaseAgent, AgentContext, AgentResult, AgentRole
from backend.core.providers import BaseProvider


PHILOSOPHY_TUTOR_PROMPT = """You are an expert philosophy tutor and textual analyst.

Your task is to help absorb and understand philosophical texts through:

1. **Layered Summaries**: 3-sentence, 1-paragraph, and full summaries
2. **Argument Extraction**: Identify premises, conclusions, definitions
3. **Objection Generation**: Find tensions, weaknesses, counter-arguments
4. **Concept Mapping**: Extract key concepts and their relationships
5. **Note Creation**: Generate atomic Zettelkasten-style notes
6. **Recall Prompts**: Create flashcards for spaced repetition

Quality Standards:
- Precise philosophical terminology
- Clear argument reconstruction
- Charitable interpretation
- Identify both strengths and weaknesses
- Link to related concepts

Be thorough and pedagogically sound."""


class PhilosophyTutorAgent(BaseAgent):
    """
    Philosophy tutor agent helps absorb philosophical texts.

    This agent:
    - Creates layered summaries
    - Extracts arguments
    - Generates objections
    - Creates notes and flashcards
    - Updates concept graph
    """

    def __init__(self, provider: BaseProvider):
        super().__init__(
            role=AgentRole.TUTOR,
            provider=provider,
            system_prompt=PHILOSOPHY_TUTOR_PROMPT,
            tools=["get_document", "create_note", "update_concept_graph", "create_flashcard"]
        )

    async def execute(self, context: AgentContext) -> AgentResult:
        """
        Execute philosophy tutoring task.

        Args:
            context: Agent context with document to process

        Returns:
            Agent result with summaries, arguments, notes, etc.
        """
        # Determine specific sub-task
        task = context.task.lower()

        if "summarize" in task or "summary" in task:
            return await self._create_summaries(context)
        elif "argument" in task:
            return await self._extract_arguments(context)
        elif "objection" in task:
            return await self._generate_objections(context)
        elif "note" in task or "zettel" in task:
            return await self._create_notes(context)
        elif "flashcard" in task or "recall" in task:
            return await self._generate_flashcards(context)
        else:
            # Default: do comprehensive processing
            return await self._process_document(context)

    async def _create_summaries(self, context: AgentContext) -> AgentResult:
        """Create layered summaries of a document."""
        doc_text = self._get_document_text(context)

        prompt = f"""Create layered summaries of this philosophical text:

{doc_text[:5000]}  # Truncate for prompt size

Generate:
1. **Three-sentence summary**: Capture core thesis and main arguments
2. **One-paragraph summary**: Expand with key points and structure
3. **Section-by-section outline**: Break down the argument structure

Output as JSON:
{{
  "three_sentence": "...",
  "one_paragraph": "...",
  "outline": [
    {{"section": "Introduction", "summary": "..."}}
  ]
}}"""

        import json
        response = await self._call_llm(prompt=prompt, json_schema={"type": "object"})

        try:
            summaries = json.loads(response)
            success = True
            error = None
        except json.JSONDecodeError as e:
            summaries = {"raw_text": response}
            success = False
            error = f"Failed to parse JSON: {e}"

        return AgentResult(
            success=success,
            output=summaries,
            error=error
        )

    async def _extract_arguments(self, context: AgentContext) -> AgentResult:
        """Extract key arguments from document."""
        doc_text = self._get_document_text(context)

        prompt = f"""Extract the main argument(s) from this philosophical text:

{doc_text[:5000]}

For each argument, identify:
- **Conclusion**: What is being argued for
- **Premises**: What reasons support it
- **Definitions**: Key terms defined
- **Hidden assumptions**: Unstated premises

Output as JSON:
{{
  "arguments": [
    {{
      "conclusion": "...",
      "premises": ["P1", "P2"],
      "definitions": {{"term": "definition"}},
      "assumptions": ["assumption1"]
    }}
  ]
}}"""

        import json
        response = await self._call_llm(prompt=prompt, json_schema={"type": "object"})

        try:
            arguments = json.loads(response)
            success = True
            error = None
        except json.JSONDecodeError as e:
            arguments = {"raw_text": response}
            success = False
            error = f"Failed to parse JSON: {e}"

        return AgentResult(
            success=success,
            output=arguments,
            error=error
        )

    async def _generate_objections(self, context: AgentContext) -> AgentResult:
        """Generate objections and critiques."""
        doc_text = self._get_document_text(context)
        arguments = context.artifacts.get("extract_arguments", {})

        prompt = f"""Generate objections to the arguments in this text:

{doc_text[:3000]}

Previous analysis: {arguments}

Generate:
1. **Internal tensions**: Contradictions within the text
2. **External critiques**: Standard objections from other traditions
3. **Weak points**: Questionable premises or inferences

Output as JSON:
{{
  "internal_tensions": ["..."],
  "external_critiques": ["..."],
  "weak_points": ["..."]
}}"""

        import json
        response = await self._call_llm(prompt=prompt, json_schema={"type": "object"})

        try:
            objections = json.loads(response)
            success = True
            error = None
        except json.JSONDecodeError as e:
            objections = {"raw_text": response}
            success = False
            error = f"Failed to parse JSON: {e}"

        return AgentResult(
            success=success,
            output=objections,
            error=error
        )

    async def _create_notes(self, context: AgentContext) -> AgentResult:
        """Create Zettelkasten-style atomic notes."""
        # Placeholder implementation
        return AgentResult(
            success=True,
            output={"notes": [], "message": "Note creation pending full implementation"}
        )

    async def _generate_flashcards(self, context: AgentContext) -> AgentResult:
        """Generate recall prompts and flashcards."""
        # Placeholder implementation
        return AgentResult(
            success=True,
            output={"flashcards": [], "message": "Flashcard generation pending full implementation"}
        )

    async def _process_document(self, context: AgentContext) -> AgentResult:
        """Comprehensive document processing."""
        # Would orchestrate all sub-tasks
        return AgentResult(
            success=True,
            output={"message": "Comprehensive processing pending full implementation"}
        )

    def _get_document_text(self, context: AgentContext) -> str:
        """Get document text from context."""
        # In full implementation, would fetch from database
        # For now, return placeholder
        return context.artifacts.get("document_text", "")

    def get_required_tools(self) -> list[str]:
        """Tutor needs document access and note creation tools."""
        return ["get_document", "create_note"]

    def requires_sources(self) -> bool:
        """Tutor requires source documents."""
        return True
