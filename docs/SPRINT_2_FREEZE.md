# Sprint 2 Freeze — Database Schema Contract

> This document freezes the database schema produced by Sprint 2.
> Future sprints may **ADD** fields and tables.
> They may **NOT** rename or drop existing tables or columns without an explicit migration.
> This is the contract. Violations must be flagged during code review.

---

## Migration Order

The schema is applied in this exact order (migration `0001` → `0002`):

```
0001_create_all_tables.py  (baseline — 15 tables)
0002_refine_schema.py      (refinements — claim_evidence, new columns, renames)
```

**`0001` creates:** users, connected_accounts, creator_profiles, channel_metrics, videos, video_metrics, feature_vectors, import_runs, analysis_runs, rule_executions, evidence, claims, recommendations, recommendation_feedback, experiments, experiment_results

**`0002` modifies:** evidence (drop claim_id FK, add extra_data, add generator_version), claims (add generator_version), recommendations (add generator_version, rename metadata→extra_data), analysis_runs (add pipeline_metadata, generator_version), rule_executions (add started_at, finished_at), recommendation_feedback (add helpful, implemented, drop applied), experiments (add recommendation_id FK)

**`0002` creates:** claim_evidence (join table)

---

## Complete Table Inventory (16 tables)

| # | Table | Purpose | Sprint |
|---|-------|---------|--------|
| 1 | `users` | Platform users | 2 |
| 2 | `connected_accounts` | OAuth connections | 2 |
| 3 | `creator_profiles` | Content creators | 2 |
| 4 | `channel_metrics` | Channel time-series | 2 |
| 5 | `videos` | Imported videos | 2 |
| 6 | `video_metrics` | Video engagement time-series | 2 |
| 7 | `feature_vectors` | Computed ML features | 2 |
| 8 | `import_runs` | Import pipeline runs | 2 |
| 9 | `analysis_runs` | Analysis pipeline runs | 2 |
| 10 | `rule_executions` | Individual rule results | 2 |
| 11 | `evidence` | Supporting/refuting data | 2 |
| 12 | `claim_evidence` | Claim ↔ Evidence join | 2 |
| 13 | `claims` | Extracted statements | 2 |
| 14 | `recommendations` | Generated actions | 2 |
| 15 | `recommendation_feedback` | User feedback on recs | 2 |
| 16 | `experiment_results` | Experiment metrics | 2 |

---

## Complete Index Inventory (17 indexes)

| Table | Index | Type | Columns |
|-------|-------|------|---------|
| `users` | `ix_users_email` | UNIQUE | `email` |
| `connected_accounts` | `ix_connected_accounts_provider_provider_id` | UNIQUE | `provider`, `provider_account_id` |
| `connected_accounts` | `ix_connected_accounts_user_id` | STANDARD | `user_id` |
| `creator_profiles` | `ix_creator_profiles_platform_creator` | UNIQUE | `platform`, `platform_creator_id` |
| `creator_profiles` | `ix_creator_profiles_user_id` | STANDARD | `user_id` |
| `channel_metrics` | `ix_channel_metrics_creator_profile_id` | STANDARD | `creator_profile_id` |
| `channel_metrics` | `ix_channel_metrics_recorded_at` | STANDARD | `recorded_at` |
| `videos` | `ix_videos_platform_video_id` | UNIQUE | `platform_video_id` |
| `videos` | `ix_videos_creator_profile_id` | STANDARD | `creator_profile_id` |
| `videos` | `ix_videos_published_at` | STANDARD | `published_at` |
| `video_metrics` | `ix_video_metrics_video_recorded` | STANDARD | `video_id`, `recorded_at` |
| `video_metrics` | `ix_video_metrics_video_id` | STANDARD | `video_id` |
| `video_metrics` | `ix_video_metrics_recorded_at` | STANDARD | `recorded_at` |
| `feature_vectors` | `ix_feature_vectors_video_type` | STANDARD | `video_id`, `feature_type` |
| `feature_vectors` | `ix_feature_vectors_video_id` | STANDARD | `video_id` |
| `import_runs` | `ix_import_runs_creator_profile_id` | STANDARD | `creator_profile_id` |
| `import_runs` | `ix_import_runs_status` | STANDARD | `status` |
| `analysis_runs` | `ix_analysis_runs_creator_profile_id` | STANDARD | `creator_profile_id` |
| `analysis_runs` | `ix_analysis_runs_status` | STANDARD | `status` |
| `rule_executions` | `ix_rule_executions_analysis_run_id` | STANDARD | `analysis_run_id` |
| `evidence` | `ix_evidence_analysis_run_id` | STANDARD | `analysis_run_id` |
| `claims` | `ix_claims_analysis_run_id` | STANDARD | `analysis_run_id` |
| `claims` | `ix_claims_video_id` | STANDARD | `video_id` |
| `claims` | `ix_claims_status` | STANDARD | `status` |
| `recommendations` | `ix_recommendations_analysis_run_id` | STANDARD | `analysis_run_id` |
| `recommendations` | `ix_recommendations_creator_profile_id` | STANDARD | `creator_profile_id` |
| `recommendations` | `ix_recommendations_status` | STANDARD | `status` |
| `recommendation_feedback` | `ix_recommendation_feedback_recommendation_id` | STANDARD | `recommendation_id` |
| `experiments` | `ix_experiments_creator_profile_id` | STANDARD | `creator_profile_id` |
| `experiments` | `ix_experiments_status` | STANDARD | `status` |
| `experiments` | `ix_experiments_recommendation_id` | STANDARD | `recommendation_id` |
| `experiment_results` | `ix_experiment_results_experiment_id` | STANDARD | `experiment_id` |

