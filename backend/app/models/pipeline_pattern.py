"""PipelinePattern model — rich intelligence pattern produced by Creator Intelligence Engine."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, uuid_pk


class PipelinePattern(Base):
    """A structured pattern extracted from video-level intelligence.

    Produced by the Creator Intelligence Engine's extractors
    (TopicClusterExtractor, SeriesPatternExtractor, TitlePatternExtractor).
    Each pattern represents a data-backed observation about creator
    performance that can drive recommendations.
    """

    __tablename__ = "pipeline_patterns"

    id: Mapped[uuid.UUID] = uuid_pk()
    creator_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("creator_profiles.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    pattern_type: Mapped[str] = mapped_column(
        String(32), nullable=False, index=True
    )
    summary: Mapped[str] = mapped_column(String(256), nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    impact: Mapped[float] = mapped_column(Float, nullable=False)
    impact_score: Mapped[float] = mapped_column(Float, nullable=False)
    metrics: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    evidence: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    suggested_actions: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    creator_profile: Mapped["CreatorProfile"] = relationship("CreatorProfile")

    def __repr__(self) -> str:
        return (
            f"<PipelinePattern id={self.id} "
            f"type={self.pattern_type} score={self.impact_score:.2f}>"
        )
