"""Finding model — immutable rule evaluation result.

Produced by RuleEngine. One finding per rule trigger event.
Never mutated after creation.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, uuid_pk


class Finding(Base):
    """An immutable finding produced by a rule evaluation.

    Each finding represents one triggered rule against one FeatureVector.
    Findings are never updated — historical findings are always preserved.
    """

    __tablename__ = "findings"

    id: Mapped[uuid.UUID] = uuid_pk()
    creator_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("creator_profiles.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    source_feature_vector_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("metric_feature_vectors.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    # ── Rule identity ─────────────────────────────────────────────────
    rule_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # ── Finding content ───────────────────────────────────────────────
    severity: Mapped[str] = mapped_column(
        String(8), nullable=False, default="INFO"
    )
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # ── Timestamp ─────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # ── Relationships ──────────────────────────────────────────────────
    creator_profile: Mapped["CreatorProfile"] = relationship("CreatorProfile")
    source_feature_vector: Mapped["MetricFeatureVector"] = relationship(
        "MetricFeatureVector"
    )

    __table_args__ = (
        Index(
            "ix_findings_creator_rule",
            "creator_profile_id", "rule_id",
        ),
        Index(
            "ix_findings_feature_vector",
            "source_feature_vector_id",
        ),
    )

    def __repr__(self) -> str:
        return f"<Finding id={self.id} rule={self.rule_id} severity={self.severity}>"
