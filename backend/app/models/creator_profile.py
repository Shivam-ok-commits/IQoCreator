"""CreatorProfile model."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, TimestampMixin, SoftDeleteMixin, uuid_pk


class CreatorProfile(TimestampMixin, SoftDeleteMixin, Base):
    """A content creator monitored by the platform.

    A profile may be linked to an authenticated user or discovered
    independently and later claimed.
    """

    __tablename__ = "creator_profiles"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    handle: Mapped[str | None] = mapped_column(String(128), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    thumbnail_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    platform: Mapped[str] = mapped_column(
        String(32), nullable=False, default="youtube"
    )
    platform_creator_id: Mapped[str] = mapped_column(String(128), nullable=False)
    subscriber_count: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    total_views: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    country: Mapped[str | None] = mapped_column(String(4), nullable=True)
    banner_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    joined_platform_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Relationships ────────────────────────────────────────────────────
    user: Mapped["User | None"] = relationship(
        "User", back_populates="creator_profiles"
    )
    channel_metrics: Mapped[list["ChannelMetrics"]] = relationship(
        "ChannelMetrics", back_populates="creator_profile",
        cascade="all, delete-orphan",
    )
    videos: Mapped[list["Video"]] = relationship(
        "Video", back_populates="creator_profile",
        cascade="all, delete-orphan",
    )
    import_runs: Mapped[list["ImportRun"]] = relationship(
        "ImportRun", back_populates="creator_profile",
        cascade="all, delete-orphan",
    )
    analysis_runs: Mapped[list["AnalysisRun"]] = relationship(
        "AnalysisRun", back_populates="creator_profile",
        cascade="all, delete-orphan",
    )
    recommendations: Mapped[list["Recommendation"]] = relationship(
        "Recommendation", back_populates="creator_profile",
        cascade="all, delete-orphan",
    )
    experiments: Mapped[list["Experiment"]] = relationship(
        "Experiment", back_populates="creator_profile",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index(
            "ix_creator_profiles_platform_creator",
            "platform", "platform_creator_id",
            unique=True,
        ),
    )

    def __repr__(self) -> str:
        return f"<CreatorProfile id={self.id} name={self.name}>"
