"""Experiment model."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, TimestampMixin, uuid_pk


class ExperimentStatus(str, PyEnum):
    """Lifecycle status of an experiment."""

    DRAFT = "draft"
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Experiment(TimestampMixin, Base):
    """A controlled experiment testing a hypothesis on a creator's content.

    Each experiment is optionally linked to the recommendation it
    originated from.
    """

    __tablename__ = "experiments"

    id: Mapped[uuid.UUID] = uuid_pk()
    creator_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("creator_profiles.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    recommendation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recommendations.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    hypothesis: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ExperimentStatus] = mapped_column(
        String(16), nullable=False,
        default=ExperimentStatus.DRAFT, index=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Relationships ────────────────────────────────────────────────────
    creator_profile: Mapped["CreatorProfile"] = relationship(
        "CreatorProfile", back_populates="experiments"
    )
    recommendation: Mapped["Recommendation | None"] = relationship(
        "Recommendation"
    )
    results: Mapped[list["ExperimentResult"]] = relationship(
        "ExperimentResult", back_populates="experiment",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Experiment id={self.id} name={self.name}>"
