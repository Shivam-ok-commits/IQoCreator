"""add details JSONB column to pipeline_recommendations

Revision ID: 0007
Revises: 0006
Create Date: 2026-07-18
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "pipeline_recommendations",
        sa.Column("details", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("pipeline_recommendations", "details")