---

## Complete Foreign Key Inventory (15 FKs)

| FK Name | From | To | Rule |
|---------|------|----|------|
| `fk_connected_accounts_user_id_users` | `connected_accounts.user_id` | `users.id` | CASCADE |
| `fk_creator_profiles_user_id_users` | `creator_profiles.user_id` | `users.id` | SET NULL |
| `fk_channel_metrics_creator_profile_id_creator_profiles` | `channel_metrics.creator_profile_id` | `creator_profiles.id` | CASCADE |
| `fk_videos_creator_profile_id_creator_profiles` | `videos.creator_profile_id` | `creator_profiles.id` | CASCADE |
| `fk_video_metrics_video_id_videos` | `video_metrics.video_id` | `videos.id` | CASCADE |
| `fk_feature_vectors_video_id_videos` | `feature_vectors.video_id` | `videos.id` | CASCADE |
| `fk_import_runs_creator_profile_id_creator_profiles` | `import_runs.creator_profile_id` | `creator_profiles.id` | CASCADE |
| `fk_analysis_runs_creator_profile_id_creator_profiles` | `analysis_runs.creator_profile_id` | `creator_profiles.id` | CASCADE |
| `fk_rule_executions_analysis_run_id_analysis_runs` | `rule_executions.analysis_run_id` | `analysis_runs.id` | CASCADE |
| `fk_evidence_analysis_run_id_analysis_runs` | `evidence.analysis_run_id` | `analysis_runs.id` | CASCADE |
| `fk_claims_analysis_run_id_analysis_runs` | `claims.analysis_run_id` | `analysis_runs.id` | CASCADE |
| `fk_claims_video_id_videos` | `claims.video_id` | `videos.id` | CASCADE |
| `fk_recommendations_analysis_run_id_analysis_runs` | `recommendations.analysis_run_id` | `analysis_runs.id` | CASCADE |
| `fk_recommendations_creator_profile_id_creator_profiles` | `recommendations.creator_profile_id` | `creator_profiles.id` | CASCADE |
| `fk_recommendations_claim_id_claims` | `recommendations.claim_id` | `claims.id` | SET NULL |
| `fk_recommendation_feedback_recommendation_id_recommendations` | `recommendation_feedback.recommendation_id` | `recommendations.id` | CASCADE |
| `fk_experiments_creator_profile_id_creator_profiles` | `experiments.creator_profile_id` | `creator_profiles.id` | CASCADE |
| `fk_experiments_recommendation_id_recommendations` | `experiments.recommendation_id` | `recommendations.id` | SET NULL |
| `fk_experiment_results_experiment_id_experiments` | `experiment_results.experiment_id` | `experiments.id` | CASCADE |
| `fk_claim_evidence_claim_id_claims` | `claim_evidence.claim_id` | `claims.id` | CASCADE |
| `fk_claim_evidence_evidence_id_evidence` | `claim_evidence.evidence_id` | `evidence.id` | CASCADE |

