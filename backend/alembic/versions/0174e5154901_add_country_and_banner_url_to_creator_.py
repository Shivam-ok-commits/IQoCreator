"""add country and banner_url to creator_profiles

Revision ID: 0174e5154901
Revises: 0002
Create Date: 2026-07-17 11:56:09.826937
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0174e5154901'
down_revision: str | None = '0002'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('creator_profiles', sa.Column('country', sa.String(length=4), nullable=True))
    op.add_column('creator_profiles', sa.Column('banner_url', sa.String(length=1024), nullable=True))


def downgrade() -> None:
    op.drop_column('creator_profiles', 'banner_url')
    op.drop_column('creator_profiles', 'country')
