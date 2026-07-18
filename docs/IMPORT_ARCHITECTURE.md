# Import Architecture

> **Sprint 4B freeze** — do not modify without updating this document and recording the decision in the ADR section below.
>
> This document is **normative**: it specifies what must be true. Any implementation that violates these rules is incorrect by definition.

---

## Goals

| Goal | Description |
|------|-------------|
| **Provider-independent imports** | The import pipeline must never reference a specific provider (YouTube, TikTok, Twitch) outside the `ProviderAdapter` layer. |
| **Resumable execution** | Any import run interrupted mid-pagination must be resumable from the last checkpoint without data loss or duplication. |
| **Idempotent persistence** | Re-importing the same data must produce the same result — upserts, not inserts. No duplicate videos, no duplicate metrics. |
| **Single responsibility per layer** | Each layer in the architecture has exactly one job. Layer boundaries are enforced by interface contracts, not convention. |

---

## Layer Architecture

```
        API Route (thin)            Scheduler (future)       Profile Events (future)
               │                          │                         │
               └──────────────┬───────────┴─────────────┬───────────┘
                              │                         │
                              ▼                         ▼
                    ImportTriggerService          ImportTriggerService
                    (planned — single             (planned — single
                     entry point for               entry point for
                     all triggers)                 all triggers)
                              │
                              ▼
                     ImportCoordinator
                    (orchestration, lifecycle)
                              │
                              ▼
                      ImportJobFactory
                        (construction)
                              │
                              ▼
                        ImportJob
                   (execution, checkpoint-aware)
                         │          │
                         │          ▼
                         │  ImportRunRepository
                         │   (checkpoints)
                         ▼
                   ProviderAdapterFactory
                      (provider selection)
                              │
                              ▼
                       ProviderAdapter
                  (provider-specific API calls)
                              │
                              ▼
                         Repository
                         (persistence)
```

### API Route

| Attribute | Rule |
|-----------|------|
| **Responsibilities** | Validate request, call coordinator, return response |
| **Allowed dependencies** | `ImportCoordinator` |
| **Forbidden dependencies** | `ImportJob`, `ImportJobFactory`, `ProviderAdapter`, `Repository`, any model class |

In the future (Sprint 5+), routes will call `ImportTriggerService` instead of `ImportCoordinator` directly.

### ImportTriggerService (planned, Sprint 5)

| Attribute | Rule |
|-----------|------|
| **Responsibilities** | Single entry point for all import triggers (HTTP, scheduler, events, admin). Deduplicate concurrent requests. Apply trigger policies. Call `ImportCoordinator.run()`. |
| **Allowed dependencies** | `ImportCoordinator` |
| **Forbidden dependencies** | Any concrete `ImportJob`, any `ProviderAdapter`, `Repository`, `TokenManager` |
| **Return type** | `TriggerResult(import_run_id: UUID, status: ImportRunStatus)` — a value object, not a bare UUID |

### ImportCoordinator

| Attribute | Rule |
|-----------|------|
| **Responsibilities** | Load connected account, acquire token via `TokenManager`, extract resume state from prior run, create `ImportRun`, build `ImportContext`, delegate to `ImportJobFactory`, execute job, persist final run state, stamp `run_id` on result |
| **Allowed dependencies** | `ImportJobFactory`, `TokenManager`, `ConnectedAccountRepository`, `ImportRunRepository` |
| **Forbidden dependencies** | Any concrete `ImportJob`, any `ProviderAdapter`, any model class directly |

### ImportJobFactory

| Attribute | Rule |
|-----------|------|
| **Responsibilities** | Select and construct the correct `ImportJob` implementation for the requested provider + import type combination. Constructs and injects all lower-level dependencies (adapter, repository) into the job. |
| **Allowed dependencies** | `Provider` enum, `ImportType` enum, concrete `ImportJob` implementations, `ProviderAdapterFactory`, `AsyncSession` (forwarded to repository constructors) |
| **Forbidden dependencies** | Any provider adapter, repository, or token manager used **for the factory's own logic** (construction is allowed — dependence is not) |

