"""Brainstormer agent for creative ideation and synthesis."""

import json
from typing import Optional
from datetime import datetime

from .base import (
    BaseAgent,
    AgentContext,
    AgentResult,
    AgentRole,
    ToolUse,
)
from backend.core.providers import BaseProvider


BRAINSTORMER_SYSTEM_PROMPT = """You are a creative brainstorming agent skilled at generating novel ideas and finding unexpected connections.

Your role is to:
1. Pull relevant knowledge from philosophy, culture, and stored notes
2. Synthesize new ideas by combining concepts in creative ways
3. Challenge assumptions and explore alternative perspectives
4. Find analogies and connections across different domains
5. Facilitate multi-perspective discussions by consulting other agents

When brainstorming:
- Start broad, then focus on the most promising directions
- Consider both conventional and unconventional approaches
- Ground ideas in evidence and sources where possible
- Mark speculative ideas clearly
- Build on existing knowledge rather than starting from scratch

Output Format:
Provide structured brainstorming output with:
- Main ideas (each with sources and confidence)
- Connections between ideas
- Suggested directions for further exploration
- Key questions that remain unanswered"""


class BrainstormerAgent(BaseAgent):
    """
    Agent for creative brainstorming and ideation.

    This agent:
    - Retrieves relevant content from the knowledge base
    - Synthesizes new ideas from existing knowledge
    - Explores concept graphs for connections
    - Consults other agents for diverse perspectives
    """

    def __init__(
        self,
        provider: BaseProvider,
        db_session=None,
        embedding_provider=None,
        orchestrator=None,
    ):
        """
        Initialize the brainstormer agent.

        Args:
            provider: LLM provider for synthesis
            db_session: Database session for knowledge retrieval
            embedding_provider: Provider for semantic search
            orchestrator: Orchestrator for multi-agent discussions
        """
        super().__init__(
            role=AgentRole.BRAINSTORMER,
            provider=provider,
            system_prompt=BRAINSTORMER_SYSTEM_PROMPT,
        )
        self.db_session = db_session
        self.embedding_provider = embedding_provider
        self.orchestrator = orchestrator
        self._brainstorm_tool = None

    def _get_brainstorm_tool(self):
        """Lazy load brainstorming tool."""
        if self._brainstorm_tool is None:
            from backend.tools import BrainstormingTool
            self._brainstorm_tool = BrainstormingTool(
                db_session=self.db_session,
                embedding_provider=self.embedding_provider,
                llm_provider=self.provider,
                orchestrator=self.orchestrator,
            )
        return self._brainstorm_tool

    async def execute(self, context: AgentContext) -> AgentResult:
        """
        Execute brainstorming based on the task.

        Args:
            context: Execution context with topic and constraints

        Returns:
            AgentResult with brainstormed ideas
        """
        start_time = datetime.utcnow()
        tool_uses = []

        try:
            # Parse task for brainstorming parameters
            topic = context.task
            constraints = context.constraints

            # Extract mode from constraints or infer from task
            mode = constraints.get("mode", self._infer_mode(topic))
            depth = constraints.get("depth", 2)
            sources = constraints.get("sources", ["philosophy", "culture", "notes", "concepts"])
            perspectives = constraints.get("perspectives", [])

            # Get existing context/ideas if available
            existing_context = {}
            if "ideas" in context.artifacts:
                existing_context["existing_ideas"] = context.artifacts["ideas"]
            if "focus" in constraints:
                existing_context["focus"] = constraints["focus"]

            # Execute brainstorming tool
            brainstorm_tool = self._get_brainstorm_tool()
            result = await brainstorm_tool(
                topic=topic,
                mode=mode,
                context=existing_context if existing_context else None,
                sources=sources,
                depth=depth,
                agent_perspectives=perspectives if perspectives else None,
            )

            tool_uses.append(ToolUse(
                tool_name="brainstorm",
                arguments={
                    "topic": topic,
                    "mode": mode,
                    "depth": depth,
                    "sources": sources,
                },
                result=result.data if result.success else result.error,
                timestamp=datetime.utcnow().isoformat(),
            ))

            if not result.success:
                return AgentResult(
                    success=False,
                    output=None,
                    error=result.error,
                    tool_uses=tool_uses,
                    duration_seconds=(datetime.utcnow() - start_time).total_seconds(),
                )

            # Post-process: Find connections between generated ideas
            session_data = result.data
            ideas = session_data.get("ideas", [])

            if len(ideas) > 2 and self.provider:
                # Use LLM to find connections
                connections = await self._find_connections(ideas)
                if connections:
                    session_data["connections"] = connections

                    tool_uses.append(ToolUse(
                        tool_name="find_connections",
                        arguments={"idea_count": len(ideas)},
                        result=connections,
                        timestamp=datetime.utcnow().isoformat(),
                    ))

            # Generate summary and next steps
            summary = await self._generate_summary(topic, session_data)
            session_data["summary"] = summary
            session_data["next_steps"] = await self._suggest_next_steps(topic, session_data)

            return AgentResult(
                success=True,
                output=session_data,
                tool_uses=tool_uses,
                metadata={
                    "topic": topic,
                    "mode": mode,
                    "idea_count": len(ideas),
                    "session_id": session_data.get("session_id"),
                },
                duration_seconds=(datetime.utcnow() - start_time).total_seconds(),
            )

        except Exception as e:
            return AgentResult(
                success=False,
                output=None,
                error=str(e),
                tool_uses=tool_uses,
                duration_seconds=(datetime.utcnow() - start_time).total_seconds(),
            )

    def _infer_mode(self, topic: str) -> str:
        """Infer brainstorming mode from the topic."""
        topic_lower = topic.lower()

        if any(word in topic_lower for word in ["challenge", "critique", "problem", "weakness"]):
            return "challenge"
        elif any(word in topic_lower for word in ["combine", "synthesize", "merge", "integrate"]):
            return "synthesize"
        elif any(word in topic_lower for word in ["analogy", "similar", "like", "compare"]):
            return "analogize"
        elif any(word in topic_lower for word in ["expand", "develop", "detail", "elaborate"]):
            return "elaborate"
        else:
            return "explore"

    async def _find_connections(self, ideas: list) -> Optional[dict]:
        """Find connections between brainstormed ideas."""
        if not ideas or len(ideas) < 2:
            return None

        try:
            ideas_text = "\n".join([
                f"{i+1}. {idea.get('content', '')[:200]}"
                for i, idea in enumerate(ideas[:10])
            ])

            prompt = f"""Analyze these brainstormed ideas for connections:

{ideas_text}

Identify:
1. Thematic clusters (ideas that share common themes)
2. Causal relationships (ideas that enable or lead to others)
3. Tensions or contradictions between ideas
4. Synthesis opportunities (ideas that could be combined)

Respond in JSON:
{{
  "clusters": [
    {{"theme": "...", "idea_indices": [1, 3, 5], "description": "..."}}
  ],
  "relationships": [
    {{"from": 1, "to": 3, "type": "enables", "description": "..."}}
  ],
  "tensions": [
    {{"ideas": [2, 4], "description": "..."}}
  ],
  "synthesis_opportunities": [
    {{"ideas": [1, 2], "potential": "..."}}
  ]
}}"""

            from backend.core.providers import GenerationRequest

            response = await self.provider.generate(GenerationRequest(
                prompt=prompt,
                system="Analyze ideas for patterns and connections.",
                temperature=0.5,
                json_schema={"type": "object"},
            ))

            return json.loads(response.text)

        except Exception:
            return None

    async def _generate_summary(self, topic: str, session_data: dict) -> str:
        """Generate a summary of the brainstorming session."""
        ideas = session_data.get("ideas", [])
        if not ideas:
            return "No ideas generated."

        try:
            ideas_text = "\n".join([
                f"- {idea.get('content', '')[:150]}"
                for idea in ideas[:8]
            ])

            prompt = f"""Summarize this brainstorming session on "{topic}":

Ideas generated:
{ideas_text}

Provide a 2-3 sentence summary of the key themes and most promising directions."""

            from backend.core.providers import GenerationRequest

            response = await self.provider.generate(GenerationRequest(
                prompt=prompt,
                system="Summarize brainstorming sessions concisely.",
                temperature=0.3,
                max_tokens=200,
            ))

            return response.text.strip()

        except Exception:
            return f"Generated {len(ideas)} ideas on {topic}."

    async def _suggest_next_steps(self, topic: str, session_data: dict) -> list[str]:
        """Suggest next steps based on brainstorming results."""
        ideas = session_data.get("ideas", [])
        connections = session_data.get("connections", {})

        try:
            context_text = f"Topic: {topic}\nIdea count: {len(ideas)}"
            if connections:
                context_text += f"\nClusters found: {len(connections.get('clusters', []))}"
                context_text += f"\nSynthesis opportunities: {len(connections.get('synthesis_opportunities', []))}"

            prompt = f"""Based on this brainstorming session:

{context_text}

Suggest 3-5 concrete next steps to develop these ideas further. Consider:
- Which ideas deserve deeper exploration
- What additional research might be needed
- How to test or validate promising directions
- Whether to consult specific experts or perspectives

Respond as a JSON array of strings."""

            from backend.core.providers import GenerationRequest

            response = await self.provider.generate(GenerationRequest(
                prompt=prompt,
                system="Suggest actionable next steps.",
                temperature=0.5,
                json_schema={"type": "array"},
            ))

            return json.loads(response.text)

        except Exception:
            return [
                "Review and prioritize generated ideas",
                "Research promising directions in depth",
                "Consult with domain experts",
            ]

    def get_required_tools(self) -> list[str]:
        """Get list of required tools."""
        return ["brainstorm", "semantic_search", "get_notes", "get_concepts"]

    def requires_sources(self) -> bool:
        """Brainstormer benefits from but doesn't require sources."""
        return False
