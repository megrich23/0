"""Brainstorming tool for creative ideation with memory and agent collaboration."""

from typing import Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import json
import uuid

from .base import (
    BaseTool,
    ToolResult,
    ToolParameter,
    ToolCategory,
    register_tool,
    ToolRegistry,
)


class BrainstormingMode(str, Enum):
    """Modes of brainstorming."""
    EXPLORE = "explore"           # Open-ended exploration
    SYNTHESIZE = "synthesize"     # Combine existing ideas
    CHALLENGE = "challenge"       # Devil's advocate mode
    ANALOGIZE = "analogize"       # Find analogies and connections
    ELABORATE = "elaborate"       # Expand on existing ideas


@dataclass
class BrainstormIdea:
    """A single brainstormed idea."""
    idea_id: str
    content: str
    source_type: str  # 'memory', 'knowledge_base', 'agent', 'synthesis'
    sources: list[dict] = field(default_factory=list)  # References
    confidence: float = 0.5
    tags: list[str] = field(default_factory=list)
    related_ideas: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "idea_id": self.idea_id,
            "content": self.content,
            "source_type": self.source_type,
            "sources": self.sources,
            "confidence": self.confidence,
            "tags": self.tags,
            "related_ideas": self.related_ideas,
        }


@dataclass
class BrainstormSession:
    """A brainstorming session with accumulated ideas."""
    session_id: str
    topic: str
    mode: BrainstormingMode
    ideas: list[BrainstormIdea] = field(default_factory=list)
    context: dict = field(default_factory=dict)
    iterations: int = 0

    def add_idea(self, idea: BrainstormIdea) -> None:
        self.ideas.append(idea)

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "topic": self.topic,
            "mode": self.mode.value,
            "ideas": [i.to_dict() for i in self.ideas],
            "iterations": self.iterations,
        }