**Note:** The factory creates repository instances from the `AsyncSession` it receives and passes them to jobs. This is construction, not dependence — the factory does not use repositories for its own orchestration. The "forbidden" rule targets layers that depend on repositories to make decisions; the factory is a construction coordinator and is exempt.

### ImportJob

| Attribute | Rule |
|-----------|------|
| **Responsibilities** | Execute a complete import of a single type (video, channel, metrics). Manage pagination loop. Write checkpoints to `ImportRunRepository` after each page. Delegate provider-specific API calls to `ProviderAdapter`. Delegate persistence to `Repository`. Implement retry with exponential backoff for retryable errors. |
| **Allowed dependencies** | `ProviderAdapter`, `Repository`, `ImportRunRepository` (all via constructor injection) |
| **Forbidden dependencies** | `ImportCoordinator`, `TokenManager`, any model class directly |
| **Entry point** | A single `execute(context, state)` method — the job checks `state.next_page_token` internally to determine fresh vs. resume |

**Rationale for allowing `ImportRunRepository`:** The job writes checkpoints after every completed page. Using a repository callback or injector pattern would add indirection without benefit — the job already has `ImportContext.run_id`. Allowing direct repository access keeps checkpointing simple and auditable.

### ProviderAdapterFactory

| Attribute | Rule |
|-----------|------|
| **Responsibilities** | Return the correct `ProviderAdapter` implementation for the given `Provider` enum value |
| **Allowed dependencies** | `Provider` enum, concrete `ProviderAdapter` implementations |
| **Forbidden dependencies** | `ImportJob`, `Repository`, `TokenManager` |

### ProviderAdapter

| Attribute | Rule |
|-----------|------|
| **Responsibilities** | Make provider-specific API calls, transform responses into typed DTOs, raise typed exceptions (`AuthenticationError`, `RateLimitError`, `ApiError`, `UnavailableError`) |
| **Allowed dependencies** | Provider SDKs/HTTP client, DTO types (`YouTubeVideoData`, etc.) |
| **Forbidden dependencies** | Any model class, any repository, `TokenManager` |

### Repository

| Attribute | Rule |
|-----------|------|
| **Responsibilities** | Persist and retrieve domain models. Implement upsert semantics for idempotent writes. |
| **Allowed dependencies** | SQLAlchemy, model classes |
| **Forbidden dependencies** | Any external API, any provider SDK, `TokenManager` |

---

## State Model

### ImportContext (immutable)

Created once at job start. Never modified.

```python
@dataclass(frozen=True)
class ImportContext:
    import_run_id: UUID
    creator_profile_id: UUID
    connected_account_id: UUID
    provider: str
    started_at: datetime
```

### ImportState (mutable)

Updated as the job progresses through pagination, checkpointing, and error recovery. No phase enum — the job
infers its phase from `next_page_token` and the adapter's discovery results.

```python
@dataclass
class ImportState:
    processed: int = 0
    total: int = 0
    next_page_token: str | None = None
    retries: int = 0
```

### ImportCheckpoint (persisted snapshot)

```python
@dataclass(frozen=True)
class ImportCheckpoint:
    next_page_token: str | None = None
    processed_count: int = 0
    total_count: int | None = None
```

Checkpoints are stored directly in `ImportRun` model fields (`last_page_token`, `processed_count`,
`total_count`), not as opaque blobs. This lets the coordinator reconstruct `ImportState` for resume
without needing a provider-specific deserializer.

### ImportResult (frozen return value)

```python
@dataclass(frozen=True)
class ImportResult:
    status: ImportRunStatus
    processed: int = 0
    inserted: int = 0
    updated: int = 0
    duration_ms: int = 0
    checkpoint: ImportCheckpoint | None = None
    run_id: UUID | None = None
```

### Resume Logic

