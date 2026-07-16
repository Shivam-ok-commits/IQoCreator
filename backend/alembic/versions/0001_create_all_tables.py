"""Initial migration — create all tables.

Revision ID: 0001
Revises: None
Create Date: 2026-07-16
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create all 15 tables."""

    # ── Identity ──────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False, index=True),
        sa.Column("display_name", sa.String(128), nullable=True),
        sa.Column("avatar_url", sa.String(1024), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False,
                  server_default=sa.text("true")),
        sa.Column("is_superuser", sa.Boolean(), nullable=False,
                  server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("is_deleted", sa.Boolean(), nullable=False,
                  server_default=sa.text("false")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_unique_constraint("uq_users_email", "users", ["email"])

    op.create_table(
        "connected_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("provider_account_id", sa.String(256), nullable=False),
        sa.Column("access_token", sa.Text(), nullable=True),
        sa.Column("refresh_token", sa.Text(), nullable=True),
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scope", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )
    op.create_index(
        "ix_connected_accounts_provider_provider_id",
        "connected_accounts", ["provider", "provider_account_id"],
        unique=True,
    )

    # ── Creator ───────────────────────────────────────────────────────────
    op.create_table(
        "creator_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"),
                  nullable=True, index=True),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("handle", sa.String(128), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("thumbnail_url", sa.String(1024), nullable=True),
        sa.Column("platform", sa.String(32), nullable=False,
                  server_default=sa.text("'youtube'")),
        sa.Column("platform_creator_id", sa.String(128), nullable=False),
        sa.Column("subscriber_count", sa.BigInteger(), nullable=True),
        sa.Column("total_views", sa.BigInteger(), nullable=True),
        sa.Column("joined_platform_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("is_deleted", sa.Boolean(), nullable=False,
                  server_default=sa.text("false")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_creator_profiles_platform_creator",
        "creator_profiles", ["platform", "platform_creator_id"],
        unique=True,
    )

    op.create_table(
        "channel_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("creator_profile_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("creator_profiles.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False,
                  index=True),
        sa.Column("subscriber_count", sa.BigInteger(), nullable=True),
        sa.Column("total_views", sa.BigInteger(), nullable=True),
        sa.Column("total_videos", sa.Integer(), nullable=True),
        sa.Column("avg_view_duration_seconds", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )

    # ── Content ───────────────────────────────────────────────────────────
    op.create_table(
        "videos",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("creator_profile_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("creator_profiles.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("platform_video_id", sa.String(64), nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("thumbnail_url", sa.String(1024), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True,
                  index=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("url", sa.String(1024), nullable=True),
        sa.Column("language", sa.String(16), nullable=True),
        sa.Column("tags", postgresql.JSONB(), nullable=True),
        sa.Column("transcript", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("is_deleted", sa.Boolean(), nullable=False,
                  server_default=sa.text("false")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_unique_constraint("uq_videos_platform_video_id", "videos", ["platform_video_id"])

    op.create_table(
        "video_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("video_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("videos.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False,
                  index=True),
        sa.Column("view_count", sa.BigInteger(), nullable=True),
        sa.Column("like_count", sa.BigInteger(), nullable=True),
        sa.Column("comment_count", sa.BigInteger(), nullable=True),
        sa.Column("share_count", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )
    op.create_index("ix_video_metrics_video_recorded", "video_metrics",
                    ["video_id", "recorded_at"])

    op.create_table(
        "feature_vectors",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("video_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("videos.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("feature_type", sa.String(64), nullable=False),
        sa.Column("vector", postgresql.JSONB(), nullable=False),
        sa.Column("model_version", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )
    op.create_index("ix_feature_vectors_video_type", "feature_vectors",
                    ["video_id", "feature_type"])

    # ── Pipeline ──────────────────────────────────────────────────────────
    op.create_table(
        "import_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("creator_profile_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("creator_profiles.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("status", sa.String(16), nullable=False,
                  server_default=sa.text("'pending'"), index=True),
        sa.Column("source", sa.String(32), nullable=False,
                  server_default=sa.text("'youtube_api'")),
        sa.Column("videos_imported", sa.Integer(), nullable=True),
        sa.Column("videos_failed", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )

    op.create_table(
        "analysis_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("creator_profile_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("creator_profiles.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("status", sa.String(16), nullable=False,
                  server_default=sa.text("'pending'"), index=True),
        sa.Column("trigger", sa.String(32), nullable=False,
                  server_default=sa.text("'manual'")),
        sa.Column("claim_count", sa.Integer(), nullable=True),
        sa.Column("evidence_count", sa.Integer(), nullable=True),
        sa.Column("rule_count", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )

    # ── Intelligence ──────────────────────────────────────────────────────
    op.create_table(
        "claims",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("analysis_run_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("analysis_runs.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("video_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("videos.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("claim_type", sa.String(32), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False,
                  server_default=sa.text("'unverified'"), index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("is_deleted", sa.Boolean(), nullable=False,
                  server_default=sa.text("false")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "rule_executions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("analysis_run_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("analysis_runs.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("rule_name", sa.String(128), nullable=False),
        sa.Column("rule_version", sa.String(32), nullable=True),
        sa.Column("input_snapshot", postgresql.JSONB(), nullable=True),
        sa.Column("output", postgresql.JSONB(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False,
                  server_default=sa.text("'success'")),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )

    op.create_table(
        "recommendations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("analysis_run_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("analysis_runs.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("creator_profile_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("creator_profiles.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("claim_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("claims.id", ondelete="SET NULL"),
                  nullable=True),
        sa.Column("recommendation_type", sa.String(64), nullable=False),
        sa.Column("title", sa.String(256), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False,
                  server_default=sa.text("'draft'"), index=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )

    op.create_table(
        "evidence",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("analysis_run_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("analysis_runs.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("claim_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("claims.id", ondelete="SET NULL"),
                  nullable=True, index=True),
        sa.Column("source_type", sa.String(32), nullable=False),
        sa.Column("source_url", sa.String(1024), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("relevance_score", sa.Float(), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )

    # ── Validation ────────────────────────────────────────────────────────
    op.create_table(
        "experiments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("creator_profile_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("creator_profiles.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("hypothesis", sa.Text(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False,
                  server_default=sa.text("'draft'"), index=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )

    op.create_table(
        "experiment_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("experiment_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("experiments.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("metric_name", sa.String(128), nullable=False),
        sa.Column("metric_value", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(32), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )

    op.create_table(
        "recommendation_feedback",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("recommendation_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("recommendations.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("rating", sa.Integer(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("applied", sa.Boolean(), nullable=False,
                  server_default=sa.text("false")),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )


def downgrade() -> None:
    """Drop all tables in reverse dependency order."""
    op.drop_table("recommendation_feedback")
    op.drop_table("experiment_results")
    op.drop_table("experiments")
    op.drop_table("evidence")
    op.drop_table("recommendations")
    op.drop_table("rule_executions")
    op.drop_table("claims")
    op.drop_table("analysis_runs")
    op.drop_table("import_runs")
    op.drop_table("feature_vectors")
    op.drop_table("video_metrics")
    op.drop_table("videos")
    op.drop_table("channel_metrics")
    op.drop_table("creator_profiles")
    op.drop_table("connected_accounts")
    op.drop_table("users")
