"""AnalysisRun model."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, TimestampMixin, uuid_pk


class AnalysisRunStatus(str, PyEnum):
    """Possible states of an analysis run."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AnalysisRun(TimestampMixin, Base):
    """A single analysis operation that processes imported content.

    Runs rule executions, extracts claims, gathers evidence, and
    generates recommendations.
    """

    __tablename__ = "analysis_runs"

    id: Mapped[uuid.UUID] = uuid_pk()
    creator_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("creator_profiles.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    status: Mapped[AnalysisRunStatus] = mapped_column(
        String(16), nullable=False,
        default=AnalysisRunStatus.PENDING, index=True,
    )
    trigger: Mapped[str] = mapped_column(
        String(32), nullable=False, default="manual"
    )  # "manual", "scheduled", "post_import"
    pipeline_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    generator_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    claim_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    evidence_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rule_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Relationships ────────────────────────────────────────────────────
    creator_profile: Mapped["CreatorProfile"] = relationship(
        "CreatorProfile", back_populates="analysis_runs"
    )
    rule_executions: Mapped[list["RuleExecution"]] = relationship(
        "RuleExecution", back_populates="analysis_run",
        cascade="all, delete-orphan",
    )
    evidence: Mapped[list["Evidence"]] = relationship(
        "Evidence", back_populates="analysis_run",
        cascade="all, delete-orphan",
    )
    claims: Mapped[list["Claim"]] = relationship(
        "Claim", back_populates="analysis_run",
        cascade="all, delete-orphan",
    )
    recommendations: Mapped[list["Recommendation"]] = relationship(
        "Recommendation", back_populates="analysis_run",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<AnalysisRun id={self.id} status={self.status}>"
