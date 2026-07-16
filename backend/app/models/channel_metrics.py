"""ChannelMetrics model."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, TimestampMixin, uuid_pk


class ChannelMetrics(TimestampMixin, Base):
    """Time-series snapshot of a creator's channel performance."""

    __tablename__ = "channel_metrics"

    id: Mapped[uuid.UUID] = uuid_pk()
    creator_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("creator_profiles.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    subscriber_count: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    total_views: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    total_videos: Mapped[int | None] = mapped_column(Integer, nullable=True)
    avg_view_duration_seconds: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )

    # ── Relationships ────────────────────────────────────────────────────
    creator_profile: Mapped["CreatorProfile"] = relationship(
        "CreatorProfile", back_populates="channel_metrics"
    )

    def __repr__(self) -> str:
        return f"<ChannelMetrics id={self.id} recorded_at={self.recorded_at}>"
