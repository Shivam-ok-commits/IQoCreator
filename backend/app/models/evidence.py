"""Evidence model."""

from __future__ import annotations

import uuid

from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, TimestampMixin, uuid_pk


class Evidence(TimestampMixin, Base):
    """A piece of evidence collected to support or refute a claim.

    Evidence can come from video transcripts, descriptions, or external
    sources. Linked to claims via the claim_evidence join table.
    """

    __tablename__ = "evidence"

    id: Mapped[uuid.UUID] = uuid_pk()
    analysis_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analysis_runs.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    source_type: Mapped[str] = mapped_column(
        String(32), nullable=False  # "transcript", "description", "external"
    )
    source_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    relevance_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    generator_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    extra_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # ── Relationships ────────────────────────────────────────────────────
    analysis_run: Mapped["AnalysisRun"] = relationship(
        "AnalysisRun", back_populates="evidence"
    )
    claims: Mapped[list["Claim"]] = relationship(
        "Claim", secondary="claim_evidence", back_populates="evidence"
    )

    def __repr__(self) -> str:
        return f"<Evidence id={self.id} source={self.source_type}>"