The coordinator checks for a prior incomplete run before creating a new one:

```python
state = ImportState()
existing = await run_repo.get_last_pending_or_running(creator_profile_id)
if existing is not None and existing.last_page_token is not None:
    state.next_page_token = existing.last_page_token
    state.processed = existing.processed_count or 0
    state.total = existing.total_count or 0
```

The coordinator then creates a **new** `ImportRun` (even on resume) and passes the populated `ImportState`
to the job. The job checks `state.next_page_token`:

- If `None` → fresh import, start from beginning
- If set → resume, skip discovery, continue pagination from token

---

## Execution Lifecycle

```
Request
   │
   ▼
┌─────────────────────────────────────────────────────────────┐
│                   ImportCoordinator.run()                    │
│                                                              │
│   1. Load connected account  (ConnectedAccountRepository)     │
│        → None → raise ConnectedAccountNotFoundError          │
│                                                              │
│   2. Acquire access token  (TokenManager)                    │
│        → None → raise TokenAcquisitionError                  │
│                                                              │
│   3. Check for prior pending/running run  (ImportRunRepo)    │
│        → Populate ImportState for resume if applicable       │
│                                                              │
│   4. Create ImportRun  (status=RUNNING)                      │
│                                                              │
│   5. Build ImportContext (immutable run identity)            │
│                                                              │
│   6. Resolve ImportJob  (ImportJobFactory)                   │
│                                                              │
│   7. Execute job  (job.execute(context, state))              │
│        → On exception: mark run FAILED, re-raise             │
│                                                              │
│   8. Persist final status                                    │
│        → COMPLETED or FAILED  (ImportRunRepository)          │
│                                                              │
│   9. Stamp run_id on result, return                          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
   │
   ▼
Response
```

### Checkpointing

During execution, each `ImportJob` calls `run_repo.update_checkpoint()` after each completed page:

```python
await run_repo.update_checkpoint(
    run_id=context.import_run_id,
    next_page_token=state.next_page_token,
    processed_count=state.processed,
    total_count=state.total,
)
```

This persists `last_page_token`, `processed_count`, and `total_count` on the `ImportRun` row.
If the process is interrupted between checkpoints, the next invocation resumes from the last
saved state.

### Retry Strategy

Retryable errors (`RateLimitError`, `UnavailableError`) are retried with exponential backoff.
Non-retryable errors (`AuthenticationError`, `ApiError`) fail immediately. Retry logic lives
entirely inside `ImportJob` — the coordinator never retries.

---

## Typed Exceptions

All provider adapter errors are typed for unambiguous handling:

```
ProviderError (base)
├── AuthenticationError  → 401 — fail immediately, signal to coordinator
├── RateLimitError       → 429 — retry with backoff
├── ApiError             → 403/500 — fail immediately (permission, server error)
└── UnavailableError     → timeout/connection — retry with backoff
```

Coordinator maps its own exceptions for the API layer:

```
CoordinatorError (base)
├── ConnectedAccountNotFoundError → 404
└── TokenAcquisitionError         → 401
```

---

## Extension Rules

### Adding a new provider

1. Create a new `ProviderAdapter` implementation (e.g., `TikTokAdapter`)
2. Register it in `ProviderAdapterFactory`
3. Add the provider to the `Provider` enum
4. Do **not** modify any existing adapter unless fixing a bug
5. Do **not** modify `ImportJob` or `ImportCoordinator`

### Adding a new import type

1. Create a new `ImportJob` implementation (e.g., `CommentsImportJob`)
2. Register it in `ImportJobFactory`
3. Add the type to the `ImportType` enum
4. Create API route(s) in a new router module
5. Do **not** add provider-specific logic to the coordinator
6. Do **not** modify existing jobs

### General rules

| Rule | Enforcement |
|------|-------------|
| Repositories never call external APIs | Review import statements |
| Adapters never write to the database | Review return types |
| Coordinator never knows which concrete job is running | Only interacts through `ImportJobFactory` |
| Every job has exactly one entry point (`execute()`) | No `resume()` method on `ImportJob` interface |
| Retry strategy is per-job, not per-coordinator | No retry logic in `ImportCoordinator` |

