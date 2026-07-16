"""FeatureVector model."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, uuid_pk


class FeatureVector(Base):
    """Computed feature vector for a video — topics, sentiment, toxicity, etc.

    JSONB is justified because feature vectors are heterogeneous in shape:
    different feature types produce different keys and depths.
    """

    __tablename__ = "feature_vectors"

    id: Mapped[uuid.UUID] = uuid_pk()
    video_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("videos.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    feature_type: Mapped[str] = mapped_column(
        String(64), nullable=False  # e.g. "topic", "sentiment", "toxicity"
    )
    vector: Mapped[dict] = mapped_column(JSONB, nullable=False)
    model_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # ── Relationships ────────────────────────────────────────────────────
    video: Mapped["Video"] = relationship("Video", back_populates="feature_vectors")

    __table_args__ = (
        Index("ix_feature_vectors_video_type", "video_id", "feature_type"),
    )

    def __repr__(self) -> str:
        return f"<FeatureVector id={self.id} type={self.feature_type}>"
