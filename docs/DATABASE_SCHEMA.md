# Database Schema

Documentation for all 15 IQoCreator database tables + 1 join table.

---

## Naming Conventions

| Convention | Rule |
|------------|------|
| **Tables** | Snake case, plural (`users`, `creator_profiles`) |
| **Primary keys** | `id` — UUID v4, application-generated |
| **Foreign keys** | `<table>_id` — e.g. `creator_profile_id` |
| **Timestamps** | `created_at`, `updated_at` — timezone-aware |
| **Indexes** | `ix_<table>_<column>` — explicit names |
| **FK constraints** | `fk_<table>_<column>_<referred_table>` |
| **Unique constraints** | `uq_<table>_<column>` |

---

## Table: `users`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `UUID` | PK, default `uuid4()` | |
| `email` | `VARCHAR(320)` | UNIQUE, NOT NULL, INDEX | Max email length per RFC 5321 |
| `display_name` | `VARCHAR(128)` | NULLABLE | |
| `avatar_url` | `VARCHAR(1024)` | NULLABLE | |
| `is_active` | `BOOLEAN` | NOT NULL, default `true` | |
| `is_superuser` | `BOOLEAN` | NOT NULL, default `false` | |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, `now()` | TimestampMixin |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL, `now()` | TimestampMixin |
| `is_deleted` | `BOOLEAN` | NOT NULL, default `false` | SoftDeleteMixin |
| `deleted_at` | `TIMESTAMPTZ` | NULLABLE | SoftDeleteMixin |

**Indexes:** `ix_users_email` (unique)

**Relationships:**
- 1:N → `connected_accounts` (cascade delete)
- 1:N → `creator_profiles` (cascade delete)

---

## Table: `connected_accounts`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `UUID` | PK, default `uuid4()` | |
| `user_id` | `UUID` | FK → `users.id` ON DELETE CASCADE, NOT NULL, INDEX | |
| `provider` | `VARCHAR(64)` | NOT NULL | e.g. `"google"`, `"youtube"` |
| `provider_account_id` | `VARCHAR(256)` | NOT NULL | |
| `access_token` | `TEXT` | NULLABLE | OAuth access token |
| `refresh_token` | `TEXT` | NULLABLE | OAuth refresh token |
| `token_expires_at` | `TIMESTAMPTZ` | NULLABLE | |
| `scope` | `VARCHAR(512)` | NULLABLE | OAuth scopes |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, `now()` | TimestampMixin |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL, `now()` | TimestampMixin |

**Indexes:** `ix_connected_accounts_provider_provider_id` (UNIQUE, composite)

**Relationships:**
- N:1 → `users`

---

## Table: `creator_profiles`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `UUID` | PK, default `uuid4()` | |
| `user_id` | `UUID` | FK → `users.id` ON DELETE SET NULL, NULLABLE, INDEX | |
| `name` | `VARCHAR(256)` | NOT NULL | |
| `handle` | `VARCHAR(128)` | NULLABLE | |
| `description` | `TEXT` | NULLABLE | |
| `thumbnail_url` | `VARCHAR(1024)` | NULLABLE | |
| `platform` | `VARCHAR(32)` | NOT NULL, default `'youtube'` | |
| `platform_creator_id` | `VARCHAR(128)` | NOT NULL | YouTube channel ID |
| `subscriber_count` | `BIGINT` | NULLABLE | |
| `total_views` | `BIGINT` | NULLABLE | |
| `joined_platform_at` | `TIMESTAMPTZ` | NULLABLE | |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, `now()` | TimestampMixin |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL, `now()` | TimestampMixin |
| `is_deleted` | `BOOLEAN` | NOT NULL, default `false` | SoftDeleteMixin |
| `deleted_at` | `TIMESTAMPTZ` | NULLABLE | SoftDeleteMixin |

**Indexes:** `ix_creator_profiles_platform_creator` (UNIQUE, composite)