---

## Architecture Decision Record (ADR)

### ADR-001: Single `execute()` entry point

**Status:** Accepted

**Context:** The initial design considered separate `execute()` and `resume()` methods. This would require the coordinator to branch on whether the run is new or resuming.

**Decision:** Use a single `execute(context, state)` method. The job checks `state.next_page_token` internally to determine whether to start fresh or resume.

**Consequence:** The coordinator never branches on resume vs. fresh. The job owns its lifecycle.

---

### ADR-002: Non-opaque checkpoint storage

**Status:** Accepted

**Context:** The initial design used an opaque `ImportCheckpoint` with a `provider_state: dict[str, Any]` field, intended to isolate provider-specific pagination tokens.

**Decision:** Store checkpoint fields (`last_page_token`, `processed_count`, `total_count`) directly on the `ImportRun` model. The `ImportCheckpoint` dataclass is a simple container, not an opaque blob. The coordinator reconstructs `ImportState` from model fields rather than deserializing provider-specific state.

**Rationale:** The current single-provider (YouTube) design doesn't need opaque storage. The `next_page_token` string pattern generalizes to any cursor-based pagination. If a future provider requires fundamentally different pagination (e.g., offset-based), an opaque checkpoint can be introduced at that point.

**Consequence:** Less indirection during debugging. The database schema is self-documenting for checkpoint state. Adding a provider with a different pagination model may require adding a `checkpoint_data: JSON` column later.

---

### ADR-003: Coordinator-driven resume

**Status:** Accepted

**Context:** Resume state could be extracted either by the coordinator (reading `ImportRun` fields and populating `ImportState`) or by the job (receiving the run ID and querying itself).

**Decision:** The coordinator reads the prior `ImportRun`, extracts `last_page_token`/`processed_count`/`total_count`, and populates `ImportState` before passing it to the job.

**Consequence:** The job is stateless with respect to the database — it receives all resume context through `state`. The coordinator owns the database interaction for lifecycle management. The job can be tested without a database.

---

### ADR-004: Repository Pattern

**Status:** Accepted

**Context:** Early code had database access scattered across services and API routes.

**Decision:** Encapsulate all database access in `Repository` classes. No layer above `Repository` may reference SQLAlchemy session or model classes directly for write operations.

**Consequence:** Persistence logic is testable in isolation. Changing the ORM or database affects only the repository layer.

---

### ADR-005: Provider Abstraction

**Status:** Accepted

**Context:** The initial import implementation called the YouTube Data API directly from the importer, coupling the import logic to YouTube-specific endpoints and pagination.

**Decision:** Introduce a `ProviderAdapter` interface and `ProviderAdapterFactory`. All provider-specific API calls are encapsulated behind this interface. The `ImportJob` depends only on the abstract interface.

**Consequence:** Adding YouTube, TikTok, Twitch — or any future provider — requires only a new adapter implementation and a factory registration. No changes to `ImportJob` or `ImportCoordinator`.

---

### ADR-006: Typed provider exceptions

**Status:** Accepted

**Context:** Early error handling used generic exceptions or HTTP status codes propagated across layers, making it impossible for jobs and coordinators to distinguish retryable from non-retryable errors without inspecting message strings.

**Decision:** Define a `ProviderError` hierarchy (`AuthenticationError`, `RateLimitError`, `ApiError`, `UnavailableError`). Adapters raise these typed exceptions. Jobs check exception type to determine retry behavior. Coordinators map specific exceptions to HTTP responses.

**Consequence:** Error handling is unambiguous at every layer. Adding a new error type requires no changes to existing error-handling branches.

---

### ADR-007: Coordinator acquires token before creating ImportRun

**Status:** Accepted

