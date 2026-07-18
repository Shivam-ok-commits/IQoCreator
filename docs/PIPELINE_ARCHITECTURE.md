# Pipeline Architecture

> **v2.0** — reflects the pipeline as implemented in Sprints 5A–10. This document is **normative**: it specifies what must be true. Any implementation that violates these rules is incorrect by definition.
>
> Architectural decisions affecting the pipeline are recorded as ADRs in `IMPORT_ARCHITECTURE.md`.

---

## 1. Vision

IQoCreator transforms raw YouTube data into actionable, explainable recommendations for creators. The transformation happens through a sequence of deterministic, independently testable stages — each consuming one immutable artifact and producing the next.

```
MetricSnapshot
       │
       ▼
MetricFeatureVector
       │
       ▼
     Finding
       │
       ▼
PipelineEvidence
       │
       ▼
 PipelineClaim
       │
       ▼
PipelineRecommendation
       │
       ▼
PipelineExperiment
```

No stage mutates its input. No stage depends on the internal state of another. Every stage is replayable with identical inputs producing identical outputs.

---

## 2. Design Principles

### Immutable Artifacts

Every artifact in the pipeline is immutable once produced. Artifacts may be versioned (new schema → new artifact type), but never mutated in place. A stage never mutates its input artifact.

**Rationale:** Immutability guarantees that reprocessing any stage produces the same downstream results. It eliminates an entire class of bugs where a stage accidentally modifies shared state. Combined with the Artifact Ownership Principle, it ensures that only the owner of an artifact has the authority to produce a new version.

### Artifact Ownership Principle

Every artifact has exactly one authoritative owner. Ownership includes creation, schema evolution, versioning, lifecycle management, and publication.

| Artifact | Owner |
|----------|-------|
| `ConnectedAccount` | OAuth subsystem |
| `ImportRun` | ImportCoordinator |
| `MetricSnapshot` | MetricsCollectionStage |
| `MetricFeatureVector` | FeatureExtractionStage |
| `Finding` | RuleEngine |
| `PipelineEvidence` | EvidenceEngine |
| `PipelineClaim` | ClaimEngine |
| `PipelineRecommendation` | RecommendationEngine |
| `PipelineExperiment` | LearningEngine |

**Rationale:** Ownership is the foundational principle from which all other rules derive. If ownership is clear, producer, consumer, versioning, and replay policies are straightforward consequences rather than independent decisions.

### Single Producer Principle

Every artifact type has exactly one producer — a direct consequence of the Artifact Ownership Principle. No artifact is ever written by two different stages.

**Rationale:** Single ownership guarantees deterministic provenance, unambiguous schema authority, and straightforward versioning. If two stages could produce the same artifact type, conflicts would require arbitration logic — an entire category of complexity eliminated by this rule.

### Single Consumer Responsibility

Each stage consumes exactly one input artifact type. A stage never reads from multiple artifact types to produce its output.

**Exception:** The `LearningEngine` (Sprint 10) may consume `Recommendation` + `ExperimentOutcome` to produce `KnowledgeBase` entries, as this is definitionally a synthesis of two prior stages. This exception is **not** a precedent — no layer after LearningEngine may consume more than one input.

**Rationale:** Single-consumer stages are independently testable — mock one input, verify one output. Multi-consumer stages introduce implicit coupling between upstream producers.

### Replayability

Re-running any stage with identical inputs must produce identical outputs (excluding timestamps and auto-generated IDs).

**Enforcement:** Stages are pure functions with respect to their input artifact. Side effects (persistence, event publication) happen after the output artifact is fully constructed, not during transformation.

### Idempotency

Persisting an artifact multiple times produces the same result as persisting it once. All pipeline persistence is append-only — new artifacts do not overwrite or corrupt previous ones.

**Rationale:** Idempotency allows safe retry of any stage without deduplication logic at the consumer level.

### Deterministic Processing

Pipeline stages must never use AI, LLMs, randomization, or external state to produce their output. Every decision must be traceable to a deterministic rule operating on the input artifact.

