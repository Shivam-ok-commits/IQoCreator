"""Recommendation model."""

from __future__ import annotations

import uuid
from enum import Enum as PyEnum

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, TimestampMixin, uuid_pk


class RecommendationStatus(str, PyEnum):
    """Lifecycle status of a recommendation."""

    DRAFT = "draft"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class Recommendation(TimestampMixin, Base):
    """A course of action generated from analysis results."""

    __tablename__ = "recommendations"

    id: Mapped[uuid.UUID] = uuid_pk()
    analysis_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analysis_runs.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    creator_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("creator_profiles.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    claim_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("claims.id", ondelete="SET NULL"),
        nullable=True,
    )
    recommendation_type: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority: Mapped[int | None] = mapped_column(Integer, nullable=True)
    generator_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[RecommendationStatus] = mapped_column(
        String(16), nullable=False,
        default=RecommendationStatus.DRAFT, index=True,
    )
    extra_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # ── Relationships ────────────────────────────────────────────────────
    analysis_run: Mapped["AnalysisRun"] = relationship(
        "AnalysisRun", back_populates="recommendations"
    )
    creator_profile: Mapped["CreatorProfile"] = relationship(
        "CreatorProfile", back_populates="recommendations"
    )
    claim: Mapped["Claim | None"] = relationship(
        "Claim", back_populates="recommendations"
    )
    feedback: Mapped[list["RecommendationFeedback"]] = relationship(
        "RecommendationFeedback", back_populates="recommendation",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Recommendation id={self.id} type={self.recommendation_type}>"
