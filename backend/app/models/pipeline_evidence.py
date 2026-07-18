"""PipelineEvidence model — immutable evidence artifact produced by EvidenceEngine.

One evidence per Finding. Links the finding to its supporting data
and provides a deterministic confidence score.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, uuid_pk


class PipelineEvidence(Base):
    """Immutable evidence artifact that enriches a Finding with supporting data.

    Produced by EvidenceEngine. One evidence per Finding.
    Never mutated after creation.
    """

    __tablename__ = "pipeline_evidence"

    id: Mapped[uuid.UUID] = uuid_pk()
    creator_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("creator_profiles.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    source_finding_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("findings.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True,
    )
    source_feature_vector_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("metric_feature_vectors.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    # ── Rule linkage ──────────────────────────────────────────────────
    source_rule_id: Mapped[str] = mapped_column(String(64), nullable=False)

    # ── Confidence scoring ────────────────────────────────────────────
    confidence: Mapped[float] = mapped_column(Float, nullable=False)

    # ── Evidence content ──────────────────────────────────────────────
    supporting_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Timestamp ─────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # ── Relationships ──────────────────────────────────────────────────
    creator_profile: Mapped["CreatorProfile"] = relationship("CreatorProfile")
    source_finding: Mapped["Finding"] = relationship("Finding")

    __table_args__ = (
        Index(
            "ix_pipeline_evidence_creator_finding",
            "creator_profile_id", "source_finding_id",
        ),
    )

    def __repr__(self) -> str:
        return f"<PipelineEvidence id={self.id} rule={self.source_rule_id} confidence={self.confidence}>"