**Rationale:** Nondeterministic stages cannot be replayed, cannot be tested deterministically, and cannot produce explainable recommendations. AI may be used for *presentation* (e.g., natural-language explanation of a Finding) but never for *production* of the artifact itself.

---

## 3. Dataflow Architecture

```
                 ┌──────────────────────────┐
                 │      ImportCompleted      │
                 │      (domain event)       │
                 └───────────┬───────────────┘
                             │
                             ▼
                 ┌──────────────────────────┐
                 │  MetricsCollectionStage   │
                 │  (Sprint 5A)              │
                 └───────────┬───────────────┘
                             │
                             ▼
                 ┌──────────────────────────┐
                 │      MetricSnapshot       │
                 │      (immutable)          │
                 └───────────┬───────────────┘
                             │
                             ▼
                 ┌──────────────────────────┐
                 │  FeatureExtractionStage   │
                 │  (Sprint 5B)              │
                 └───────────┬───────────────┘
                             │
                             ▼
                 ┌──────────────────────────┐
                 │   MetricFeatureVector     │
                 │   (immutable)             │
                 └───────────┬───────────────┘
                             │
                             ▼
                 ┌──────────────────────────┐
                 │       RuleEngine          │
                 │       (Sprint 6)          │
                 └───────────┬───────────────┘
                             │
                             ▼
                 ┌──────────────────────────┐
                 │        Finding            │
                 │        (immutable)        │
                 └───────────┬───────────────┘
                             │
                             ▼
                 ┌──────────────────────────┐
                 │     EvidenceEngine        │
                 │     (Sprint 7)            │
                 └───────────┬───────────────┘
                             │
                             ▼
                 ┌──────────────────────────┐
                 │    PipelineEvidence       │
                 │    (immutable)            │
                 └───────────┬───────────────┘
                             │
                             ▼
                 ┌──────────────────────────┐
                 │      ClaimEngine          │
                 │      (Sprint 8)           │
                 └───────────┬───────────────┘
                             │
                             ▼
                 ┌──────────────────────────┐
                 │     PipelineClaim         │
                 │     (immutable)           │
                 └───────────┬───────────────┘
                             │
                             ▼
                 ┌──────────────────────────┐
                 │ RecommendationEngine      │
                 │ (Sprint 9)                │
                 └───────────┬───────────────┘
                             │
                             ▼
                 ┌──────────────────────────┐
                 │ PipelineRecommendation    │
                 │ (immutable, terminal)     │
                 └───────────┬───────────────┘
                             │
                             ▼
                 ┌──────────────────────────┐
                 │     LearningEngine        │
                 │     (Sprint 10)           │
                 └───────────┬───────────────┘
                             │
                             ▼
                 ┌──────────────────────────┐
                 │  PipelineExperiment       │
                 │  (immutable)              │
                 └───────────────────────────┘
```

### Pipeline Initiation

The pipeline starts when `ImportTriggerService` receives a trigger event (see ADR-012). The trigger event carries the `TriggerRequest` value object:

```python
@dataclass(frozen=True)
class TriggerRequest:
    trigger_type: TriggerType        # api, event, schedule, manual
    creator_profile_id: UUID
    connected_account_id: UUID
    requested_at: datetime
    initiated_by: UUID | None
```

The resulting `TriggerResult` carries the outcome:

```python
@dataclass(frozen=True)
class TriggerResult:
    import_run_id: UUID
    status: ImportRunStatus
```

### Stage Chaining

Stages are currently invoked serially through the `ImportTriggerService` and pipeline orchestration (see Sprint 5A.2). Future domain event publication will follow the commit-before-event pattern (ADR-012):

```
MetricSnapshotCreated → triggers → FeatureExtraction
MetricFeatureVectorCreated → triggers → RuleEvaluation
FindingCreated → triggers → EvidenceGeneration
PipelineEvidenceCreated → triggers → ClaimGeneration
PipelineClaimCreated → triggers → RecommendationGeneration
PipelineRecommendationCreated → triggers → ExperimentCreation
```