@register_tool
class BrainstormingTool(BaseTool):
    """
    Brainstorming tool that pulls from memory, knowledge base, and agent discussions.

    This tool enables creative ideation by:
    1. Retrieving relevant content from philosophy and culture knowledge bases
    2. Querying the concept graph for related ideas
    3. Synthesizing new ideas from retrieved information
    4. Facilitating multi-agent discussions for diverse perspectives
    """

    name = "brainstorm"
    description = "Generate ideas by pulling from memory, knowledge base, and agent discussions"
    category = ToolCategory.ANALYSIS

    parameters = [
        ToolParameter(
            name="topic",
            param_type=str,
            description="The topic or question to brainstorm about",
            required=True,
        ),
        ToolParameter(
            name="mode",
            param_type=str,
            description="Brainstorming mode: explore, synthesize, challenge, analogize, elaborate",
            required=False,
            default="explore",
        ),
        ToolParameter(
            name="context",
            param_type=dict,
            description="Additional context (existing ideas, constraints, goals)",
            required=False,
            default=None,
        ),
        ToolParameter(
            name="sources",
            param_type=list,
            description="Specific sources to pull from: 'philosophy', 'culture', 'notes', 'concepts'",
            required=False,
            default=None,
        ),
        ToolParameter(
            name="depth",
            param_type=int,
            description="Depth of exploration (1=surface, 3=deep)",
            required=False,
            default=2,
        ),
        ToolParameter(
            name="agent_perspectives",
            param_type=list,
            description="Agent roles to consult: 'critic', 'philosopher', 'curator'",
            required=False,
            default=None,
        ),
    ]

    def __init__(
        self,
        db_session=None,
        embedding_provider=None,
        llm_provider=None,
        orchestrator=None,
        **kwargs
    ):
        """
        Initialize brainstorming tool.

        Args:
            db_session: Database session for knowledge retrieval
            embedding_provider: Provider for semantic search
            llm_provider: LLM for synthesis and ideation
            orchestrator: Orchestrator for agent discussions
        """
        super().__init__(**kwargs)
        self.db_session = db_session
        self.embedding_provider = embedding_provider
        self.llm_provider = llm_provider
        self.orchestrator = orchestrator
        self._sessions: dict[str, BrainstormSession] = {}

    async def execute(
        self,
        topic: str,
        mode: str = "explore",
        context: Optional[dict] = None,
        sources: Optional[list] = None,
        depth: int = 2,
        agent_perspectives: Optional[list] = None,
    ) -> ToolResult:
        """
        Execute brainstorming session.

        Args:
            topic: Topic to brainstorm
            mode: Brainstorming mode
            context: Additional context
            sources: Sources to pull from
            depth: Exploration depth
            agent_perspectives: Agent perspectives to include

        Returns:
            ToolResult with BrainstormSession
        """
        try:
            # Parse mode
            try:
                brainstorm_mode = BrainstormingMode(mode)
            except ValueError:
                brainstorm_mode = BrainstormingMode.EXPLORE

            # Create session
            session = BrainstormSession(
                session_id=str(uuid.uuid4()),
                topic=topic,
                mode=brainstorm_mode,
                context=context or {},
            )

            # Default sources based on mode
            if sources is None:
                sources = ["philosophy", "culture", "notes", "concepts"]

            # Track which phases ran
            phases_run = []
            phases_skipped = []

            # Phase 1: Retrieve from knowledge base
            if self.db_session and self.embedding_provider:
                kb_ideas = await self._retrieve_from_knowledge_base(
                    topic=topic,
                    sources=sources,
                    depth=depth,
                )
                for idea in kb_ideas:
                    session.add_idea(idea)
                phases_run.append("knowledge_base_retrieval")
            else:
                phases_skipped.append({
                    "phase": "knowledge_base_retrieval",
                    "reason": "Missing db_session or embedding_provider"
                })

            # Phase 2: Query concept graph for connections
            if self.db_session and "concepts" in sources:
                concept_ideas = await self._explore_concept_graph(
                    topic=topic,
                    depth=depth,
                )
                for idea in concept_ideas:
                    session.add_idea(idea)
                phases_run.append("concept_graph_exploration")
            elif "concepts" in sources:
                phases_skipped.append({
                    "phase": "concept_graph_exploration",
                    "reason": "Missing db_session"
                })

            # Phase 3: Synthesize with LLM
            if self.llm_provider:
                synthesized = await self._synthesize_ideas(
                    session=session,
                    mode=brainstorm_mode,
                    context=context,
                )
                for idea in synthesized:
                    session.add_idea(idea)
                phases_run.append("llm_synthesis")
            else:
                phases_skipped.append({
                    "phase": "llm_synthesis",
                    "reason": "Missing llm_provider"
                })

            # Phase 4: Get agent perspectives
            if agent_perspectives and self.orchestrator:
                agent_ideas = await self._get_agent_perspectives(
                    topic=topic,
                    session=session,
                    perspectives=agent_perspectives,
                )
                for idea in agent_ideas:
                    session.add_idea(idea)
                phases_run.append("agent_perspectives")
            elif agent_perspectives:
                phases_skipped.append({
                    "phase": "agent_perspectives",
                    "reason": "Missing orchestrator"
                })

            # Store session
            self._sessions[session.session_id] = session
            session.iterations += 1

            # Build result with diagnostic info
            result_data = session.to_dict()
            result_data["phases_run"] = phases_run
            result_data["phases_skipped"] = phases_skipped

            # Warn if no ideas generated
            if not session.ideas and phases_skipped:
                return ToolResult.ok(
                    data=result_data,
                    session_id=session.session_id,
                    idea_count=0,
                    warning="No ideas generated - all phases skipped due to missing dependencies",
                )

            return ToolResult.ok(
                data=result_data,
                session_id=session.session_id,
                idea_count=len(session.ideas),
            )

        except Exception as e:
            return ToolResult.fail(f"Brainstorming failed: {str(e)}")

    async def _retrieve_from_knowledge_base(
        self,
        topic: str,
        sources: list[str],
        depth: int,
    ) -> list[BrainstormIdea]:
        """Retrieve relevant content from the knowledge base."""
        ideas = []

        # Get semantic search tool
        search_tool = ToolRegistry.get_tool(
            "semantic_search",
            db_session=self.db_session,
            embedding_provider=self.embedding_provider,
        )

        if not search_tool:
            return ideas

        # Determine content types to search
        content_types = []
        if "philosophy" in sources:
            content_types.append("philosophy")
        if "culture" in sources:
            content_types.append("culture")
        if not content_types:
            content_types = ["all"]

        # Search with depth-based limits
        limit = depth * 5  # More depth = more results

        for content_type in content_types:
            result = await search_tool(
                query=topic,
                limit=limit,
                min_score=0.4,
                content_type=content_type,
            )

            if result.success and result.data:
                for passage in result.data:
                    idea = BrainstormIdea(
                        idea_id=str(uuid.uuid4()),
                        content=passage["text"],
                        source_type="knowledge_base",
                        sources=[{
                            "type": content_type,
                            "passage_id": passage["passage_id"],
                            "title": passage["title"],
                            "author": passage["author"],
                            "score": passage["score"],
                        }],
                        confidence=passage["score"],
                        tags=[content_type],
                    )
                    ideas.append(idea)

        return ideas

    async def _explore_concept_graph(
        self,
        topic: str,
        depth: int,
    ) -> list[BrainstormIdea]:
        """Explore the concept graph for related ideas."""
        ideas = []

        # Get concepts tool
        concepts_tool = ToolRegistry.get_tool(
            "get_concepts",
            db_session=self.db_session,
        )

        if not concepts_tool:
            return ideas

        # Search for related concepts
        result = await concepts_tool(
            search_text=topic,
            include_relations=True,
        )

        if result.success and result.data:
            for concept in result.data:
                # Create idea from concept definition
                if concept.get("definition"):
                    idea = BrainstormIdea(
                        idea_id=str(uuid.uuid4()),
                        content=f"Concept: {concept['name']}\n{concept['definition']}",
                        source_type="concept_graph",
                        sources=[{
                            "type": "concept",
                            "concept_id": concept["concept_id"],
                            "name": concept["name"],
                        }],
                        confidence=0.7,
                        tags=["concept", "philosophy"],
                    )
                    ideas.append(idea)

                # Explore relations for deeper connections
                if depth > 1 and concept.get("related_to"):
                    for relation in concept["related_to"][:depth]:
                        rel_idea = BrainstormIdea(
                            idea_id=str(uuid.uuid4()),
                            content=f"Connection: {concept['name']} {relation['relation']} another concept",
                            source_type="concept_graph",
                            sources=[{
                                "type": "relation",
                                "from_concept": concept["name"],
                                "relation_type": relation["relation"],
                                "description": relation.get("description"),
                            }],
                            confidence=0.6,
                            tags=["connection", "philosophy"],
                        )
                        ideas.append(rel_idea)

        # Also check notes
        notes_tool = ToolRegistry.get_tool(
            "get_notes",
            db_session=self.db_session,
        )

        if notes_tool:
            notes_result = await notes_tool(
                search_text=topic,
                limit=depth * 3,
            )

            if notes_result.success and notes_result.data:
                for note in notes_result.data:
                    idea = BrainstormIdea(
                        idea_id=str(uuid.uuid4()),
                        content=f"Note: {note['title']}\n{note['body']}",
                        source_type="memory",
                        sources=[{
                            "type": "note",
                            "note_id": note["note_id"],
                            "title": note["title"],
                        }],
                        confidence=0.8,
                        tags=note.get("tags", []) + ["note"],
                    )
                    ideas.append(idea)

        return ideas

    async def _synthesize_ideas(
        self,
        session: BrainstormSession,
        mode: BrainstormingMode,
        context: Optional[dict],
    ) -> list[BrainstormIdea]:
        """Use LLM to synthesize new ideas from retrieved content."""
        ideas = []

        if not self.llm_provider:
            return ideas

        # Build synthesis prompt based on mode
        existing_ideas = "\n".join([
            f"- {idea.content[:200]}..." if len(idea.content) > 200 else f"- {idea.content}"
            for idea in session.ideas[:10]  # Limit context
        ])

        mode_prompts = {
            BrainstormingMode.EXPLORE: (
                "Generate diverse, creative ideas exploring different angles of this topic. "
                "Consider unconventional perspectives and surprising connections."
            ),
            BrainstormingMode.SYNTHESIZE: (
                "Combine and synthesize the existing ideas into novel insights. "
                "Look for patterns, themes, and opportunities to merge concepts."
            ),
            BrainstormingMode.CHALLENGE: (
                "Play devil's advocate. Challenge assumptions, identify weaknesses, "
                "and propose counterarguments to the existing ideas."
            ),
            BrainstormingMode.ANALOGIZE: (
                "Find analogies and connections to other domains, fields, or concepts. "
                "What can we learn from similar situations elsewhere?"
            ),
            BrainstormingMode.ELABORATE: (
                "Expand and deepen the most promising ideas. Add detail, "
                "consider implications, and explore how they could be developed."
            ),
        }

        prompt = f"""Topic: {session.topic}

Existing ideas and sources:
{existing_ideas}

{f"Additional context: {json.dumps(context)}" if context else ""}

Task: {mode_prompts.get(mode, mode_prompts[BrainstormingMode.EXPLORE])}

Generate 3-5 new ideas. For each idea:
1. State the idea clearly
2. Explain the reasoning or connection
3. Note any relevant sources or inspirations

Respond in JSON format:
{{
  "ideas": [
    {{
      "content": "The idea",
      "reasoning": "Why this is interesting/relevant",
      "inspired_by": ["source1", "source2"],
      "confidence": 0.7
    }}
  ]
}}"""

        try:
            from backend.core.providers import GenerationRequest

            request = GenerationRequest(
                prompt=prompt,
                system="You are a creative brainstorming assistant skilled at generating novel ideas and finding unexpected connections.",
                temperature=0.8,  # Higher temperature for creativity
                json_schema={"type": "object"},
            )

            response = await self.llm_provider.generate(request)
            result = json.loads(response.text)

            for item in result.get("ideas", []):
                idea = BrainstormIdea(
                    idea_id=str(uuid.uuid4()),
                    content=item["content"],
                    source_type="synthesis",
                    sources=[{
                        "type": "llm_synthesis",
                        "reasoning": item.get("reasoning", ""),
                        "inspired_by": item.get("inspired_by", []),
                    }],
                    confidence=item.get("confidence", 0.6),
                    tags=[mode.value, "synthesized"],
                )
                ideas.append(idea)

        except Exception as e:
            # Log but don't fail - synthesis is optional
            pass

        return ideas

    async def _get_agent_perspectives(
        self,
        topic: str,
        session: BrainstormSession,
        perspectives: list[str],
    ) -> list[BrainstormIdea]:
        """Get perspectives from other agents in the system."""
        ideas = []

        if not self.orchestrator:
            return ideas

        # Map perspective names to agent roles
        from backend.agents.base import AgentRole

        perspective_map = {
            "critic": AgentRole.CRITIC,
            "philosopher": AgentRole.TUTOR,
            "curator": AgentRole.CURATOR,
            "researcher": AgentRole.RESEARCH,
            "planner": AgentRole.PLANNER,
        }

        # Collect existing ideas summary
        ideas_summary = "\n".join([
            f"- {idea.content[:150]}"
            for idea in session.ideas[:5]
        ])

        for perspective in perspectives:
            agent_role = perspective_map.get(perspective.lower())
            if not agent_role:
                continue

            agent = self.orchestrator.agents.get(agent_role)
            if not agent:
                continue

            # Create a mini-context for the agent
            from backend.agents.base import AgentContext

            context = AgentContext(
                task=f"Provide your perspective on this brainstorming topic: {topic}\n\nExisting ideas:\n{ideas_summary}",
                constraints={"max_ideas": 3, "perspective": perspective},
                artifacts={"brainstorm_session": session.to_dict()},
            )

            try:
                result = await agent.execute(context)
                if result.success and result.output:
                    # Parse agent output into ideas
                    output = result.output
                    if isinstance(output, str):
                        idea = BrainstormIdea(
                            idea_id=str(uuid.uuid4()),
                            content=output,
                            source_type="agent",
                            sources=[{
                                "type": "agent_perspective",
                                "agent_role": agent_role.value,
                                "perspective": perspective,
                            }],
                            confidence=0.7,
                            tags=[perspective, "agent_generated"],
                        )
                        ideas.append(idea)
                    elif isinstance(output, dict):
                        # Handle structured output
                        for key, value in output.items():
                            if isinstance(value, str) and len(value) > 20:
                                idea = BrainstormIdea(
                                    idea_id=str(uuid.uuid4()),
                                    content=f"{key}: {value}",
                                    source_type="agent",
                                    sources=[{
                                        "type": "agent_perspective",
                                        "agent_role": agent_role.value,
                                        "perspective": perspective,
                                        "aspect": key,
                                    }],
                                    confidence=0.7,
                                    tags=[perspective, "agent_generated", key],
                                )
                                ideas.append(idea)

            except Exception:
                # Agent consultation is optional, continue on failure
                pass

        return ideas

    async def continue_session(
        self,
        session_id: str,
        direction: Optional[str] = None,
        selected_ideas: Optional[list[str]] = None,
    ) -> ToolResult:
        """
        Continue an existing brainstorming session.

        Args:
            session_id: ID of session to continue
            direction: New direction or focus
            selected_ideas: IDs of ideas to build upon

        Returns:
            ToolResult with updated session
        """
        session = self._sessions.get(session_id)
        if not session:
            return ToolResult.fail(f"Session not found: {session_id}")

        # Update context with selected ideas
        if selected_ideas:
            session.context["focus_ideas"] = [
                idea.to_dict()
                for idea in session.ideas
                if idea.idea_id in selected_ideas
            ]

        # Re-run with new direction
        topic = direction or session.topic
        return await self.execute(
            topic=topic,
            mode=session.mode.value,
            context=session.context,
            depth=3,  # Deeper on continuation
        )


