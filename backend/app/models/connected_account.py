"""ConnectedAccount model."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, TimestampMixin, uuid_pk


class ConnectedAccount(TimestampMixin, Base):
    """An OAuth or API-key-based external account linked to a user."""

    __tablename__ = "connected_accounts"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider: Mapped[str] = mapped_column(
        String(64), nullable=False  # e.g. "google", "youtube"
    )
    provider_account_id: Mapped[str] = mapped_column(String(256), nullable=False)
    access_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    scope: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # ── Relationships ────────────────────────────────────────────────────
    user: Mapped["User"] = relationship("User", back_populates="connected_accounts")

    __table_args__ = (
        Index(
            "ix_connected_accounts_provider_provider_id",
            "provider", "provider_account_id",
            unique=True,
        ),
    )

    def __repr__(self) -> str:
        return f"<ConnectedAccount id={self.id} provider={self.provider}>"
