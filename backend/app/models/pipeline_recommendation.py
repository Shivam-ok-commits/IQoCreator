"""PipelineRecommendation model — immutable recommendation artifact.

Terminal artifact of the intelligence pipeline (Sprint 9).
Consumed by the LearningEngine (Sprint 10) and presented to creators.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, uuid_pk


class PipelineRecommendation(Base):
    """Immutable recommendation artifact produced by RecommendationEngine.

    One recommendation per PipelineClaim. Represents an actionable,
    deterministic course of action derived from a claim.
    Terminal artifact — consumed by LearningEngine or presented to users.
    """

    __tablename__ = "pipeline_recommendations"

    id: Mapped[uuid.UUID] = uuid_pk()
    creator_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("creator_profiles.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    source_claim_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pipeline_claims.id", ondelete="CASCADE"),
        nullable=True, index=True,
    )

    # ── Recommendation content ─────────────────────────────────────────
    priority: Mapped[str] = mapped_column(
        String(8), nullable=False, default="MEDIUM"
    )
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_outcome: Mapped[str | None] = mapped_column(
        String(512), nullable=True
    )
    success_metric: Mapped[str | None] = mapped_column(
        String(256), nullable=True
    )
    details: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, default=None
    )

    # ── Timestamp ─────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # ── Relationships ──────────────────────────────────────────────────
    creator_profile: Mapped["CreatorProfile"] = relationship("CreatorProfile")
    source_claim: Mapped["PipelineClaim"] = relationship("PipelineClaim")

    __table_args__ = (
        Index(
            "ix_pipeline_recommendations_creator_claim",
            "creator_profile_id", "source_claim_id",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<PipelineRecommendation id={self.id} "
            f"priority={self.priority} title={self.title[:50]}>"
        )