---

## Enum Reference

All enums are stored as `VARCHAR(16)` — **not** PostgreSQL native enums.

| Enum | Values | Default |
|------|--------|---------|
| `ImportRunStatus` | `pending`, `running`, `completed`, `failed` | `pending` |
| `AnalysisRunStatus` | `pending`, `running`, `completed`, `failed` | `pending` |
| `RuleExecutionStatus` | `success`, `failure`, `error` | `success` |
| `ClaimStatus` | `unverified`, `verified`, `debunked`, `uncertain` | `unverified` |
| `RecommendationStatus` | `draft`, `reviewed`, `approved`, `rejected`, `archived` | `draft` |
| `ExperimentStatus` | `draft`, `running`, `completed`, `cancelled` | `draft` |

---

## JSONB Fields (7 total)

| Table | Column | Justification |
|-------|--------|---------------|
| `videos` | `tags` | Variable-length YouTube tags; not independently queried |
| `feature_vectors` | `vector` | Heterogeneous per `feature_type` — no fixed schema |
| `rule_executions` | `input_snapshot` | Each rule defines its own input shape |
| `rule_executions` | `output` | Each rule defines its own output shape |
| `analysis_runs` | `pipeline_metadata` | Pipeline config varies per run type and trigger |
| `evidence` | `extra_data` | Source-specific metadata (transcript offset, external URL context) |
| `recommendations` | `extra_data` | Recommendation-type-specific data |

---

## Naming Conventions

| Convention | Rule | Example |
|------------|------|---------|
| **Tables** | Snake case, plural | `creator_profiles` |
| **Primary keys** | `id` — UUID v4 | |
| **Foreign keys** | `<referenced_table>_id` | `creator_profile_id` |
| **Boolean columns** | `is_` or `has_` prefix | `is_active`, `is_deleted` |
| **Timestamps** | `created_at`, `updated_at` — always `TIMESTAMPTZ` | |
| **Soft delete** | `is_deleted` + `deleted_at` | |
| **JSON data** | `extra_data` — NOT `metadata` | |
| **Version fields** | `generator_version` — VARCHAR(32) | |

---

## Things Intentionally Omitted

These are not in the schema and should not be added speculatively:

| Item | Reason |
|------|--------|
| **PostgreSQL native enums** | String columns are simpler; avoid ALTER TYPE migrations |
| **Partial unique indexes** (e.g. `WHERE is_deleted = false`) | Not yet needed; add when email-reuse collisions occur |
| **`video_tags` join table** | Tags are JSONB; extract if tag-based filtering becomes a query hot path |
| **Direct `video_id` FK on `Evidence`** | Evidence links through claims; add if claim-agnostic evidence queries emerge |
| **`RuleExecution.claim_id`** | Rules produce claims, but the link is through the analysis run, not a direct FK |
| **Inheritance / polymorphic tables** | Each entity has its own table; no single-table inheritance |
| **Created by / updated by audit columns** | Not needed until multi-user editing emerges |
| **Soft delete on every table** | Only applied where deletion is a business event (User, CreatorProfile, Video, Claim) |
| **Database-level encryption** | Application-layer encryption for tokens is preferred |

---

## Contract Enforcement

1. **Before merging any Sprint 3+ PR**, diff the new migration against this freeze
2. If the new migration **renames or drops** a table/column from this freeze, it must be approved
3. If the new migration **adds** tables/columns, no approval needed — this is expected
4. If the new migration **changes** an existing FK rule (e.g. SET NULL → CASCADE), it must be approved
5. This freeze document must be updated to reflect approved changes

---

## Verification

After running `alembic upgrade head`, query PostgreSQL:

```sql
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
-- Should return exactly 16 tables

SELECT COUNT(*) FROM pg_indexes
WHERE schemaname = 'public';
-- Should match index count above
```
