"""PipelineExperiment model — immutable experiment artifact produced by LearningEngine.

One experiment per recommendation. Tracks the hypothesis and expected
outcome for measuring recommendation effectiveness.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, uuid_pk


class PipelineExperimentStatus(str, PyEnum):
    """Lifecycle status of a pipeline experiment."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PipelineExperiment(Base):
    """Immutable experiment record derived from a recommendation.

    Produced by LearningEngine. One per PipelineRecommendation.
    Never mutated — success/failure is tracked via separate results.
    """

    __tablename__ = "pipeline_experiments"

    id: Mapped[uuid.UUID] = uuid_pk()
    creator_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("creator_profiles.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    source_recommendation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pipeline_recommendations.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True,
    )

    # ── Experiment content ────────────────────────────────────────────
    hypothesis: Mapped[str] = mapped_column(Text, nullable=False)
    success_metric: Mapped[str | None] = mapped_column(
        String(256), nullable=True
    )
    expected_outcome: Mapped[str | None] = mapped_column(
        String(512), nullable=True
    )

    # ── Status ────────────────────────────────────────────────────────
    status: Mapped[PipelineExperimentStatus] = mapped_column(
        String(16), nullable=False,
        default=PipelineExperimentStatus.PENDING, index=True
    )

    # ── Timestamps ────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # ── Relationships ──────────────────────────────────────────────────
    creator_profile: Mapped["CreatorProfile"] = relationship("CreatorProfile")
    source_recommendation: Mapped["PipelineRecommendation"] = relationship(
        "PipelineRecommendation"
    )

    __table_args__ = (
        Index(
            "ix_pipeline_experiments_creator_rec",
            "creator_profile_id", "source_recommendation_id",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<PipelineExperiment id={self.id} "
            f"status={self.status} hypothesis={self.hypothesis[:50]}>"
        )