**Context:** During implementation, token acquisition could fail (expired refresh token, revoked access). If the `ImportRun` is created before token acquisition, every token failure would produce a failed run in the database, even though no work was attempted.

**Decision:** Acquire the token first. Only create the `ImportRun` after the token is confirmed valid. If token acquisition fails, no database record is created.

**Consequence:** No "failed" runs in the database for token acquisition failures. The tradeoff is that token acquisition errors are invisible in run history — the caller gets an immediate error response with no persisted record.

---

### ADR-008: Coordinator stamps `run_id` on result (not the job)

**Status:** Accepted

**Context:** The `ImportResult` dataclass has a `run_id` field. The job could set it directly, but it doesn't know the `ImportRun` ID (it only receives the `ImportContext`). Alternatively, the coordinator could stamp it after execution.

**Decision:** The coordinator assigns `run_id` by calling `dataclasses.replace(result, run_id=run.id)` before returning. The job never writes `run_id`.

**Consequence:** The job produces a pure result — no side effects on the result's identity fields. The coordinator is the single source of truth for associating results with runs.

---

### ADR-009: No ImportPhase enum

**Status:** Accepted (reversed from initial design)

**Context:** The initial design specified an `ImportPhase` enum (`INITIALIZING`, `DISCOVERING`, `IMPORTING`, `FINISHING`, `COMPLETED`) to make recovery deterministic by recording which phase a run was in at each checkpoint. During implementation, it became clear that `DISCOVERING` vs `IMPORTING` is implicitly determined by the presence of `next_page_token` and the state of the adapter's discovery results.

**Decision:** Remove the `ImportPhase` enum. The job infers its phase from `state.next_page_token`: if set, skip discovery and resume pagination; if unset, start fresh with discovery.

**Consequence:** Less state to persist and test. Resume correctness depends on the checkpoint having a valid `next_page_token`. If a future use case requires phase-level granularity (e.g., "resume discovery only"), the enum can be reintroduced.

---

### ADR-010: `TriggerResult` value object for `ImportTriggerService` (planned)

**Status:** Deferred to Sprint 5

**Context:** The `ImportTriggerService` will be the single entry point for all import triggers. Returning a bare `UUID` from `trigger()` makes it impossible to add metadata later without changing the signature.

**Decision:** When implemented, `ImportTriggerService.trigger()` will return a `TriggerResult` value object:

```python
@dataclass(frozen=True)
class TriggerResult:
    import_run_id: UUID
    status: ImportRunStatus
```

**Consequence:** Future fields (`already_running`, `resumed`, `queued`) can be added without changing the method signature. The tradeoff is one additional type to maintain.

---

### ADR-011: Factory Pattern over Switch Statements

**Status:** Accepted

**Context:** Early implementation used conditional logic (if/elif chains) to select provider adapters and import jobs. This approach had three problems: (1) every new provider or import type required modifying existing code, violating the Open/Closed Principle; (2) conditional branches were duplicated across the legacy `ImportService` and the new coordinator layer; (3) testing required enumerating every branch to ensure coverage.

**Decision:** Use two dedicated factories — `ProviderAdapterFactory` and `ImportJobFactory` — for provider and job selection respectively. The target pattern is a registry-based lookup where each factory maintains a mapping from enum key to implementation class, and adding a new provider or import type requires only a new class and a single registration line.

**Current state:** `ProviderAdapterFactory` already uses a dict registry (`_registry: dict[Provider, type[ProviderAdapter]]`). `ImportJobFactory` currently uses a conditional chain internally (acceptable while only one provider+type combination exists) and is expected to migrate to a registry when more combinations are added.

**Consequence:** Provider and job selection is centralized and testable in isolation. Adding YouTube Channel import or TikTok video import requires no changes to `ImportCoordinator` or the API route layer. The tradeoff is two additional abstraction classes, justified by the extension frequency expected across 4+ providers and 3+ import types.

---

### ADR-012: Event-Driven Pipeline — Commit-Before-Event

