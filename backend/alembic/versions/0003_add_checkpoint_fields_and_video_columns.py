"""add checkpoint fields to import_runs and columns to videos

Revision ID: c56163e9fc95
Revises: 0174e5154901
Create Date: 2026-07-17 12:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision: str = 'c56163e9fc95'
down_revision: str | None = '0174e5154901'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ImportRun checkpoint columns
    op.add_column('import_runs', sa.Column('last_page_token', sa.String(length=512), nullable=True))
    op.add_column('import_runs', sa.Column('total_count', sa.Integer(), nullable=True))
    op.add_column('import_runs', sa.Column('processed_count', sa.Integer(), nullable=True))
    op.add_column('import_runs', sa.Column('checkpoint_data', JSONB(), nullable=True))

    # Video columns
    op.add_column('videos', sa.Column('privacy_status', sa.String(length=16), nullable=True))
    op.add_column('videos', sa.Column('category_id', sa.String(length=8), nullable=True))


def downgrade() -> None:
    op.drop_column('videos', 'category_id')
    op.drop_column('videos', 'privacy_status')
    op.drop_column('import_runs', 'checkpoint_data')
    op.drop_column('import_runs', 'processed_count')
    op.drop_column('import_runs', 'total_count')
    op.drop_column('import_runs', 'last_page_token')
