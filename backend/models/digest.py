"""Digest models for culture watch functionality."""

from typing import Optional
from datetime import datetime
from sqlalchemy import String, Integer, Text, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
import uuid

from .base import Base, TimestampMixin


class DigestIssue(Base, TimestampMixin):
    """
    A digest issue represents a periodic summary of cultural scene activity.
    """
    __tablename__ = "digest_issues"

    issue_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    tags: Mapped[list[str]] = mapped_column(
        ARRAY(String),
        default=list,
        nullable=False,
        comment="Tags used to filter sources (e.g., dimes_square, poetry)"
    )

    # Summary content
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)

    # Clusters of related items
    clusters: Mapped[list] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
        comment="Topic clusters with linked items"
    )

    # Highlights (top N items)
    highlights: Mapped[list] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
        comment="Top items for this period"
    )

    # Emerging themes
    emerging_themes: Mapped[list] = mapped_column(
        JSONB,
        default=list,
        nullable=False
    )

    # Trend statistics
    trend_stats: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
        comment="Time series data, frequencies, co-mentions"
    )

    # Notable quotes (small excerpts)
    notable_quotes: Mapped[list] = mapped_column(
        JSONB,
        default=list,
        nullable=False
    )

    # Processing metadata
    document_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    source_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    published: Mapped[bool] = mapped_column(default=False, nullable=False)
    published_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    def __repr__(self) -> str:
        return f"<DigestIssue {self.title} ({self.period_start.date()} - {self.period_end.date()})>"

    def publish(self) -> None:
        """Mark the digest as published."""
        self.published = True
        self.published_at = datetime.utcnow()


class DigestCluster(Base):
    """
    A cluster represents a group of related items in a digest.
    """
    __tablename__ = "digest_clusters"

    cluster_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    issue_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("digest_issues.issue_id"),
        nullable=False
    )

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Document IDs in this cluster
    document_ids: Mapped[list] = mapped_column(
        JSONB,
        default=list,
        nullable=False
    )

    # Keywords/topics
    keywords: Mapped[list[str]] = mapped_column(
        ARRAY(String),
        default=list,
        nullable=False
    )

    # Named entities (people, venues, presses)
    entities: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
        comment="people, venues, presses, publications"
    )

    # Centrality score (how important is this cluster)
    centrality_score: Mapped[float] = mapped_column(default=0.0, nullable=False)

    def __repr__(self) -> str:
        return f"<DigestCluster {self.title}>"


class CultureWatchSource(Base, TimestampMixin):
    """
    Extended source tracking specifically for culture watch.
    Tracks additional metadata like fetch frequency and processing stats.
    """
    __tablename__ = "culture_watch_sources"

    cw_source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sources.source_id"),
        nullable=False
    )

    # Scheduling
    fetch_frequency_hours: Mapped[int] = mapped_column(
        Integer,
        default=24,
        nullable=False
    )

    last_successful_fetch: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Statistics
    total_items_fetched: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    items_this_week: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    items_this_month: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Health
    consecutive_errors: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<CultureWatchSource {self.source_id}>"

    def record_success(self, item_count: int) -> None:
        """Record a successful fetch."""
        self.last_successful_fetch = datetime.utcnow()
        self.total_items_fetched += item_count
        self.items_this_week += item_count
        self.items_this_month += item_count
        self.consecutive_errors = 0
        self.last_error = None

    def record_error(self, error_message: str) -> None:
        """Record a fetch error."""
        self.last_error = error_message
        self.consecutive_errors += 1

        # Deactivate after too many consecutive errors
        if self.consecutive_errors >= 5:
            self.is_active = False