Events must be published only after the artifact is durably persisted (see ADR-012: Commit-Before-Event).

---

## 4. Artifact Catalog

### MetricSnapshot

*Defined in:* `app/models/metric_snapshot.py`

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `creator_profile_id` | UUID | Owning creator |
| `snapshot_at` | datetime | When metrics were collected |
| `source_import_run_id` | UUID | ImportRun that produced this snapshot |
| `total_videos` | int | Video count at snapshot time |
| `total_views` | int | Lifetime views |
| `total_subscribers` | int | Subscriber count |
| `avg_views_per_video` | float | Average views per video |
| `avg_view_duration_seconds` | float | Average view duration |
| `total_watch_time_hours` | float | Total watch time |
| `engagement_rate` | float | (likes+comments) / views |
| `version` | int | Schema version |

**Producer:** `MetricsCollectionStage` (Sprint 5A)

**Persistence:** Append-only via `MetricsRepository.create()`

---

### MetricFeatureVector

*Defined in:* `app/models/feature_vector.py`

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `creator_profile_id` | UUID | Owning creator |
| `computed_at` | datetime | When features were extracted |
| `source_snapshot_id` | UUID | MetricSnapshot this was derived from |
| `features` | JSONB | Key-value map of feature name → value |
| `feature_schema_version` | int | Schema version for the features dict |
| `version` | int | Artifact version |

**Initial features:**

| Feature | Type | Description |
|---------|------|-------------|
| `total_videos` | int | Video count |
| `upload_frequency` | float | Videos per day |
| `average_views` | float | Mean views per video |
| `average_likes` | float | Mean likes per video |
| `average_comments` | float | Mean comments per video |
| `engagement_rate` | float | (likes+comments) / views |
| `shorts_ratio` | float | Fraction of videos that are Shorts |
| `average_duration` | float | Mean video duration in seconds |
| `average_title_length` | float | Mean title character count |
| `channel_age_days` | float | Days since channel creation |

**Producer:** `FeatureExtractionStage` (Sprint 5B)

**Persistence:** Append-only via `FeatureRepository.create()`

---

### Finding

*Defined in:* `app/models/finding.py`

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `creator_profile_id` | UUID | Owning creator |
| `computed_at` | datetime | When the finding was generated |
| `source_feature_vector_id` | UUID | MetricFeatureVector this was derived from |
| `rule_id` | string | Machine-readable rule identifier |
| `severity` | enum | `INFO`, `LOW`, `MEDIUM`, `HIGH` |
| `category` | string | Finding category (e.g., `publishing`, `engagement`, `growth`) |
| `title` | string | Short human-readable title |
| `description` | string | Detailed description |
| `evidence` | JSONB | The specific feature values that triggered the rule |
| `version` | int | Schema version |

**Implemented rules:**

| Rule ID | Severity | Description |
|---------|----------|-------------|
| `low_upload_frequency` | MEDIUM | Upload frequency < 0.02 videos/day |
| `low_engagement_rate` | HIGH | Engagement rate < 0.01 (1%) |
| `high_shorts_ratio` | INFO | Shorts ratio > 0.5 (50%) |
| `low_average_views` | MEDIUM/HIGH | Average views < 1000 |
| `inconsistent_publishing` | HIGH | Upload frequency < 0.01 videos/day |
| `new_channel` | INFO | Channel age < 90 days |

**Producer:** `RuleEngine` (Sprint 6)

**Persistence:** Append-only via `FindingRepository.create_many()`

**Architecture:** Rules are pure functions registered in a `RuleRegistry`. The `RuleEngine` orchestrates execution — one failing rule never crashes the engine.

---

### PipelineEvidence

