"""Video model."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, TimestampMixin, SoftDeleteMixin, uuid_pk


class Video(TimestampMixin, SoftDeleteMixin, Base):
    """A video published by a creator, imported from YouTube or another platform."""

    __tablename__ = "videos"

    id: Mapped[uuid.UUID] = uuid_pk()
    creator_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("creator_profiles.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    platform_video_id: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, index=True
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    thumbnail_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    privacy_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    category_id: Mapped[str | None] = mapped_column(String(8), nullable=True)
    tags: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Relationships ────────────────────────────────────────────────────
    creator_profile: Mapped["CreatorProfile"] = relationship(
        "CreatorProfile", back_populates="videos"
    )
    metrics: Mapped[list["VideoMetrics"]] = relationship(
        "VideoMetrics", back_populates="video",
        cascade="all, delete-orphan",
    )
    feature_vectors: Mapped[list["FeatureVector"]] = relationship(
        "FeatureVector", back_populates="video",
        cascade="all, delete-orphan",
    )
    claims: Mapped[list["Claim"]] = relationship(
        "Claim", back_populates="video",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Video id={self.id} title={self.title[:50]}>"
