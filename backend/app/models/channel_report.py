"""ChannelReport model — executive summary of a completed analysis pipeline run."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, TimestampMixin, uuid_pk


class ChannelReport(TimestampMixin, Base):
    """A narrative executive summary of the channel after a full analysis run.

    Unlike raw metrics or individual recommendations, this report synthesises
    the most important patterns into a coherent story for the creator.
    """

    __tablename__ = "channel_reports"

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

    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    thesis: Mapped[str] = mapped_column(Text, nullable=False)
    biggest_opportunity: Mapped[str] = mapped_column(Text, nullable=False)
    biggest_risk: Mapped[str] = mapped_column(Text, nullable=False)
    what_surprised_us: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_30_day_goal: Mapped[str] = mapped_column(String(512), nullable=False)
    channel_story: Mapped[str | None] = mapped_column(Text, nullable=True)

    recommendation_ids: Mapped[list] = mapped_column(
        JSONB, default=list, nullable=False,
    )

    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
    )

    def __repr__(self) -> str:
        return f"<ChannelReport id={self.id} version={self.version}>"
