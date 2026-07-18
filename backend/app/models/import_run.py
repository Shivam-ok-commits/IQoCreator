"""ImportRun model."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, TimestampMixin, uuid_pk


class ImportRunStatus(str, PyEnum):
    """Possible states of an import run."""

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    FAILED = "failed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ImportRun(TimestampMixin, Base):
    """A single import operation that fetches videos from a creator."""

    __tablename__ = "import_runs"

    id: Mapped[uuid.UUID] = uuid_pk()
    creator_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("creator_profiles.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    status: Mapped[ImportRunStatus] = mapped_column(
        String(16), nullable=False,
        default=ImportRunStatus.PENDING, index=True,
    )
    source: Mapped[str] = mapped_column(
        String(32), nullable=False, default="youtube_api"
    )
    videos_imported: Mapped[int | None] = mapped_column(Integer, nullable=True)
    videos_failed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_page_token: Mapped[str | None] = mapped_column(
        String(512), nullable=True
    )
    total_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    processed_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    checkpoint_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # ── Relationships ────────────────────────────────────────────────────
    creator_profile: Mapped["CreatorProfile"] = relationship(
        "CreatorProfile", back_populates="import_runs"
    )

    def __repr__(self) -> str:
        return f"<ImportRun id={self.id} status={self.status}>"