**Status:** Accepted (Sprint 5)

**Context:** Sprint 5 introduces asynchronous pipeline triggers (OAuth completion events, scheduler, API calls). This creates a distributed-systems concern the import subsystem did not previously have: an event may arrive at `ImportTriggerService` before the transaction that created the underlying state has committed. If the trigger service reads from the database before the transaction is visible, it will see stale or missing data.

This ordering problem does not affect synchronous API calls (the caller waits for a response), but it is critical for event-driven paths where the producer and consumer are decoupled.

**Decision:** Domain events must never be published before the transaction that creates the underlying state has successfully committed. The required order is:

```
BEGIN TRANSACTION
    Create domain entity (ConnectedAccount, MetricSnapshot, etc.)
COMMIT TRANSACTION
    ↓
PUBLISH domain event (ConnectedAccountCreated, MetricSnapshotCreated, etc.)
    ↓
ImportTriggerService or downstream stage
```

The inverse order (publish before commit) is explicitly forbidden.

**Outbox pattern:** The architecture targets an outbox pattern as the durable evolution of commit-before-event, but does not require it for Sprint 5A. The immediate implementation publishes directly after commit. When the system requires stronger delivery guarantees (multiple consumers, at-least-once delivery), the publish call is replaced with an outbox row insert + worker without changing the trigger service:

```
# Sprint 5A (direct publish)
await db.commit()
await event_bus.publish(ConnectedAccountCreated(...))

# Future (outbox)
await db.commit()
# outbox worker reads OutboxEvent table and publishes
```

**Event publication table:** Not every artifact should publish an event. Publication is an explicit property:

| Artifact | Publish Event? | Reason |
|----------|---------------|--------|
| `ConnectedAccount` | ✅ | Starts ingestion |
| `ImportRun` | ❌ | Internal lifecycle |
| `MetricSnapshot` | ✅ | Starts feature extraction |
| `FeatureVector` | ✅ | Starts rule evaluation |
| `Finding` | ✅ | Starts evidence generation |
| `Evidence` | ✅ | Starts claim generation |
| `Claim` | ✅ | Starts recommendation generation |
| `Recommendation` | ❌ | Terminal artifact (unless experiments are enabled) |

**Consequence:** The trigger service never needs to retry due to uncommitted state. The outbox evolution path is preserved without premature infrastructure. The tradeoff is that direct publish after commit is not transactional — if the publish fails, the event is lost (acceptable at Sprint 5A scale; the next scheduled import or manual trigger compensates).

**Implementation note (Sprint 5A):** The OAuth callback in the auth route currently commits the session inside `get_db()`'s cleanup (FastAPI dependency). The `ConnectedAccountCreated` event must be published *after* `get_db()` completes, not inside the route handler. The event publisher should be called in a FastAPI `after_request` handler or in the caller of the OAuth flow, not inside the transactional boundary.

---

### ADR-013: `ImportTrigger` value object

**Status:** Accepted (Sprint 5)

**Context:** Multiple trigger sources (API, events, scheduler, manual) each carry different metadata about why an import was initiated. Without a standard trigger object, the `ImportTriggerService` would need to extract meaning from caller-specific parameters, and `ImportRun` records would lack provenance data.

**Decision:** All trigger sources construct an `ImportTrigger` value object before calling `ImportTriggerService.trigger()`:

```python
@dataclass(frozen=True)
class ImportTrigger:
    trigger_type: TriggerType
    creator_profile_id: UUID
    connected_account_id: UUID
    requested_at: datetime
    initiated_by: UUID | None  # user who requested it, if applicable
```

The trigger is recorded on the resulting `ImportRun` for observability.

**Trigger types:**

```python
class TriggerType(str, Enum):
    API = "api"
    EVENT = "event"
    SCHEDULE = "schedule"
    MANUAL = "manual"
```

**Consequence:** Every import run records its origin, enabling analytics (which triggers fail most often, which produce the most recommendations). The service is decoupled from its callers — it consumes one immutable contract regardless of the trigger source.