*Defined in:* `app/models/pipeline_evidence.py`

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `finding_id` | UUID (FK→Finding, unique) | Finding this evidence supports |
| `source_rule_id` | string | The rule that produced the source finding |
| `confidence` | float | 0.0–1.0 deterministic confidence score |
| `supporting_data` | JSONB | Feature values, thresholds, and completeness metrics |
| `explanation` | text | Deterministic template-generated explanation |
| `source_feature_vector_id` | UUID (FK) | FeatureVector used for computation |

**Confidence scoring factors:**

1. **Severity base:** INFO=0.3, LOW=0.5, MEDIUM=0.7, HIGH=0.9
2. **Distance from threshold:** Normalized distance scaled by `min(threshold * 2, 0.01)`
3. **Completeness:** Proportion of rule-relevant features present in the input

**Producer:** `EvidenceEngine` (Sprint 7)

**Persistence:** Append-only via `PipelineEvidenceRepository.create_many()`

---

### PipelineClaim

*Defined in:* `app/models/pipeline_claim.py`

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `source_evidence_id` | UUID (FK→PipelineEvidence, unique) | Evidence this claim is based on |
| `category` | string | Claim category (mirrors finding category) |
| `severity` | string | Mirrors finding severity |
| `confidence` | float | Copied from evidence confidence |
| `summary` | string | Deterministic template-generated summary |
| `rationale` | text | Explanation + evidence details |
| `supporting_evidence_ids` | JSONB(list[str]) | Evidence IDs supporting this claim |
| `creator_profile_id` | UUID | Owning creator |

**Summary templates:**

| Category | Template |
|----------|----------|
| `publishing` | `{title} — the channel's publishing activity is below recommended levels.` |
| `engagement` | `{title} — audience engagement is lower than expected.` |
| `content_format` | `{title} — the channel may have an imbalance in content format.` |
| `performance` | `{title} — the channel's content performance is below the expected baseline.` |
| `growth` | `{title} — the channel is still in an early stage of growth.` |

**Producer:** `ClaimEngine` (Sprint 8)

**Persistence:** Append-only via `ClaimRepository.create_many()`

---

### PipelineRecommendation

*Defined in:* `app/models/pipeline_recommendation.py`

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `source_claim_id` | UUID (FK→PipelineClaim, unique) | Claim this recommendation addresses |
| `priority` | enum | `LOW`, `MEDIUM`, `HIGH`, `CRITICAL` |
| `category` | string | Recommendation category |
| `title` | string | Short action-oriented title |
| `description` | string | Detailed recommendation |
| `expected_outcome` | string | Predicted outcome if followed |
| `success_metric` | string | How to measure success |
| `creator_profile_id` | UUID | Owning creator |

**Template map:**

| Category | Priority | Title | Expected Outcome |
|----------|----------|-------|------------------|
| `publishing` | HIGH | Increase upload cadence | More consistent audience growth |
| `engagement` | CRITICAL | Improve audience retention | Higher view duration and repeat viewership |
| `content_format` | MEDIUM | Increase long-form balance | Improved overall channel performance |
| `performance` | HIGH | Improve topic/title selection | Higher average views per video |
| `growth` | LOW | Continue publishing — collect data | More accurate recommendations after sufficient data |
| *(unknown)* | MEDIUM | Review channel metrics | Better understanding of channel health |

**Producer:** `RecommendationEngine` (Sprint 9)

**Persistence:** Append-only via `RecommendationRepository.create_many()`

---

### PipelineExperiment

*Defined in:* `app/models/pipeline_experiment.py`

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `source_recommendation_id` | UUID (FK, unique) | Recommendation being experimented on |
| `hypothesis` | text | Deterministic template-generated hypothesis |
| `success_metric` | string | How success is measured (copied from recommendation) |
| `expected_outcome` | string | Predicted outcome (copied from recommendation) |
| `status` | enum | `PENDING`, `RUNNING`, `COMPLETED`, `FAILED`, `CANCELLED` |
| `created_at` | datetime | When the experiment was created |
| `creator_profile_id` | UUID | Owning creator |

**Hypothesis template:**

```
Implementing "{title}" will lead to {outcome}. Success is measured by: {metric}.
```