@register_tool
class IdeaConnectionTool(BaseTool):
    """Find connections between ideas in brainstorming sessions."""

    name = "find_idea_connections"
    description = "Find connections and patterns between brainstormed ideas"
    category = ToolCategory.ANALYSIS

    parameters = [
        ToolParameter(
            name="ideas",
            param_type=list,
            description="List of ideas to analyze for connections",
            required=True,
        ),
        ToolParameter(
            name="connection_type",
            param_type=str,
            description="Type of connections: 'thematic', 'causal', 'analogical', 'all'",
            required=False,
            default="all",
        ),
    ]

    def __init__(self, llm_provider=None, **kwargs):
        super().__init__(**kwargs)
        self.llm_provider = llm_provider

    async def execute(
        self,
        ideas: list,
        connection_type: str = "all",
    ) -> ToolResult:
        """Find connections between ideas."""
        if not self.llm_provider:
            return ToolResult.fail("LLM provider required for connection analysis")

        try:
            ideas_text = "\n".join([
                f"{i+1}. {idea if isinstance(idea, str) else idea.get('content', str(idea))}"
                for i, idea in enumerate(ideas)
            ])

            prompt = f"""Analyze these ideas for connections and patterns:

{ideas_text}

Find {connection_type if connection_type != 'all' else 'thematic, causal, and analogical'} connections.

Respond in JSON:
{{
  "connections": [
    {{
      "idea_indices": [1, 3],
      "connection_type": "thematic",
      "description": "Both ideas relate to...",
      "strength": 0.8
    }}
  ],
  "clusters": [
    {{
      "name": "Cluster theme",
      "idea_indices": [1, 2, 4],
      "description": "These ideas form a coherent group around..."
    }}
  ],
  "insights": ["Key insight 1", "Key insight 2"]
}}"""

            from backend.core.providers import GenerationRequest

            request = GenerationRequest(
                prompt=prompt,
                system="You are an analytical assistant skilled at finding patterns and connections between ideas.",
                temperature=0.5,
                json_schema={"type": "object"},
            )

            response = await self.llm_provider.generate(request)
            result = json.loads(response.text)

            return ToolResult.ok(
                data=result,
                connection_count=len(result.get("connections", [])),
                cluster_count=len(result.get("clusters", [])),
            )

        except Exception as e:
            return ToolResult.fail(f"Connection analysis failed: {str(e)}")
