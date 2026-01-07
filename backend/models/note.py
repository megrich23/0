"""Note and Concept models for knowledge graph (Zettelkasten-style)."""

from enum import Enum
from typing import Optional
from sqlalchemy import String, Text, ForeignKey, Table, Column, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, ARRAY
import uuid

from .base import Base, TimestampMixin


# Association table for note-to-note links
note_links = Table(
    "note_links",
    Base.metadata,
    Column("source_note_id", UUID(as_uuid=True), ForeignKey("notes.note_id"), primary_key=True),
    Column("target_note_id", UUID(as_uuid=True), ForeignKey("notes.note_id"), primary_key=True),
)


# Association table for note-to-passage references
note_passages = Table(
    "note_passages",
    Base.metadata,
    Column("note_id", UUID(as_uuid=True), ForeignKey("notes.note_id"), primary_key=True),
    Column("passage_id", UUID(as_uuid=True), ForeignKey("passages.passage_id"), primary_key=True),
)


class Note(Base, TimestampMixin):
    """
    A Zettelkasten-style note (atomic piece of knowledge).

    Notes are:
    - Atomic (one idea)
    - Linked to other notes
    - Tagged
    - Connected to source passages
    """
    __tablename__ = "notes"

    note_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    title: Mapped[str] = mapped_column(String(500), nullable=False)

    body: Mapped[str] = mapped_column(Text, nullable=False)

    tags: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)

    # Relationships
    # Notes this note links to
    links: Mapped[list["Note"]] = relationship(
        "Note",
        secondary=note_links,
        primaryjoin=note_id == note_links.c.source_note_id,
        secondaryjoin=note_id == note_links.c.target_note_id,
        backref="backlinks"
    )

    # Source passages this note references
    source_passages: Mapped[list["Passage"]] = relationship(
        "Passage",
        secondary=note_passages
    )

    def __repr__(self) -> str:
        return f"<Note {self.title}>"

    def add_link(self, target_note: "Note") -> None:
        """Add a link to another note."""
        if target_note not in self.links:
            self.links.append(target_note)

    def add_source(self, passage: "Passage") -> None:
        """Add a source passage reference."""
        if passage not in self.source_passages:
            self.source_passages.append(passage)


class ConceptRelationType(str, Enum):
    """Types of relationships between concepts."""
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    IS_EXAMPLE_OF = "is_example_of"
    IS_PART_OF = "is_part_of"
    DEPENDS_ON = "depends_on"
    RELATED_TO = "related_to"


class ConceptRelation(Base):
    """Relationship between two concepts."""
    __tablename__ = "concept_relations"

    relation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    source_concept_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("concepts.concept_id"),
        nullable=False
    )

    target_concept_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("concepts.concept_id"),
        nullable=False
    )

    relation_type: Mapped[ConceptRelationType] = mapped_column(
        SQLEnum(ConceptRelationType),
        nullable=False
    )

    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<ConceptRelation {self.relation_type}>"


class Concept(Base, TimestampMixin):
    """
    A concept extracted from philosophical texts.

    Concepts form a graph that helps understand relationships between ideas.
    """
    __tablename__ = "concepts"

    concept_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)

    definition: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    outgoing_relations: Mapped[list[ConceptRelation]] = relationship(
        "ConceptRelation",
        foreign_keys=[ConceptRelation.source_concept_id],
        cascade="all, delete-orphan"
    )

    incoming_relations: Mapped[list[ConceptRelation]] = relationship(
        "ConceptRelation",
        foreign_keys=[ConceptRelation.target_concept_id],
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Concept {self.name}>"

    def add_relation(
        self,
        target: "Concept",
        relation_type: ConceptRelationType,
        description: Optional[str] = None
    ) -> ConceptRelation:
        """Add a relationship to another concept."""
        relation = ConceptRelation(
            source_concept_id=self.concept_id,
            target_concept_id=target.concept_id,
            relation_type=relation_type,
            description=description
        )
        self.outgoing_relations.append(relation)
        return relation