**Producer:** `LearningEngine` (Sprint 10)

**Persistence:** Append-only via `ExperimentRepository.create_many()`

---

## 5. Pipeline Layers

### Metrics Ingestion (Sprint 5A)

| Attribute | Rule |
|-----------|------|
| **Module** | `app.pipeline.metrics_collection_stage` |
| **Input** | `ImportRun` completion event |
| **Output** | `MetricSnapshot` |
| **Responsibilities** | Collect channel and video metrics from the database after an import completes. Compute derived metrics (averages, rates, trends). Persist as an immutable snapshot. |
| **Allowed dependencies** | `CreatorProfileRepository`, `VideoRepository`, `ChannelMetricsRepository` |
| **Forbidden dependencies** | `ProviderAdapter`, `ImportCoordinator`, `MetricFeatureVector`, any intelligence-layer model |
| **Idempotency** | Append-only — new snapshots are created; previous ones preserved unmodified |

### Feature Extraction (Sprint 5B)

| Attribute | Rule |
|-----------|------|
| **Module** | `app.pipeline.feature_extraction_stage` |
| **Input** | `MetricSnapshot` |
| **Output** | `MetricFeatureVector` |
| **Responsibilities** | Derive semantic features from raw metrics. Each feature is a deterministic function of one or more metric fields. Features are named, typed, and versioned. |
| **Allowed dependencies** | Feature computation functions (pure), `FeatureRepository` |
| **Forbidden dependencies** | Any model class, any repository other than `FeatureRepository`, any external API, any AI/LLM |
| **Idempotency** | Append-only |

### Rule Engine (Sprint 6)

| Attribute | Rule |
|-----------|------|
| **Module** | `app.rules.engine` |
| **Input** | `MetricFeatureVector` |
| **Output** | `Finding` |
| **Responsibilities** | Evaluate a registry of deterministic rules against a feature vector. Each rule produces zero or one finding. Rules are versioned and independently testable. |
| **Allowed dependencies** | `FindingRepository`, rule definitions, `RuleRegistry` |
| **Forbidden dependencies** | Any model class, any external API, any AI/LLM, any feature vector field not present in the input |
| **Idempotency** | Append-only — one failing rule never crashes the engine |

### Evidence Engine (Sprint 7)

| Attribute | Rule |
|-----------|------|
| **Module** | `app.pipeline.evidence_engine` |
| **Input** | `Finding` |
| **Output** | `PipelineEvidence` |
| **Responsibilities** | For each finding, compute deterministic confidence and generate structured supporting data. No database access inside evidence generation. |
| **Allowed dependencies** | `PipelineEvidenceRepository` |
| **Forbidden dependencies** | Any AI/LLM, non-deterministic sources, any repository other than `PipelineEvidenceRepository` |
| **Idempotency** | Append-only |

### Claim Engine (Sprint 8)

| Attribute | Rule |
|-----------|------|
| **Module** | `app.pipeline.claim_engine` |
| **Input** | `PipelineEvidence` |
| **Output** | `PipelineClaim` |
| **Responsibilities** | Convert evidence into structured summaries and rationales using deterministic templates. Claims are the system's human-readable conclusions. |
| **Allowed dependencies** | `ClaimRepository` |
| **Forbidden dependencies** | Any model class, any repository other than `ClaimRepository`, any AI/LLM |
| **Idempotency** | Append-only |

### Recommendation Engine (Sprint 9)

| Attribute | Rule |
|-----------|------|
| **Module** | `app.pipeline.recommendation_engine` |
| **Input** | `PipelineClaim` |
| **Output** | `PipelineRecommendation` |
| **Responsibilities** | Map claims to actionable recommendations using category-based templates. Recommendations are prioritized by severity. No free-form text generation. |
| **Allowed dependencies** | `RecommendationRepository`, recommendation template definitions |
| **Forbidden dependencies** | Any model class, any AI/LLM, non-deterministic sources |
| **Idempotency** | Append-only |

