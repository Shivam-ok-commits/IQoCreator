"""RecommendationFeedback model."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, TimestampMixin, uuid_pk


class RecommendationFeedback(TimestampMixin, Base):
    """User feedback on whether a recommendation was applied and how useful it was."""

    __tablename__ = "recommendation_feedback"

    id: Mapped[uuid.UUID] = uuid_pk()
    recommendation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recommendations.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1-5 scale
    helpful: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    implemented: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    applied_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Relationships ────────────────────────────────────────────────────
    recommendation: Mapped["Recommendation"] = relationship(
        "Recommendation", back_populates="feedback"
    )

    def __repr__(self) -> str:
        return f"<RecommendationFeedback id={self.id} helpful={self.helpful}>"
