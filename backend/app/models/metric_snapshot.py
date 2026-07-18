"""MetricSnapshot model — immutable historical snapshot of channel metrics."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Index, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, TimestampMixin, uuid_pk


class MetricSnapshot(TimestampMixin, Base):
    """Immutable snapshot of a creator's channel and video metrics at a point in time.

    Produced by MetricsCollectionStage. Never mutated after creation.
    Idempotent on (creator_profile_id, snapshot_at).
    """

    __tablename__ = "metric_snapshots"

    id: Mapped[uuid.UUID] = uuid_pk()
    creator_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("creator_profiles.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    snapshot_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True,
    )
    source_import_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("import_runs.id", ondelete="SET NULL"),
        nullable=True,
    )

    # ── Channel-level metrics ──────────────────────────────────────────
    total_videos: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_views: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    total_subscribers: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    avg_views_per_video: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_view_duration_seconds: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    total_watch_time_hours: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    engagement_rate: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ── Schema versioning ──────────────────────────────────────────────
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1
    )

    # ── Relationships ──────────────────────────────────────────────────
    creator_profile: Mapped["CreatorProfile"] = relationship(
        "CreatorProfile", back_populates="metric_snapshots"
    )

    __table_args__ = (
        Index(
            "ix_metric_snapshots_creator_snapshot",
            "creator_profile_id", "snapshot_at",
            unique=True,
        ),
    )

    def __repr__(self) -> str:
        return f"<MetricSnapshot id={self.id} snapshot_at={self.snapshot_at}>"
