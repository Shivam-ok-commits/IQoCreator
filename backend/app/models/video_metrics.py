"""VideoMetrics model."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, TimestampMixin, uuid_pk


class VideoMetrics(TimestampMixin, Base):
    """Time-series snapshot of a video's engagement metrics."""

    __tablename__ = "video_metrics"

    id: Mapped[uuid.UUID] = uuid_pk()
    video_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("videos.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    view_count: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    like_count: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    comment_count: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    share_count: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    # ── Relationships ────────────────────────────────────────────────────
    video: Mapped["Video"] = relationship("Video", back_populates="metrics")

    __table_args__ = (
        Index("ix_video_metrics_video_recorded", "video_id", "recorded_at"),
    )

    def __repr__(self) -> str:
        return f"<VideoMetrics id={self.id} recorded_at={self.recorded_at}>"