### Learning Engine (Sprint 10)

| Attribute | Rule |
|-----------|------|
| **Module** | `app.pipeline.learning_engine` |
| **Input** | `PipelineRecommendation` |
| **Output** | `PipelineExperiment` |
| **Responsibilities** | Convert recommendations into experiment records. Generate deterministic hypotheses from templates. Never evaluate experiment success or update previous experiments. |
| **Allowed dependencies** | `ExperimentRepository` |
| **Forbidden dependencies** | Any AI/LLM, any analytics, any automatic recommendation tuning, any feedback loop |
| **Idempotency** | Append-only |

---

## 6. Dependency Rules

### Layer dependency direction

```
        Metrics Ingestion
               │
               ▼
        Feature Extraction
               │
               ▼
           Rule Engine
               │
               ▼
        Evidence Engine
               │
               ▼
          Claim Engine
               │
               ▼
    Recommendation Engine
               │
               ▼
        Learning Engine
```

- A layer may depend only on artifacts from the immediately preceding layer.
- A layer must not depend on artifacts two or more layers away.
- A layer must not depend on repositories owned by another layer.
- Exception: the `EvidenceEngine` may query `VideoRepository` and `ChannelMetricsRepository` (owned by the import subsystem) to retrieve concrete evidence data. This is a read-only dependency and does not violate ownership. (Note: the current implementation does not make database queries inside evidence generation — it receives all data through the context.)

### General rules

| Rule | Enforcement |
|------|-------------|
| Layers communicate through immutable artifacts | Review import statements between layer packages |
| No layer mutates an artifact it did not produce | Verify artifact constructors and persistence are append-only |
| No layer depends on the internal state of another layer | No direct imports between layer modules; only artifact types |
| Each artifact type has exactly one repository | Review repository imports per layer |
| Events are published after commit, not before | ADR-012 |

---

## 7. Extension Guidelines

### Adding a new feature

1. Define the feature as a deterministic function of `MetricSnapshot` fields
2. Register it in the `FeatureExtractionStage` feature computation
3. Update `feature_schema_version` if the set of features changes
4. Do **not** modify existing feature functions

### Adding a new rule

1. Create a rule in `app/rules/impl.py`: `(RuleContext) → Finding | None`
2. Register it in `RuleRegistry`
3. Define the `rule_id`, `severity`, `category`, and `evidence` keys
4. Do **not** modify existing rules

### Adding a new claim type

1. Add a template in `ClaimEngine._generate_summary()`
2. Map the category to the appropriate template
3. Do **not** modify existing claim generation logic

### Adding a new recommendation type

1. Add a `RecommendationTemplate` entry in `RecommendationEngine._TEMPLATES`
2. Define priority, title, description, expected outcome, and success metric
3. Do **not** modify existing templates

### Adding a new experiment hypothesis pattern

1. Modify `LearningEngine._generate_hypothesis()` — currently uses a single template
2. Extend with per-category or per-priority patterns as needed
3. Do **not** modify existing experiment creation logic

---

## 8. Replay & Reprocessing

### Partial replay

Any stage can be replayed in isolation by providing its input artifact:

```python
input_artifact = load(MetricSnapshot, id=...)
output = FeatureExtractionStage.execute(context)
persist(output)
```

This does not affect downstream stages until they are also replayed with the new output.

### Full reprocessing

To regenerate all artifacts from a given point:

1. Truncate all artifacts from `target_stage` onward
2. Re-run `target_stage` with its original input
3. Cascade — each downstream stage processes the newly produced artifact
4. Verify the final `PipelineRecommendation` / `PipelineExperiment` set matches expected counts

### Determinism guarantee

Because all stages are deterministic and all artifacts are immutable, reprocessing produces bit-identical outputs (excluding timestamps and IDs). Any deviation indicates a bug or a non-deterministic dependency that must be removed.

### Tested via

Every stage includes replay tests:
- `test_replay_produces_same_output` (or equivalent)
- `test_historical_persistence` (previous artifacts unchanged after new run)
- `test_empty_input` (no crash, empty output list)

