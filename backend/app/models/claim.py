"""Claim model."""

from __future__ import annotations

import uuid
from enum import Enum as PyEnum

from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, TimestampMixin, SoftDeleteMixin, uuid_pk


class ClaimStatus(str, PyEnum):
    """Verification status of a claim."""

    UNVERIFIED = "unverified"
    VERIFIED = "verified"
    DEBUNKED = "debunked"
    UNCERTAIN = "uncertain"


class Claim(TimestampMixin, SoftDeleteMixin, Base):
    """A specific statement extracted from a video that may need verification."""

    __tablename__ = "claims"

    id: Mapped[uuid.UUID] = uuid_pk()
    analysis_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analysis_runs.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    video_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("videos.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    claim_type: Mapped[str | None] = mapped_column(
        String(32), nullable=True  # "factual", "opinion", "prediction"
    )
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    generator_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[ClaimStatus] = mapped_column(
        String(16), nullable=False,
        default=ClaimStatus.UNVERIFIED, index=True,
    )

    # ── Relationships ────────────────────────────────────────────────────
    analysis_run: Mapped["AnalysisRun"] = relationship(
        "AnalysisRun", back_populates="claims"
    )
    video: Mapped["Video"] = relationship("Video", back_populates="claims")
    evidence: Mapped[list["Evidence"]] = relationship(
        "Evidence", secondary="claim_evidence", back_populates="claims"
    )
    recommendations: Mapped[list["Recommendation"]] = relationship(
        "Recommendation", back_populates="claim",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Claim id={self.id} status={self.status}>"
