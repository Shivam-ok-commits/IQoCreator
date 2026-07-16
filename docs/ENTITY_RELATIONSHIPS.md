# Entity Relationships

## Foreign Key Graph

```
users
└── connected_accounts.user_id ──── ON DELETE CASCADE
└── creator_profiles.user_id ────── ON DELETE SET NULL
    │
    ├── channel_metrics.creator_profile_id ── ON DELETE CASCADE
    ├── videos.creator_profile_id ─────────── ON DELETE CASCADE
    │   ├── video_metrics.video_id ────────── ON DELETE CASCADE
    │   ├── feature_vectors.video_id ──────── ON DELETE CASCADE
    │   └── claims.video_id ───────────────── ON DELETE CASCADE
    │
    ├── import_runs.creator_profile_id ────── ON DELETE CASCADE
    │
    ├── analysis_runs.creator_profile_id ──── ON DELETE CASCADE
    │   ├── rule_executions.analysis_run_id ─ ON DELETE CASCADE
    │   ├── evidence.analysis_run_id ──────── ON DELETE CASCADE
    │   │   └── claim_evidence.evidence_id ── ON DELETE CASCADE
    │   ├── claims.analysis_run_id ────────── ON DELETE CASCADE
    │   │   ├── claim_evidence.claim_id ───── ON DELETE CASCADE
    │   │   └── recommendations.claim_id ──── ON DELETE SET NULL
    │   └── recommendations.analysis_run_id ─ ON DELETE CASCADE
    │       └── recommendation_feedback.recommendation_id ── ON DELETE CASCADE
    │
    ├── recommendations.creator_profile_id ── ON DELETE CASCADE
    │
    └── experiments.creator_profile_id ────── ON DELETE CASCADE
        ├── experiments.recommendation_id ─── ON DELETE SET NULL
        └── experiment_results.experiment_id─ ON DELETE CASCADE
```

## Cascade Rules

| Parent | Child | Rule | Rationale |
|--------|-------|------|-----------|
| `users` | `connected_accounts` | CASCADE | Account is meaningless without user |
| `users` | `creator_profiles` | CASCADE | Profiles owned by user |
| `creator_profiles` | `channel_metrics` | CASCADE | Metrics are snapshots of the profile |
| `creator_profiles` | `videos` | CASCADE | Videos belong to creator |
| `creator_profiles` | `import_runs` | CASCADE | Runs are scoped to a creator |
| `creator_profiles` | `analysis_runs` | CASCADE | Runs are scoped to a creator |
| `creator_profiles` | `recommendations` | CASCADE | Recommendations target a creator |
| `creator_profiles` | `experiments` | CASCADE | Experiments are per-creator |
| `videos` | `video_metrics` | CASCADE | Metrics are video-specific |
| `videos` | `feature_vectors` | CASCADE | Features are video-specific |
| `videos` | `claims` | CASCADE | Claims come from video content |
| `analysis_runs` | `rule_executions` | CASCADE | Executions belong to the run |
| `analysis_runs` | `evidence` | CASCADE | Evidence from this run |
| `analysis_runs` | `claims` | CASCADE | Claims from this run |
| `analysis_runs` | `recommendations` | CASCADE | Recommendations from this run |
| `claims` | `claim_evidence` | CASCADE | Join table entries |
| `evidence` | `claim_evidence` | CASCADE | Join table entries |
| `claims` | `recommendations` | CASCADE | Recommendations reference a claim |
| `recommendations` | `recommendation_feedback` | CASCADE | Feedback is about the recommendation |
| `experiments` | `experiment_results` | CASCADE | Results belong to the experiment |
| `users` → `creator_profiles` | SET NULL | Profile survives user deletion |
| `claims` → `recommendations` | SET NULL | Recommendation survives claim deletion |
| `recommendations` → `experiments` | SET NULL | Experiment survives recommendation deletion |

## Cardinality Summary

```
User             1 ──N── ConnectedAccount
User             1 ──N── CreatorProfile
CreatorProfile   1 ──N── ChannelMetrics
CreatorProfile   1 ──N── Video
CreatorProfile   1 ──N── ImportRun
CreatorProfile   1 ──N── AnalysisRun
CreatorProfile   1 ──N── Recommendation
CreatorProfile   1 ──N── Experiment
Video            1 ──N── VideoMetrics
Video            1 ──N── FeatureVector
Video            1 ──N── Claim
AnalysisRun      1 ──N── RuleExecution
AnalysisRun      1 ──N── Evidence
AnalysisRun      1 ──N── Claim
AnalysisRun      1 ──N── Recommendation
Claim            N ──M── Evidence        (via claim_evidence)
Claim            1 ──N── Recommendation
Recommendation   1 ──N── RecommendationFeedback
Experiment       1 ──N── ExperimentResult
Recommendation   1 ──0N─ Experiment      (optional)
```

## Entity Groups

### Identity
Entities responsible for authentication and user management.

```
User ── ConnectedAccount
```

### Creator
Entities that model the content creator being analyzed.

```
CreatorProfile ── ChannelMetrics
                    Videos
                    ImportRuns
                    AnalysisRuns
                    Recommendations
                    Experiments
```

### Content
Entities that store imported video data and computed features.

```
Video ── VideoMetrics
     ── FeatureVector
     ── Claims
```

### Pipeline
Entities that track batch processing operations.

```
ImportRun
AnalysisRun ── RuleExecutions
           ── Evidence
           ── Claims
           ── Recommendations
```

### Intelligence
Entities that store analysis results.

```
RuleExecution
Evidence    ── Claim (
Claim       ── Evidence)   via claim_evidence
Recommendation ── Claim
```

### Validation
Entities that track experiment outcomes.

```
Experiment ── ExperimentResult
Recommendation ── RecommendationFeedback
```
