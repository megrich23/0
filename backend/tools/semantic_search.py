"""Semantic search tool for knowledge base retrieval."""

from typing import Optional
from dataclasses import dataclass
import uuid

from .base import (
    BaseTool,
    ToolResult,
    ToolParameter,
    ToolCategory,
    register_tool,
)


@dataclass
class SearchResult:
    """A single search result from the knowledge base."""
    passage_id: str
    doc_id: str
    text: str
    score: float
    title: str
    author: Optional[str]
    location: dict
    citability: str

    def to_dict(self) -> dict:
        return {
            "passage_id": self.passage_id,
            "doc_id": self.doc_id,
            "text": self.text,
            "score": self.score,
            "title": self.title,
            "author": self.author,
            "location": self.location,
            "citability": self.citability,
        }


@register_tool
class SemanticSearchTool(BaseTool):
    """
    Semantic search over the knowledge base using vector embeddings.

    Searches passages from philosophy texts, culture watch content,
    and other ingested documents.
    """

    name = "semantic_search"
    description = "Search the knowledge base for passages semantically similar to a query"
    category = ToolCategory.RETRIEVAL

    parameters = [
        ToolParameter(
            name="query",
            param_type=str,
            description="The search query text",
            required=True,
        ),
        ToolParameter(
            name="limit",
            param_type=int,
            description="Maximum number of results to return",
            required=False,
            default=10,
        ),
        ToolParameter(
            name="min_score",
            param_type=float,
            description="Minimum similarity score threshold (0-1)",
            required=False,
            default=0.5,
        ),
        ToolParameter(
            name="source_filter",
            param_type=list,
            description="List of source IDs to filter by",
            required=False,
            default=None,
        ),
        ToolParameter(
            name="content_type",
            param_type=str,
            description="Filter by content type: 'philosophy', 'culture', 'all'",
            required=False,
            default="all",
        ),
    ]

    def __init__(self, db_session=None, embedding_provider=None, **kwargs):
        """
        Initialize semantic search tool.

        Args:
            db_session: SQLAlchemy async session
            embedding_provider: Provider for generating embeddings
        """
        super().__init__(**kwargs)
        self.db_session = db_session
        self.embedding_provider = embedding_provider

    async def execute(
        self,
        query: str,
        limit: int = 10,
        min_score: float = 0.5,
        source_filter: Optional[list] = None,
        content_type: str = "all",
    ) -> ToolResult:
        """
        Execute semantic search.

        Args:
            query: Search query text
            limit: Maximum results
            min_score: Minimum similarity threshold
            source_filter: Optional source ID filter
            content_type: Content type filter

        Returns:
            ToolResult with list of SearchResult
        """
        if not self.db_session or not self.embedding_provider:
            return ToolResult.fail(
                "Semantic search requires database session and embedding provider"
            )

        try:
            # Generate embedding for query
            query_embedding = await self.embedding_provider.embed([query])
            if not query_embedding:
                return ToolResult.fail("Failed to generate query embedding")

            query_vector = query_embedding[0]

            # Build the search query
            results = await self._search_passages(
                query_vector=query_vector,
                limit=limit,
                min_score=min_score,
                source_filter=source_filter,
                content_type=content_type,
            )

            return ToolResult.ok(
                data=[r.to_dict() for r in results],
                query=query,
                result_count=len(results),
            )

        except Exception as e:
            return ToolResult.fail(f"Search failed: {str(e)}")

    async def _search_passages(
        self,
        query_vector: list[float],
        limit: int,
        min_score: float,
        source_filter: Optional[list],
        content_type: str,
    ) -> list[SearchResult]:
        """
        Search passages using pgvector similarity.

        Args:
            query_vector: Query embedding vector
            limit: Result limit
            min_score: Score threshold
            source_filter: Source filter
            content_type: Content type filter

        Returns:
            List of SearchResult
        """
        from sqlalchemy import select, func
        from sqlalchemy.orm import joinedload
        from backend.models.document import Passage, Document

        # Build query with cosine similarity
        # pgvector uses <=> for cosine distance, we convert to similarity
        similarity = 1 - Passage.embedding.cosine_distance(query_vector)

        stmt = (
            select(Passage, similarity.label("score"))
            .join(Document)
            .where(Passage.embedding.isnot(None))
            .where(similarity >= min_score)
            .options(joinedload(Passage.document))
            .order_by(similarity.desc())
            .limit(limit)
        )

        # Apply source filter
        if source_filter:
            stmt = stmt.where(Document.source_id.in_(source_filter))

        # Apply content type filter (based on source metadata/tags)
        if content_type != "all":
            # This would filter based on source type or document metadata
            # Implementation depends on how content types are tagged
            pass

        result = await self.db_session.execute(stmt)
        rows = result.all()

        search_results = []
        for passage, score in rows:
            doc = passage.document
            search_results.append(
                SearchResult(
                    passage_id=str(passage.passage_id),
                    doc_id=str(passage.doc_id),
                    text=passage.text,
                    score=float(score),
                    title=doc.title,
                    author=doc.author,
                    location=passage.location_metadata,
                    citability=passage.citability.value,
                )
            )

        return search_results


