# Pipeline Architecture

## Overview

IQoCreator processes creator content through two sequential pipeline stages: **Import** and **Analysis**. Each stage produces a run record that tracks progress, errors, and results.

```
┌─────────────┐     ┌──────────────┐     ┌───────────────┐
│             │     │              │     │               │
│  YouTube    │────▶│   ImportRun  │────▶│  AnalysisRun  │
│  Data API   │     │              │     │               │
│             │     │ • fetch      │     │ • rules       │
│             │     │ • save       │     │ • claims      │
│             │     │ • normalize  │     │ • evidence    │
│             │     │              │     │ • recommend   │
└─────────────┘     └──────────────┘     └───────────────┘
```

## Import Pipeline

The **ImportRun** fetches videos from a creator's YouTube channel and persists them to the database.

### Flow

1. **Trigger**: Manual action, scheduled job, or post-oauth redirect
2. **Create**: `ImportRun(status=pending, creator_profile_id=...)`
3. **Execute**: Fetch videos from YouTube Data API
4. **Persist**: Save `Video` + `VideoMetrics` records
5. **Complete**: Set `videos_imported`, `videos_failed`, `status=completed`

### State Machine

```
pending ──► running ──► completed
                │
                └──► failed
```

### Key Tables Written

- `import_runs` — 1 row per run
- `videos` — 1 row per imported video
- `video_metrics` — 1 row per video (initial snapshot)

---

## Analysis Pipeline

The **AnalysisRun** processes imported content through a series of rules to extract claims, gather evidence, and generate recommendations.

### Flow

1. **Trigger**: Manual action, scheduled job, or post-import completion
2. **Create**: `AnalysisRun(status=pending, creator_profile_id=...)`
3. **Execute Rules**: For each rule in the pipeline:
   - Create `RuleExecution` with `input_snapshot`
   - Run rule logic
   - Store `output` and `status`
4. **Extract Claims**: Rules identify claims in video transcripts
5. **Gather Evidence**: Evidence is collected for each claim
6. **Generate Recommendations**: Actionable items derived from claims
7. **Complete**: Set `claim_count`, `evidence_count`, `rule_count`, `status=completed`

### State Machine

```
pending ──► running ──► completed
                │
                └──► failed
```

### Key Tables Written

- `analysis_runs` — 1 row per run
- `rule_executions` — 1 row per rule applied
- `claims` — 1 row per extracted claim
- `evidence` — 1 row per evidence item
- `claim_evidence` — N rows per claim-evidence associations
- `recommendations` — 1 row per generated recommendation

---

## Rule Execution Model

Rules are the atomic unit of work in the analysis pipeline. Each rule:

1. Receives an `input_snapshot` (JSONB) with its specific input data
2. Produces an `output` (JSONB) with results
3. Records `started_at`, `finished_at`, and `duration_ms`
4. Reports `status`: `success`, `failure`, or `error`

Rule outputs can be:
- **Claims**: Statements extracted from content
- **Evidence**: Supporting/refuting data for claims
- **Recommendations**: Actionable items
- **Feature Vectors**: Computed features for ML models

---

## Pipeline Orchestration Principles

| Principle | Rule |
|-----------|------|
| **Idempotency** | Re-running the same pipeline produces the same results |
| **Observability** | Every run records timing, counts, and errors |
| **Isolation** | Pipeline stages are independent — import can succeed while analysis fails |
| **Versioning** | Every generated object records `generator_version` |
| **Ordering** | Import must complete before analysis can begin |

---

## Future Pipeline Extensions

These are intentionally not built yet (per Rule 4 — no speculative architecture):

- **Scheduled Analysis**: Cron-triggered re-analysis of existing content
- **Incremental Import**: Only fetch videos since last import
- **Batch Rules**: Rules that operate across multiple videos/channels
- **Human Review Stage**: Manual claim verification workflow
- **Experiment Stage**: A/B testing recommendations against control groups
