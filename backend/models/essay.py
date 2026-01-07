"""Essay request and artifact models."""

from enum import Enum
from typing import Optional
from sqlalchemy import String, Integer, Text, JSON, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid

from .base import Base, TimestampMixin


class EssayStatus(str, Enum):
    """Status of an essay request."""
    PENDING = "pending"
    PLANNING = "planning"
    RESEARCHING = "researching"
    DRAFTING = "drafting"
    CRITIQUING = "critiquing"
    REVISING = "revising"
    AUDITING = "auditing"
    COMPLETED = "completed"
    FAILED = "failed"


class EssayRequest(Base, TimestampMixin):
    """
    An essay request tracks the full workflow from prompt to final essay.
    """
    __tablename__ = "essay_requests"

    request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Input
    prompt: Mapped[str] = mapped_column(Text, nullable=False)

    constraints: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
        comment="wordcount, tone, citation_style, mode, etc."
    )

    audience: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Allowed sources (list of source_ids)
    allowed_source_ids: Mapped[list] = mapped_column(
        JSONB,
        default=list,
        nullable=False
    )

    # Status tracking
    status: Mapped[EssayStatus] = mapped_column(
        SQLEnum(EssayStatus),
        default=EssayStatus.PENDING,
        nullable=False
    )

    current_stage: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    progress_percentage: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Error tracking
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Artifacts (stored as JSONB for flexibility)
    artifacts: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
        comment="thesis, outline, evidence_table, draft, critique, revisions, etc."
    )

    # Quality metrics
    quality_metrics: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
        comment="citation_coverage, specificity_score, cliche_count, etc."
    )

    # Final output
    final_essay: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    bibliography: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    uncertainties: Mapped[list] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
        comment="List of claims marked as uncertain/speculative"
    )

    def __repr__(self) -> str:
        preview = self.prompt[:50] + "..." if len(self.prompt) > 50 else self.prompt
        return f"<EssayRequest {preview} ({self.status})>"

    @property
    def wordcount_target(self) -> Optional[int]:
        """Get target wordcount from constraints."""
        return self.constraints.get("wordcount")

    @property
    def is_strict_mode(self) -> bool:
        """Check if operating in strict source-only mode."""
        return self.constraints.get("mode") == "strict"

    @property
    def citation_style(self) -> str:
        """Get citation style from constraints."""
        return self.constraints.get("citation_style", "MLA")

    def update_artifact(self, name: str, value: any) -> None:
        """Update a specific artifact."""
        self.artifacts[name] = value

    def get_artifact(self, name: str) -> Optional[any]:
        """Get a specific artifact."""
        return self.artifacts.get(name)

    def update_quality_metric(self, name: str, value: float) -> None:
        """Update a quality metric."""
        self.quality_metrics[name] = value

    def get_quality_metric(self, name: str) -> Optional[float]:
        """Get a quality metric."""
        return self.quality_metrics.get(name)


class EssayArtifact:
    """
    Helper class for working with essay artifacts.

    Provides type-safe access to common artifact structures.
    """

    @staticmethod
    def create_outline(
        thesis: str,
        sections: list[dict]
    ) -> dict:
        """Create an outline artifact."""
        return {
            "type": "outline",
            "thesis": thesis,
            "sections": sections
        }

    @staticmethod
    def create_evidence_table(claims: list[dict]) -> dict:
        """Create an evidence table artifact."""
        return {
            "type": "evidence_table",
            "claims": claims
        }

    @staticmethod
    def create_critique(
        structural_issues: list[str],
        style_issues: list[str],
        revision_plan: list[dict]
    ) -> dict:
        """Create a critique artifact."""
        return {
            "type": "critique",
            "structural_issues": structural_issues,
            "style_issues": style_issues,
            "revision_plan": revision_plan
        }