**Relationships:**
- N:1 → `users`
- 1:N → `channel_metrics` (cascade delete)
- 1:N → `videos` (cascade delete)
- 1:N → `import_runs` (cascade delete)
- 1:N → `analysis_runs` (cascade delete)
- 1:N → `recommendations` (cascade delete)
- 1:N → `experiments` (cascade delete)

---

## Table: `channel_metrics`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `UUID` | PK, default `uuid4()` | |
| `creator_profile_id` | `UUID` | FK → `creator_profiles.id` ON DELETE CASCADE, NOT NULL, INDEX | |
| `recorded_at` | `TIMESTAMPTZ` | NOT NULL, INDEX | Time of snapshot |
| `subscriber_count` | `BIGINT` | NULLABLE | |
| `total_views` | `BIGINT` | NULLABLE | |
| `total_videos` | `INTEGER` | NULLABLE | |
| `avg_view_duration_seconds` | `FLOAT` | NULLABLE | |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, `now()` | TimestampMixin |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL, `now()` | TimestampMixin |

**Indexes:** `ix_channel_metrics_creator_profile_id`

**Relationships:**
- N:1 → `creator_profiles`

---

## Table: `videos`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `UUID` | PK, default `uuid4()` | |
| `creator_profile_id` | `UUID` | FK → `creator_profiles.id` ON DELETE CASCADE, NOT NULL, INDEX | |
| `platform_video_id` | `VARCHAR(64)` | UNIQUE, NOT NULL, INDEX | YouTube video ID |
| `title` | `VARCHAR(512)` | NOT NULL | |
| `description` | `TEXT` | NULLABLE | |
| `thumbnail_url` | `VARCHAR(1024)` | NULLABLE | |
| `published_at` | `TIMESTAMPTZ` | NULLABLE, INDEX | |
| `duration_seconds` | `INTEGER` | NULLABLE | |
| `url` | `VARCHAR(1024)` | NULLABLE | |
| `language` | `VARCHAR(16)` | NULLABLE | e.g. `"en"`, `"es"` |
| `tags` | `JSONB` | NULLABLE | YouTube tags array |
| `transcript` | `TEXT` | NULLABLE | Processed transcript |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, `now()` | TimestampMixin |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL, `now()` | TimestampMixin |
| `is_deleted` | `BOOLEAN` | NOT NULL, default `false` | SoftDeleteMixin |
| `deleted_at` | `TIMESTAMPTZ` | NULLABLE | SoftDeleteMixin |

**Indexes:** `ix_videos_platform_video_id` (unique), `ix_videos_creator_profile_id`, `ix_videos_published_at`

**Relationships:**
- N:1 → `creator_profiles`
- 1:N → `video_metrics` (cascade delete)
- 1:N → `feature_vectors` (cascade delete)
- 1:N → `claims` (cascade delete)

---

## Table: `video_metrics`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `UUID` | PK, default `uuid4()` | |
| `video_id` | `UUID` | FK → `videos.id` ON DELETE CASCADE, NOT NULL, INDEX | |
| `recorded_at` | `TIMESTAMPTZ` | NOT NULL, INDEX | Time of snapshot |
| `view_count` | `BIGINT` | NULLABLE | |
| `like_count` | `BIGINT` | NULLABLE | |
| `comment_count` | `BIGINT` | NULLABLE | |
| `share_count` | `BIGINT` | NULLABLE | |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, `now()` | TimestampMixin |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL, `now()` | TimestampMixin |

**Indexes:** `ix_video_metrics_video_recorded` (composite), `ix_video_metrics_video_id`, `ix_video_metrics_recorded_at`

**Relationships:**
- N:1 → `videos`

---

## Table: `feature_vectors`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `UUID` | PK, default `uuid4()` | |
| `video_id` | `UUID` | FK → `videos.id` ON DELETE CASCADE, NOT NULL, INDEX | |
| `feature_type` | `VARCHAR(64)` | NOT NULL | e.g. `"topic"`, `"sentiment"`, `"toxicity"` |
| `vector` | `JSONB` | NOT NULL | Heterogeneous feature data |
| `model_version` | `VARCHAR(64)` | NULLABLE | Model that generated this vector |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, `now()` | |