---

## 9. Versioning Strategy

### Artifact versioning

Each artifact type carries a `version` integer. When the schema changes:

1. Increment the version for that artifact type
2. The producing stage writes the new version
3. Downstream stages check the version and handle migration if needed
4. Old-version artifacts are never migrated in place — reprocessing produces new versions

### Feature vector versioning

The `MetricFeatureVector` carries a `feature_schema_version` distinct from the artifact `version`. This allows adding/removing features without changing the artifact schema:

- Artifact `version` changes when the `MetricFeatureVector` table schema changes
- `feature_schema_version` changes when the set of computed features changes
- Consumers check `feature_schema_version` to know which features are present

### Rule versioning

Each rule carries a `rule_version`. When a rule's logic changes:

1. Increment the rule's version
2. New `Finding` records reference the new `rule_version`
3. Old findings remain associated with the old `rule_version`
4. Reprocessing with the updated rule produces findings with the new version

---

## 10. Architectural Invariants

The following rules must not be violated without introducing a new ADR:

| # | Invariant |
|---|-----------|
| 1 | Every artifact has exactly one owner |
| 2 | Every artifact has exactly one producer |
| 3 | Processing stages are deterministic |
| 4 | A stage never mutates its input artifact |
| 5 | Events are published only after durable commit |
| 6 | Pipeline stages communicate through immutable artifacts |
| 7 | A stage may depend only on artifacts from the immediately preceding stage unless an ADR explicitly permits otherwise |
| 8 | Re-running any stage with identical inputs must produce identical outputs (excluding timestamps and IDs) |
| 9 | Event publication is explicit, not automatic |
| 10 | Every new artifact type requires a documented owner, producer, versioning strategy, and replay policy |

---

## 11. Implementation Reference

### File map

| Artifact | Module | Repository |
|----------|--------|------------|
| `MetricSnapshot` | `app.models.metric_snapshot` | `app.repositories.metrics_repo` |
| `MetricFeatureVector` | `app.models.feature_vector` | `app.repositories.feature_repo` |
| `Finding` | `app.models.finding` | `app.repositories.finding_repo` |
| `PipelineEvidence` | `app.models.pipeline_evidence` | `app.repositories.pipeline_evidence_repo` |
| `PipelineClaim` | `app.models.pipeline_claim` | `app.repositories.claim_repo` |
| `PipelineRecommendation` | `app.models.pipeline_recommendation` | `app.repositories.recommendation_repo` |
| `PipelineExperiment` | `app.models.pipeline_experiment` | `app.repositories.experiment_repo` |

### Stage modules

| Stage | Module |
|-------|--------|
| `MetricsCollectionStage` | `app.pipeline.metrics_collection_stage` |
| `ImportTriggerService` | `app.pipeline.import_trigger_service` |
| `FeatureExtractionStage` | `app.pipeline.feature_extraction_stage` |
| `RuleEngine` | `app.rules.engine` |
| `EvidenceEngine` | `app.pipeline.evidence_engine` |
| `ClaimEngine` | `app.pipeline.claim_engine` |
| `RecommendationEngine` | `app.pipeline.recommendation_engine` |
| `LearningEngine` | `app.pipeline.learning_engine` |

### Test directories

| Scope | Path |
|-------|------|
| Pipeline stages | `tests/test_pipeline/` |
| Rule engine | `tests/test_rules/` |

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-18 | — | Sprint 5 preview — initial pipeline architecture spec |
| 2.0 | 2026-07-18 | — | Post-Sprint 10 — reflects actual implemented artifacts, modules, and templates. Updated artifact catalog with field-level specs. Added implementation reference (file map, stage modules, test directories). Removed speculative fields and unbuilt stages. |

## Change Rule

Any architectural change (new layer, changed artifact type, modified responsibility, added dependency) **must** update this document and record the decision as an ADR in `IMPORT_ARCHITECTURE.md`.
