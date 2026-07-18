"""add channel_reports table for executive summaries

Revision ID: 0008
Revises: 0007
Create Date: 2026-07-19
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "channel_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("creator_profile_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("creator_profiles.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("analysis_run_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("analysis_runs.id", ondelete="SET NULL"),
                  nullable=True),
        sa.Column("version", sa.Integer(), default=1, nullable=False),
        sa.Column("thesis", sa.Text(), nullable=False),
        sa.Column("biggest_opportunity", sa.Text(), nullable=False),
        sa.Column("biggest_risk", sa.Text(), nullable=False),
        sa.Column("what_surprised_us", sa.Text(), nullable=True),
        sa.Column("next_30_day_goal", sa.String(512), nullable=False),
        sa.Column("channel_story", sa.Text(), nullable=True),
        sa.Column("recommendation_ids", postgresql.JSONB(),
                  default=list, nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("channel_reports")