---

### ADR-014: Trigger SLAs are caller responsibility, not coordinator responsibility

**Status:** Accepted (Sprint 5)

**Context:** Different trigger sources have different latency and failure-handling requirements:

| Trigger | Expected Latency | Failure Handling |
|---------|-----------------|------------------|
| OAuth completion | Seconds | Retry immediately or surface to user |
| API / manual | Seconds | Return structured error |
| Scheduler | Minutes acceptable | Retry with backoff and alert on repeated failures |

Encoding these policies in `ImportCoordinator` would couple orchestration logic to transport concerns.

**Decision:** The coordinator does not behave differently based on trigger source. The caller (API handler, event handler, scheduler task) is responsible for setting retry policies, timeout expectations, and user-facing error messages. The coordinator produces a `TriggerResult`; the caller decides what to do with it.

**Consequence:** The `ImportCoordinator` remains trigger-agnostic. Adding a new trigger type never requires coordinator changes. The tradeoff is that retry policy is distributed across trigger handlers rather than centralized, but this is acceptable because each handler has fundamentally different recovery semantics.

---

## Build Order

Bottom-up implementation with integration checkpoints:

| Step | Layer | Verification |
|------|-------|-------------|
| 1 | `ProviderAdapter` — `YouTubeAdapter` with typed DTOs and exceptions | Unit test with mocked HTTP |
| 2 | `ProviderAdapterFactory` | Unit test returns correct adapter per enum |
| 3 | `VideoImportJob` — pagination, checkpointing, retry | Unit test with mocked adapter (29 tests) |
| 4 | `ImportJobFactory` | Unit test returns correct job per provider+type |
| 5 | `ImportCoordinator` | Integration test with mocked job factory (16 tests) |
| 6 | API routes — `POST /api/import/videos`, `GET /api/import/status` | Full integration test (8 tests) |
| 7 | Legacy removal — delete `ImportService`, old `YouTubeImporter` | 90 tests still pass after deletion ✅ |
| — | — | — |
| 8 | `ImportTriggerService` + `ImportTrigger` + `TriggerResult` | Integration test (Sprint 5A open) |
| 9 | Event wiring — `ConnectedAccountCreated` → `ImportTriggerService` | E2E test with mocked event bus (Sprint 5A) |
| 10 | `MetricsCollector` + `MetricSnapshot` | Unit test with mocked repository (Sprint 5A) |
| 11 | `FeatureExtractor` + `FeatureVector` | Unit test with known metric inputs (Sprint 5B) |
| 12 | `RuleEngine` + `Finding` | Unit test with known feature vectors (Sprint 6) |
| 13 | `EvidenceEngine` + `Evidence` | Unit test with known findings (Sprint 7) |
| 14 | `ClaimEngine` + `Claim` | Unit test with known evidence (Sprint 8) |
| 15 | `RecommendationEngine` + `Recommendation` | Unit test with known claims (Sprint 9) |
| 16 | `LearningEngine` + `KnowledgeBase` | Integration test with experiments (Sprint 10) |

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 2.2 | 2026-07-18 | — | Sprint 5 preview — add ADR-012 (commit-before-event), ADR-013 (ImportTrigger), ADR-014 (trigger SLAs), update build order with pipeline stages 8-16 |
| 2.1 | 2026-07-18 | — | Sprint 4B complete — clarify factory dependency rules, update ImportJob deps (add ImportRunRepository), add ADR-011 (factory pattern) |
| 2.0 | 2025-07-18 | — | Sprint 4B freeze — reflect actual implementation (non-opaque checkpoint, no ImportPhase, coordinator-driven resume, typed exceptions, trigger service planned) |
| 1.0 | 2025-06-15 | — | Sprint 4A freeze — initial architecture spec |

## Change Rule

Any architectural change (new layer, changed interface, modified responsibility, added dependency) **must** update this document and add a new ADR entry in the same commit.
