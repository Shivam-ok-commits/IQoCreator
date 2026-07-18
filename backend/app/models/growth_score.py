"""GrowthScore model — snapshot of channel growth health after analysis."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, TimestampMixin, uuid_pk


class GrowthScore(TimestampMixin, Base):
    """A point-in-time snapshot of the channel's growth health.

    Persisted after every completed analysis pipeline run so the
    frontend can show score history and deltas over time.
    """

    __tablename__ = "growth_scores"

    id: Mapped[uuid.UUID] = uuid_pk()
    creator_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("creator_profiles.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    analysis_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analysis_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    tier: Mapped[str] = mapped_column(String(32), nullable=False)
    summary: Mapped[str | None] = mapped_column(String(512), nullable=True)
    potential_low: Mapped[int | None] = mapped_column(Integer, nullable=True)
    potential_high: Mapped[int | None] = mapped_column(Integer, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    def __repr__(self) -> str:
        return f"<GrowthScore id={self.id} score={self.score} tier={self.tier}>"
