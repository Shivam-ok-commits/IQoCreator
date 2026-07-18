"""MetricFeatureVector model — channel-level feature vector derived from a MetricSnapshot.

Produced by FeatureExtractionStage. Never mutated after creation.
One vector per MetricSnapshot. Idempotent on source_snapshot_id.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, uuid_pk


class MetricFeatureVector(Base):
    """Immutable channel-level feature vector derived from a MetricSnapshot.

    Contains deterministic features (upload frequency, engagement rate,
    shorts ratio, etc.) used as input to the Rule Engine.
    One vector per MetricSnapshot — never updated in place.
    """

    __tablename__ = "metric_feature_vectors"

    id: Mapped[uuid.UUID] = uuid_pk()
    creator_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("creator_profiles.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    source_snapshot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("metric_snapshots.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True,
    )
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )

    # ── Feature payload ───────────────────────────────────────────────
    features: Mapped[dict] = mapped_column(JSONB, nullable=False)

    # ── Versioning ────────────────────────────────────────────────────
    feature_schema_version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1
    )
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1
    )

    # ── Relationships ──────────────────────────────────────────────────
    creator_profile: Mapped["CreatorProfile"] = relationship(
        "CreatorProfile"
    )
    source_snapshot: Mapped["MetricSnapshot"] = relationship(
        "MetricSnapshot"
    )

    __table_args__ = (
        Index("ix_metric_feature_vectors_creator_snapshot", "creator_profile_id", "source_snapshot_id"),
    )

    def __repr__(self) -> str:
        return f"<MetricFeatureVector id={self.id} source_snapshot={self.source_snapshot_id}>"
