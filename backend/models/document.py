"""Document and Passage models for storing ingested content."""

from enum import Enum
from typing import Optional
from datetime import datetime
from sqlalchemy import String, Integer, Text, ForeignKey, Enum as SQLEnum, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from pgvector.sqlalchemy import Vector
import uuid

from .base import Base, TimestampMixin


class Citability(str, Enum):
    """Citability level for passages (copyright consideration)."""
    QUOTE_OK = "quote_ok"
    PARAPHRASE_ONLY = "paraphrase_only"
    RESTRICTED = "restricted"


class Document(Base, TimestampMixin):
    """
    A document represents a single piece of content from a source.
    """
    __tablename__ = "documents"

    doc_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sources.source_id"),
        nullable=False
    )

    retrieved_at: Mapped[datetime] = mapped_column(nullable=False)

    content_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        comment="SHA-256 hash for deduplication"
    )

    raw_content_uri: Mapped[str] = mapped_column(
        String(2000),
        nullable=False,
        comment="S3 URI or file path to stored content"
    )

    parsed_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Metadata
    metadata: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
        comment="Author, title, date, publication, etc."
    )

    # Processing status
    processing_status: Mapped[str] = mapped_column(
        String(50),
        default="pending",
        nullable=False
    )

    processing_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Statistics
    chunk_count: Mapped[int] = mapped_column(default=0, nullable=False)
    word_count: Mapped[int] = mapped_column(default=0, nullable=False)

    # Relationships
    passages: Mapped[list["Passage"]] = relationship(
        "Passage",
        back_populates="document",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_documents_source_hash", "source_id", "content_hash"),
    )

    def __repr__(self) -> str:
        title = self.metadata.get("title", "Untitled")
        return f"<Document {title[:50]}>"

    @property
    def title(self) -> str:
        """Get document title from metadata."""
        return self.metadata.get("title", "Untitled Document")

    @property
    def author(self) -> Optional[str]:
        """Get document author from metadata."""
        return self.metadata.get("author")

    @property
    def publish_date(self) -> Optional[datetime]:
        """Get publish date from metadata."""
        date_str = self.metadata.get("publish_date")
        if date_str:
            return datetime.fromisoformat(date_str)
        return None


class Passage(Base, TimestampMixin):
    """
    A passage is a chunk of a document, the atomic unit for retrieval and citation.
    """
    __tablename__ = "passages"

    passage_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    doc_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.doc_id", ondelete="CASCADE"),
        nullable=False
    )

    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)

    text: Mapped[str] = mapped_column(Text, nullable=False)

    char_start: Mapped[int] = mapped_column(Integer, nullable=False)
    char_end: Mapped[int] = mapped_column(Integer, nullable=False)

    # Vector embedding for semantic search
    embedding: Mapped[Optional[Vector]] = mapped_column(
        Vector(1536),  # OpenAI embedding dimension
        nullable=True
    )

    citability: Mapped[Citability] = mapped_column(
        SQLEnum(Citability),
        default=Citability.QUOTE_OK,
        nullable=False
    )

    # Location metadata (page, section, etc.)
    location_metadata: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False
    )

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="passages")

    __table_args__ = (
        Index("ix_passages_doc_chunk", "doc_id", "chunk_index"),
        Index("ix_passages_embedding", "embedding", postgresql_using="ivfflat"),
    )

    def __repr__(self) -> str:
        preview = self.text[:50] + "..." if len(self.text) > 50 else self.text
        return f"<Passage {preview}>"

    def get_citation(self, style: str = "inline") -> str:
        """
        Generate a citation string for this passage.

        Args:
            style: Citation style ('inline', 'footnote', 'mla', 'apa')

        Returns:
            Formatted citation string
        """
        doc = self.document
        author = doc.author or "Unknown"
        title = doc.title

        # Get page number if available
        page = self.location_metadata.get("page")

        if style == "inline":
            if page:
                return f"({author}, {title}, p. {page})"
            return f"({author}, {title})"

        elif style == "mla":
            citation = f'{author}. "{title}."'
            if page:
                citation += f" {page}."
            return citation

        # Add more citation styles as needed
        return f"{author}, {title}"