**Indexes:** `ix_feature_vectors_video_type` (composite), `ix_feature_vectors_video_id`

**Relationships:**
- N:1 → `videos`

---

## Table: `import_runs`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `UUID` | PK, default `uuid4()` | |
| `creator_profile_id` | `UUID` | FK → `creator_profiles.id` ON DELETE CASCADE, NOT NULL, INDEX | |
| `status` | `VARCHAR(16)` | NOT NULL, INDEX | Enum: `pending`, `running`, `completed`, `failed` |
| `source` | `VARCHAR(32)` | NOT NULL, default `'youtube_api'` | |
| `videos_imported` | `INTEGER` | NULLABLE | |
| `videos_failed` | `INTEGER` | NULLABLE | |
| `error_message` | `TEXT` | NULLABLE | |
| `started_at` | `TIMESTAMPTZ` | NULLABLE | |
| `completed_at` | `TIMESTAMPTZ` | NULLABLE | |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, `now()` | TimestampMixin |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL, `now()` | TimestampMixin |

**Indexes:** `ix_import_runs_creator_profile_id`, `ix_import_runs_status`

**Relationships:**
- N:1 → `creator_profiles`

---

## Table: `analysis_runs`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `UUID` | PK, default `uuid4()` | |
| `creator_profile_id` | `UUID` | FK → `creator_profiles.id` ON DELETE CASCADE, NOT NULL, INDEX | |
| `status` | `VARCHAR(16)` | NOT NULL, INDEX | Enum: `pending`, `running`, `completed`, `failed` |
| `trigger` | `VARCHAR(32)` | NOT NULL, default `'manual'` | `manual`, `scheduled`, `post_import` |
| `pipeline_metadata` | `JSONB` | NULLABLE | Runtime pipeline configuration |
| `generator_version` | `VARCHAR(32)` | NULLABLE | Pipeline version identifier |
| `claim_count` | `INTEGER` | NULLABLE | |
| `evidence_count` | `INTEGER` | NULLABLE | |
| `rule_count` | `INTEGER` | NULLABLE | |
| `started_at` | `TIMESTAMPTZ` | NULLABLE | |
| `completed_at` | `TIMESTAMPTZ` | NULLABLE | |
| `error_message` | `TEXT` | NULLABLE | |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, `now()` | TimestampMixin |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL, `now()` | TimestampMixin |

**Indexes:** `ix_analysis_runs_creator_profile_id`, `ix_analysis_runs_status`

**Relationships:**
- N:1 → `creator_profiles`
- 1:N → `rule_executions` (cascade delete)
- 1:N → `evidence` (cascade delete)
- 1:N → `claims` (cascade delete)
- 1:N → `recommendations` (cascade delete)

---

## Table: `rule_executions`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `UUID` | PK, default `uuid4()` | |
| `analysis_run_id` | `UUID` | FK → `analysis_runs.id` ON DELETE CASCADE, NOT NULL, INDEX | |
| `rule_name` | `VARCHAR(128)` | NOT NULL | |
| `rule_version` | `VARCHAR(32)` | NULLABLE | |
| `input_snapshot` | `JSONB` | NULLABLE | Rule-specific input |
| `output` | `JSONB` | NULLABLE | Rule-specific output |
| `status` | `VARCHAR(16)` | NOT NULL, default `'success'` | Enum: `success`, `failure`, `error` |
| `started_at` | `TIMESTAMPTZ` | NULLABLE | |
| `finished_at` | `TIMESTAMPTZ` | NULLABLE | |
| `duration_ms` | `INTEGER` | NULLABLE | Computed or captured duration |
| `error_message` | `TEXT` | NULLABLE | |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, `now()` | |

**Indexes:** `ix_rule_executions_analysis_run_id`

**Relationships:**
- N:1 → `analysis_runs`

---

