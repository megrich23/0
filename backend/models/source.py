"""Source model for tracking allowed data sources."""

from enum import Enum
from typing import Optional
from datetime import datetime
from sqlalchemy import String, Boolean, JSON, Text, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, ARRAY
import uuid

from .base import Base, TimestampMixin, SoftDeleteMixin


class SourceType(str, Enum):
    """Type of source."""
    UPLOAD = "upload"
    URL = "url"
    RSS = "rss"
    NEWSLETTER = "newsletter"
    API = "api"


class Source(Base, TimestampMixin, SoftDeleteMixin):
    """
    A source represents an allowed origin for documents.

    Users explicitly allowlist sources to control what the system can reference.
    """
    __tablename__ = "sources"

    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    type: Mapped[SourceType] = mapped_column(
        SQLEnum(SourceType),
        nullable=False
    )

    title: Mapped[str] = mapped_column(String(500), nullable=False)

    base_url: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)

    allowlisted: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    tags: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)

    # Fetch policy configuration
    fetch_policy: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
        comment="Rate limits, robots compliance, auth config"
    )

    # Metadata
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Statistics
    document_count: Mapped[int] = mapped_column(default=0, nullable=False)
    last_fetched_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    def __repr__(self) -> str:
        return f"<Source {self.title} ({self.type})>"

    @property
    def is_active(self) -> bool:
        """Check if source is active (allowlisted and not deleted)."""
        return self.allowlisted and not self.is_deleted


class FetchPolicy:
    """
    Configuration for fetching content from a source.

    This is a helper class for working with the fetch_policy JSON field.
    """

    def __init__(
        self,
        rate_limit_rpm: int = 10,
        respect_robots_txt: bool = True,
        user_agent: str = "Essay-System-Bot/1.0",
        timeout_seconds: int = 30,
        max_retries: int = 3,
        auth_method: Optional[str] = None,
        auth_config: Optional[dict] = None,
    ):
        self.rate_limit_rpm = rate_limit_rpm
        self.respect_robots_txt = respect_robots_txt
        self.user_agent = user_agent
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.auth_method = auth_method
        self.auth_config = auth_config or {}

    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            "rate_limit_rpm": self.rate_limit_rpm,
            "respect_robots_txt": self.respect_robots_txt,
            "user_agent": self.user_agent,
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
            "auth_method": self.auth_method,
            "auth_config": self.auth_config,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FetchPolicy":
        """Create from dictionary."""
        return cls(**data)
