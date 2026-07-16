"""Refine schema — apply Sprint 2 feedback changes.

Changes:
1. Split models into individual files (no DB impact)
2. Create claim_evidence join table (many-to-many Claim ↔ Evidence)
3. Add analysis_runs.pipeline_metadata JSONB
4. Add analysis_runs.generator_version
5. Add rule_executions.started_at, finished_at
6. Rename evidence.metadata → evidence.extra_data
7. Add evidence.generator_version
8. Add claims.generator_version
9. Add recommendations.generator_version
10. Update recommendation_feedback: add helpful, implemented, drop applied
11. Add experiments.recommendation_id FK
12. Update recommendation status enum values

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-16
"""
from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Apply 0002 — refine schema."""

    # ── 2. Claim-Evidence join table ──────────────────────────────────────
    op.create_table(
        "claim_evidence",
        sa.Column("claim_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("claims.id", ondelete="CASCADE"),
                  primary_key=True),
        sa.Column("evidence_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("evidence.id", ondelete="CASCADE"),
                  primary_key=True),
    )

    # Remove old claim_id FK from evidence (now many-to-many via join table)
    op.drop_constraint("fk_evidence_claim_id_claims", "evidence", type_="foreignkey")
    op.drop_index("ix_evidence_claim_id", table_name="evidence")
    op.drop_column("evidence", "claim_id")

    # ── 3. AnalysisRun: pipeline_metadata, generator_version ──────────────
    op.add_column("analysis_runs", sa.Column("pipeline_metadata", postgresql.JSONB(),
                  nullable=True))
    op.add_column("analysis_runs", sa.Column("generator_version", sa.String(32),
                  nullable=True))

    # ── 5. RuleExecution: started_at, finished_at ─────────────────────────
    op.add_column("rule_executions", sa.Column("started_at",
                  sa.DateTime(timezone=True), nullable=True))
    op.add_column("rule_executions", sa.Column("finished_at",
                  sa.DateTime(timezone=True), nullable=True))

    # ── 6. Evidence: rename metadata → extra_data, add generator_version ──
    op.add_column("evidence", sa.Column("extra_data", postgresql.JSONB(),
                  nullable=True))
    op.add_column("evidence", sa.Column("generator_version", sa.String(32),
                  nullable=True))
    op.drop_column("evidence", "metadata")

    # ── 8. Claim: add generator_version ───────────────────────────────────
    op.add_column("claims", sa.Column("generator_version", sa.String(32),
                  nullable=True))

    # ── 9. Recommendation: add generator_version, rename metadata→extra_data ─
    op.add_column("recommendations", sa.Column("generator_version", sa.String(32),
                  nullable=True))
    op.add_column("recommendations", sa.Column("extra_data", postgresql.JSONB(),
                  nullable=True))
    op.drop_column("recommendations", "metadata")

    # ── 10. RecommendationFeedback: add helpful, implemented, drop applied ──
    op.add_column("recommendation_feedback", sa.Column("helpful", sa.Boolean(),
                  nullable=False, server_default=sa.text("false")))
    op.add_column("recommendation_feedback", sa.Column("implemented", sa.Boolean(),
                  nullable=False, server_default=sa.text("false")))
    op.drop_column("recommendation_feedback", "applied")

    # ── 11. Experiment: add recommendation_id FK ───────────────────────────
    op.add_column("experiments", sa.Column("recommendation_id",
                  postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("recommendations.id", ondelete="SET NULL"),
                  nullable=True, index=True))

    # ── 12. Recommendation status values: updated in model enum only ───────
    # No DB migration needed — status is stored as String(16).
    # The Python enum now only allows: draft, reviewed, approved, rejected, archived.
    # Existing rows with old values (active, dismissed, implemented) remain
    # readable; new writes use the new enum.


def downgrade() -> None:
    """Revert 0002 — return to old schema."""

    # ── 11. Experiment: remove recommendation_id FK ────────────────────────
    op.drop_index("ix_experiments_recommendation_id", table_name="experiments")
    op.drop_constraint("fk_experiments_recommendation_id_recommendations",
                       "experiments", type_="foreignkey")
    op.drop_column("experiments", "recommendation_id")

    # ── 10. RecommendationFeedback: drop helpful, implemented, restore applied ──
    op.add_column("recommendation_feedback", sa.Column("applied", sa.Boolean(),
                   nullable=False, server_default=sa.text("false")))
    op.drop_column("recommendation_feedback", "implemented")
    op.drop_column("recommendation_feedback", "helpful")

    # ── 9. Recommendation: drop generator_version, restore metadata ────────
    op.add_column("recommendations", sa.Column("metadata", postgresql.JSONB(),
                  nullable=True))
    op.drop_column("recommendations", "extra_data")
    op.drop_column("recommendations", "generator_version")

    # ── 8. Claim: drop generator_version ───────────────────────────────────
    op.drop_column("claims", "generator_version")

    # ── 6. Evidence: drop extra_data, generator_version, restore metadata ──
    op.add_column("evidence", sa.Column("metadata", postgresql.JSONB(),
                  nullable=True))
    op.drop_column("evidence", "generator_version")
    op.drop_column("evidence", "extra_data")

    # ── 5. RuleExecution: drop started_at, finished_at ─────────────────────
    op.drop_column("rule_executions", "finished_at")
    op.drop_column("rule_executions", "started_at")

    # ── 3. AnalysisRun: drop pipeline_metadata, generator_version ──────────
    op.drop_column("analysis_runs", "generator_version")
    op.drop_column("analysis_runs", "pipeline_metadata")

    # ── 2. Claim-Evidence join table: restore claim_id FK on evidence ─────
    op.add_column("evidence", sa.Column("claim_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("claims.id", ondelete="SET NULL"),
                  nullable=True, index=True))

    op.drop_table("claim_evidence")