## Table: `evidence`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `UUID` | PK, default `uuid4()` | |
| `analysis_run_id` | `UUID` | FK → `analysis_runs.id` ON DELETE CASCADE, NOT NULL, INDEX | |
| `source_type` | `VARCHAR(32)` | NOT NULL | `transcript`, `description`, `external` |
| `source_url` | `VARCHAR(1024)` | NULLABLE | |
| `content` | `TEXT` | NOT NULL | Evidence text |
| `relevance_score` | `FLOAT` | NULLABLE | |
| `confidence_score` | `FLOAT` | NULLABLE | |
| `generator_version` | `VARCHAR(32)` | NULLABLE | Rule engine version |
| `extra_data` | `JSONB` | NULLABLE | Additional metadata |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, `now()` | TimestampMixin |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL, `now()` | TimestampMixin |

**Indexes:** `ix_evidence_analysis_run_id`

**Relationships:**
- N:1 → `analysis_runs`
- N:M → `claims` via `claim_evidence`

---

## Table: `claim_evidence` (join table)

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `claim_id` | `UUID` | FK → `claims.id` ON DELETE CASCADE, PK | Composite PK |
| `evidence_id` | `UUID` | FK → `evidence.id` ON DELETE CASCADE, PK | Composite PK |

---

## Table: `claims`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `UUID` | PK, default `uuid4()` | |
| `analysis_run_id` | `UUID` | FK → `analysis_runs.id` ON DELETE CASCADE, NOT NULL, INDEX | |
| `video_id` | `UUID` | FK → `videos.id` ON DELETE CASCADE, NOT NULL, INDEX | |
| `text` | `TEXT` | NOT NULL | Claim statement |
| `claim_type` | `VARCHAR(32)` | NULLABLE | `factual`, `opinion`, `prediction` |
| `confidence_score` | `FLOAT` | NULLABLE | |
| `generator_version` | `VARCHAR(32)` | NULLABLE | Rule engine version |
| `status` | `VARCHAR(16)` | NOT NULL, INDEX | Enum: `unverified`, `verified`, `debunked`, `uncertain` |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, `now()` | TimestampMixin |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL, `now()` | TimestampMixin |
| `is_deleted` | `BOOLEAN` | NOT NULL, default `false` | SoftDeleteMixin |
| `deleted_at` | `TIMESTAMPTZ` | NULLABLE | SoftDeleteMixin |

**Indexes:** `ix_claims_analysis_run_id`, `ix_claims_video_id`, `ix_claims_status`

**Relationships:**
- N:1 → `analysis_runs`
- N:1 → `videos`
- N:M → `evidence` via `claim_evidence`
- 1:N → `recommendations` (cascade delete)

---

## Table: `recommendations`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `UUID` | PK, default `uuid4()` | |
| `analysis_run_id` | `UUID` | FK → `analysis_runs.id` ON DELETE CASCADE, NOT NULL, INDEX | |
| `creator_profile_id` | `UUID` | FK → `creator_profiles.id` ON DELETE CASCADE, NOT NULL, INDEX | |
| `claim_id` | `UUID` | FK → `claims.id` ON DELETE SET NULL, NULLABLE | |
| `recommendation_type` | `VARCHAR(64)` | NOT NULL | |
| `title` | `VARCHAR(256)` | NOT NULL | |
| `description` | `TEXT` | NULLABLE | |
| `priority` | `INTEGER` | NULLABLE | |
| `generator_version` | `VARCHAR(32)` | NULLABLE | Rule engine version |
| `status` | `VARCHAR(16)` | NOT NULL, INDEX | Enum: `draft`, `reviewed`, `approved`, `rejected`, `archived` |
| `extra_data` | `JSONB` | NULLABLE | Additional metadata |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, `now()` | TimestampMixin |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL, `now()` | TimestampMixin |

**Indexes:** `ix_recommendations_analysis_run_id`, `ix_recommendations_creator_profile_id`, `ix_recommendations_status`

**Relationships:**
- N:1 → `analysis_runs`
- N:1 → `creator_profiles`
- N:1 → `claims`
- 1:N → `recommendation_feedback` (cascade delete)

---