@register_tool
class GetPassageTool(BaseTool):
    """Retrieve a specific passage by ID."""

    name = "get_passage"
    description = "Get a specific passage from the knowledge base by its ID"
    category = ToolCategory.RETRIEVAL

    parameters = [
        ToolParameter(
            name="passage_id",
            param_type=str,
            description="The UUID of the passage to retrieve",
            required=True,
        ),
    ]

    def __init__(self, db_session=None, **kwargs):
        super().__init__(**kwargs)
        self.db_session = db_session

    async def execute(self, passage_id: str) -> ToolResult:
        """Retrieve a passage by ID."""
        if not self.db_session:
            return ToolResult.fail("Database session required")

        try:
            from sqlalchemy import select
            from sqlalchemy.orm import joinedload
            from backend.models.document import Passage

            stmt = (
                select(Passage)
                .where(Passage.passage_id == uuid.UUID(passage_id))
                .options(joinedload(Passage.document))
            )

            result = await self.db_session.execute(stmt)
            passage = result.scalar_one_or_none()

            if not passage:
                return ToolResult.fail(f"Passage not found: {passage_id}")

            doc = passage.document
            return ToolResult.ok(
                data={
                    "passage_id": str(passage.passage_id),
                    "doc_id": str(passage.doc_id),
                    "text": passage.text,
                    "title": doc.title,
                    "author": doc.author,
                    "location": passage.location_metadata,
                    "citability": passage.citability.value,
                    "citation": passage.get_citation(),
                }
            )

        except Exception as e:
            return ToolResult.fail(f"Failed to retrieve passage: {str(e)}")


@register_tool
class GetNotesTool(BaseTool):
    """Retrieve notes from the Zettelkasten by tags or search."""

    name = "get_notes"
    description = "Search or retrieve notes from the knowledge graph"
    category = ToolCategory.MEMORY

    parameters = [
        ToolParameter(
            name="tags",
            param_type=list,
            description="Tags to filter notes by",
            required=False,
            default=None,
        ),
        ToolParameter(
            name="search_text",
            param_type=str,
            description="Text to search in note titles and bodies",
            required=False,
            default=None,
        ),
        ToolParameter(
            name="limit",
            param_type=int,
            description="Maximum notes to return",
            required=False,
            default=20,
        ),
    ]

    def __init__(self, db_session=None, **kwargs):
        super().__init__(**kwargs)
        self.db_session = db_session

    async def execute(
        self,
        tags: Optional[list] = None,
        search_text: Optional[str] = None,
        limit: int = 20,
    ) -> ToolResult:
        """Retrieve notes by tags or search."""
        if not self.db_session:
            return ToolResult.fail("Database session required")

        try:
            from sqlalchemy import select, or_, func
            from backend.models.note import Note

            stmt = select(Note).limit(limit)

            # Filter by tags
            if tags:
                stmt = stmt.where(Note.tags.overlap(tags))

            # Search text
            if search_text:
                search_pattern = f"%{search_text}%"
                stmt = stmt.where(
                    or_(
                        Note.title.ilike(search_pattern),
                        Note.body.ilike(search_pattern),
                    )
                )

            result = await self.db_session.execute(stmt)
            notes = result.scalars().all()

            return ToolResult.ok(
                data=[
                    {
                        "note_id": str(note.note_id),
                        "title": note.title,
                        "body": note.body,
                        "tags": note.tags,
                    }
                    for note in notes
                ],
                result_count=len(notes),
            )

        except Exception as e:
            return ToolResult.fail(f"Failed to retrieve notes: {str(e)}")


@register_tool
class GetConceptsTool(BaseTool):
    """Retrieve concepts and their relationships from the knowledge graph."""

    name = "get_concepts"
    description = "Get concepts and their relationships from the philosophical knowledge graph"
    category = ToolCategory.MEMORY

    parameters = [
        ToolParameter(
            name="concept_names",
            param_type=list,
            description="Names of concepts to retrieve",
            required=False,
            default=None,
        ),
        ToolParameter(
            name="search_text",
            param_type=str,
            description="Text to search in concept names and definitions",
            required=False,
            default=None,
        ),
        ToolParameter(
            name="include_relations",
            param_type=bool,
            description="Whether to include related concepts",
            required=False,
            default=True,
        ),
    ]

    def __init__(self, db_session=None, **kwargs):
        super().__init__(**kwargs)
        self.db_session = db_session

    async def execute(
        self,
        concept_names: Optional[list] = None,
        search_text: Optional[str] = None,
        include_relations: bool = True,
    ) -> ToolResult:
        """Retrieve concepts from knowledge graph."""
        if not self.db_session:
            return ToolResult.fail("Database session required")

        try:
            from sqlalchemy import select, or_
            from sqlalchemy.orm import joinedload
            from backend.models.note import Concept, ConceptRelation

            stmt = select(Concept)

            if concept_names:
                stmt = stmt.where(Concept.name.in_(concept_names))

            if search_text:
                search_pattern = f"%{search_text}%"
                stmt = stmt.where(
                    or_(
                        Concept.name.ilike(search_pattern),
                        Concept.definition.ilike(search_pattern),
                    )
                )

            if include_relations:
                stmt = stmt.options(
                    joinedload(Concept.outgoing_relations),
                    joinedload(Concept.incoming_relations),
                )

            result = await self.db_session.execute(stmt)
            concepts = result.unique().scalars().all()

            data = []
            for concept in concepts:
                concept_data = {
                    "concept_id": str(concept.concept_id),
                    "name": concept.name,
                    "definition": concept.definition,
                }

                if include_relations:
                    concept_data["related_to"] = [
                        {
                            "concept": rel.target_concept_id,
                            "relation": rel.relation_type.value,
                            "description": rel.description,
                        }
                        for rel in concept.outgoing_relations
                    ]
                    concept_data["related_from"] = [
                        {
                            "concept": rel.source_concept_id,
                            "relation": rel.relation_type.value,
                            "description": rel.description,
                        }
                        for rel in concept.incoming_relations
                    ]

                data.append(concept_data)

            return ToolResult.ok(data=data, result_count=len(data))

        except Exception as e:
            return ToolResult.fail(f"Failed to retrieve concepts: {str(e)}")
