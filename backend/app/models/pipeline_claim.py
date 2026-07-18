"""PipelineClaim model — immutable claim artifact produced by ClaimEngine.

One claim per PipelineEvidence. A claim is the canonical, human-readable
conclusion derived from evidence. Consumed by RecommendationEngine.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, uuid_pk


class PipelineClaim(Base):
    """Immutable claim artifact that represents a conclusion from evidence.

    Produced by ClaimEngine. One claim per PipelineEvidence.
    Never mutated after creation.
    """

    __tablename__ = "pipeline_claims"

    id: Mapped[uuid.UUID] = uuid_pk()
    creator_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("creator_profiles.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    source_evidence_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pipeline_evidence.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True,
    )

    # ── Claim content ─────────────────────────────────────────────────
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(
        String(8), nullable=False, default="INFO"
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    summary: Mapped[str] = mapped_column(String(512), nullable=False)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Supporting references ─────────────────────────────────────────
    supporting_evidence_ids: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )

    # ── Timestamp ─────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # ── Relationships ──────────────────────────────────────────────────
    creator_profile: Mapped["CreatorProfile"] = relationship("CreatorProfile")
    source_evidence: Mapped["PipelineEvidence"] = relationship("PipelineEvidence")

    __table_args__ = (
        Index(
            "ix_pipeline_claims_creator_evidence",
            "creator_profile_id", "source_evidence_id",
        ),
    )

    def __repr__(self) -> str:
        return f"<PipelineClaim id={self.id} category={self.category} severity={self.severity}>"
