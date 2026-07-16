"""RuleExecution model."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, uuid_pk


class RuleExecutionStatus(str, PyEnum):
    """Outcome of a single rule execution."""

    SUCCESS = "success"
    FAILURE = "failure"
    ERROR = "error"


class RuleExecution(Base):
    """The result of applying a single rule during an analysis run.

    Input snapshots and outputs are stored as JSONB because rules are
    heterogeneous — each rule defines its own input and output shape.
    """

    __tablename__ = "rule_executions"

    id: Mapped[uuid.UUID] = uuid_pk()
    analysis_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analysis_runs.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    rule_name: Mapped[str] = mapped_column(String(128), nullable=False)
    rule_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    input_snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    output: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[RuleExecutionStatus] = mapped_column(
        String(16), nullable=False, default=RuleExecutionStatus.SUCCESS,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # ── Relationships ────────────────────────────────────────────────────
    analysis_run: Mapped["AnalysisRun"] = relationship(
        "AnalysisRun", back_populates="rule_executions"
    )

    def __repr__(self) -> str:
        return f"<RuleExecution id={self.id} rule={self.rule_name}>"