## Table: `recommendation_feedback`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `UUID` | PK, default `uuid4()` | |
| `recommendation_id` | `UUID` | FK → `recommendations.id` ON DELETE CASCADE, NOT NULL, INDEX | |
| `rating` | `INTEGER` | NULLABLE | 1–5 scale |
| `helpful` | `BOOLEAN` | NOT NULL, default `false` | |
| `implemented` | `BOOLEAN` | NOT NULL, default `false` | |
| `comment` | `TEXT` | NULLABLE | |
| `applied_at` | `TIMESTAMPTZ` | NULLABLE | When the recommendation was applied |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, `now()` | TimestampMixin |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL, `now()` | TimestampMixin |

**Indexes:** `ix_recommendation_feedback_recommendation_id`

**Relationships:**
- N:1 → `recommendations`

---

## Table: `experiments`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `UUID` | PK, default `uuid4()` | |
| `creator_profile_id` | `UUID` | FK → `creator_profiles.id` ON DELETE CASCADE, NOT NULL, INDEX | |
| `recommendation_id` | `UUID` | FK → `recommendations.id` ON DELETE SET NULL, NULLABLE, INDEX | |
| `name` | `VARCHAR(256)` | NOT NULL | |
| `description` | `TEXT` | NULLABLE | |
| `hypothesis` | `TEXT` | NULLABLE | |
| `status` | `VARCHAR(16)` | NOT NULL, INDEX | Enum: `draft`, `running`, `completed`, `cancelled` |
| `started_at` | `TIMESTAMPTZ` | NULLABLE | |
| `completed_at` | `TIMESTAMPTZ` | NULLABLE | |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, `now()` | TimestampMixin |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL, `now()` | TimestampMixin |

**Indexes:** `ix_experiments_creator_profile_id`, `ix_experiments_status`, `ix_experiments_recommendation_id`

**Relationships:**
- N:1 → `creator_profiles`
- N:1 → `recommendations`
- 1:N → `experiment_results` (cascade delete)

---

## Table: `experiment_results`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `UUID` | PK, default `uuid4()` | |
| `experiment_id` | `UUID` | FK → `experiments.id` ON DELETE CASCADE, NOT NULL, INDEX | |
| `metric_name` | `VARCHAR(128)` | NOT NULL | |
| `metric_value` | `FLOAT` | NOT NULL | |
| `unit` | `VARCHAR(32)` | NULLABLE | e.g. `"views"`, `"percentage"` |
| `recorded_at` | `TIMESTAMPTZ` | NOT NULL | |
| `notes` | `TEXT` | NULLABLE | |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, `now()` | TimestampMixin |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL, `now()` | TimestampMixin |

**Indexes:** `ix_experiment_results_experiment_id`

**Relationships:**
- N:1 → `experiments`

---

## Enum Reference

All enums are stored as `VARCHAR(16)` — PostgreSQL native enums are intentionally avoided for migration simplicity.

| Enum | Values | Used By |
|------|--------|---------|
| `ImportRunStatus` | `pending`, `running`, `completed`, `failed` | `import_runs.status` |
| `AnalysisRunStatus` | `pending`, `running`, `completed`, `failed` | `analysis_runs.status` |
| `RuleExecutionStatus` | `success`, `failure`, `error` | `rule_executions.status` |
| `ClaimStatus` | `unverified`, `verified`, `debunked`, `uncertain` | `claims.status` |
| `RecommendationStatus` | `draft`, `reviewed`, `approved`, `rejected`, `archived` | `recommendations.status` |
| `ExperimentStatus` | `draft`, `running`, `completed`, `cancelled` | `experiments.status` |

---

## JSONB Fields (Justification)

| Table | Column | Justification |
|-------|--------|---------------|
| `videos` | `tags` | YouTube tags are variable-length arrays; not independently queried |
| `feature_vectors` | `vector` | Feature vectors are heterogeneous per `feature_type` |
| `rule_executions` | `input_snapshot` | Rules have heterogeneous input shapes |
| `rule_executions` | `output` | Rules have heterogeneous output shapes |
| `analysis_runs` | `pipeline_metadata` | Pipeline config varies per run type |
| `evidence` | `extra_data` | Evidence source-specific metadata varies |
| `recommendations` | `extra_data` | Recommendation-type-specific data varies |
