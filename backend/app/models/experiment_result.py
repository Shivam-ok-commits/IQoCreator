"""ExperimentResult model."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, TimestampMixin, uuid_pk


class ExperimentResult(TimestampMixin, Base):
    """A single metric collected during an experiment."""

    __tablename__ = "experiment_results"

    id: Mapped[uuid.UUID] = uuid_pk()
    experiment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("experiments.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    metric_name: Mapped[str] = mapped_column(String(128), nullable=False)
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Relationships ────────────────────────────────────────────────────
    experiment: Mapped["Experiment"] = relationship(
        "Experiment", back_populates="results"
    )

    def __repr__(self) -> str:
        return f"<ExperimentResult id={self.id} metric={self.metric_name}>"
