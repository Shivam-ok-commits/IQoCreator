# IQoCreator — Sprint Roadmap

## Definition of Done

A sprint is complete **ONLY** if all of the following are true:

- [ ] Builds successfully
- [ ] Database migrations run on a clean database
- [ ] Backend starts without errors
- [ ] Frontend starts without errors
- [ ] End-to-end user flow works
- [ ] No placeholder or stub code
- [ ] No dead code
- [ ] No unused files
- [ ] No TODO comments
- [ ] Documentation updated
- [ ] Previous sprint contract not violated

---

## Capability Principle

> Every sprint must leave the user with a new capability they can actually use.
>
> Sprint 3 → connect a YouTube account.
> Sprint 4 → import videos.
> Sprint 5 → see imported videos in the UI.
> Sprint 6 → see extracted metrics.
> Sprint 7 → receive the first recommendation.

---

## Sprint 1 — Foundation ✅

## Sprint 1 — Foundation ✅
**Goal:** Production-quality project skeleton running locally.

**Delivered:**
- FastAPI backend with configuration, database layer, Alembic, health endpoint
- Next.js 15 frontend with TailwindCSS, shadcn/ui
- Docker Compose (PostgreSQL + Redis + Backend + Frontend)
- Requirements pinned, README with setup instructions

**Success criteria:**
- `GET /health` returns `{"status": "ok"}`
- Backend starts, connects to PostgreSQL, runs migrations
- Frontend builds and renders

---

## Sprint 2 — Database Schema ✅
**Goal:** Complete, frozen database schema with all models, relationships, constraints, and migration.

**Delivered:**
- 16 tables across 6 domains: Identity, Creator, Content, Pipeline, Intelligence, Validation
- 21 foreign keys with explicit cascade rules
- 17 indexes on query-heavy columns
- 6 status enums, 7 JSONB fields (each justified)
- `docs/DATABASE_SCHEMA.md`, `docs/ENTITY_RELATIONSHIPS.md`, `docs/PIPELINE_ARCHITECTURE.md`
- `SPRINT_2_FREEZE.md` — architecture contract (future sprints may ADD, not RENAME/DROP)

**Success criteria:**
- `alembic upgrade head` applies both migrations cleanly
- PostgreSQL contains exactly 16 tables with all constraints

---

## Sprint 3 — Identity
**Goal:** Authenticate a YouTube creator via Google OAuth. Nothing else.

**Architecture decision:** Google OAuth is the sole identity provider. No JWT, no email/password, no user management system. YouTube is the identity source. This can be expanded later if a real need emerges.

**Scope:**
- Google OAuth flow (login, callback, token exchange)
- User creation (if new user)
- ConnectedAccount creation (OAuth tokens stored)
- CreatorProfile creation (from YouTube channel data)
- Session handling (login/logout)
- Refresh token storage (encrypted)
- OAuth error handling
- Integration tests

**Explicitly NOT built:**
- Video import ❌
- Channel sync ❌
- Metrics ❌
- Feature extraction ❌
- Rules ❌
- Evidence ❌
- Claims ❌
- Recommendations ❌
- Experiments ❌
- Pipeline ❌
- Dashboard analytics ❌
- JWT authentication ❌
- Email/password login ❌

**Acceptance criteria (checklist):**

- [ ] Click "Connect YouTube"
- [ ] Google consent screen opens
- [ ] User grants permission
- [ ] OAuth callback succeeds
- [ ] User row created
- [ ] ConnectedAccount row created
- [ ] CreatorProfile row created
- [ ] Refresh token encrypted and stored
- [ ] Browser redirected to /connected
- [ ] Refresh page → user remains logged in
- [ ] Logout → session destroyed

**Database state on completion:**
| Table | Expected rows |
|-------|--------------|
| `users` | 1 |
| `connected_accounts` | 1 |
| `creator_profiles` | 1 |
| All other tables | 0 |

**Frontend state on completion:**
- "✓ YouTube account connected successfully"
- Channel name displayed
- "Continue →" button (no dashboard, no analytics)

---

## Sprint 4 — Import
**Goal:** Import a YouTube creator's videos into the database.

**Scope:**
- YouTube Data API integration (video list + video details)
- ImportRun creation and execution
- Video + VideoMetrics persistence
- Transcript fetching (YouTube captions API)
- ImportRun status tracking
- Error handling (rate limits, missing videos, partial failures)

**Explicitly NOT built:**
- Metrics enrichment ❌
- Feature extraction ❌
- Analysis ❌
- Recommendations ❌

**Success criteria:**
- Running import fetches real videos from YouTube API
- `videos` table contains imported videos with metadata
- `video_metrics` table contains initial engagement snapshots
- Failed imports are recorded with error messages
- Database: `videos > 0`, all other analysis tables = 0

---

## Sprint 5 — Metrics
**Goal:** Enrich imported videos with time-series engagement metrics.

**Scope:**
- VideoMetrics enrichment (periodic snapshots)
- ChannelMetrics collection (periodic snapshots)
- Metric history tracking
- Stale metric detection

**Explicitly NOT built:**
- Feature extraction ❌
- Analysis pipeline ❌
- Rule engine ❌

**Success criteria:**
- Multiple VideoMetrics rows per video over time
- ChannelMetrics rows with subscriber/view counts
- Metrics are queryable by time range

---

## Sprint 6 — Feature Extraction
**Goal:** Compute and store feature vectors for imported videos.

**Scope:**
- FeatureVector creation pipeline
- Feature types: topic, sentiment, toxicity (or as designed)
- Model versioning per vector
- Batch feature extraction for existing videos

**Explicitly NOT built:**
- Rule execution ❌
- Claim extraction ❌
- Recommendations ❌

**Success criteria:**
- FeatureVectors exist for all imported videos
- Vectors are queryable by feature_type and video_id

---

## Sprint 7 — Rule Engine
**Goal:** Build the rule execution framework that powers analysis.

**Scope:**
- Rule interface/abstract base
- Rule registry (discover and register rules)
- Rule execution lifecycle (input → execute → output)
- Rule versioning
- RuleExecution persistence

**Explicitly NOT built:**
- Domain-specific rules (claims, evidence, recommendations) ❌
- AnalysisRun orchestration ❌

**Success criteria:**
- Rules can be registered, executed, and timed
- RuleExecutions are persisted with input/output snapshots
- A "hello world" rule executes end-to-end

---

## Sprint 8 — Evidence
**Goal:** Extract and store evidence from video content.

**Scope:**
- Evidence extraction rules (transcript, description)
- Evidence persistence with source tracking
- Evidence → Claim association (via claim_evidence join table)
- Evidence confidence scoring

**Success criteria:**
- Evidence items are extracted from video data
- Evidence is persisted with source_url and content
- Evidence can be associated with Claims (once Sprint 9 exists)

---

## Sprint 9 — Claim Engine
**Goal:** Extract claims from video content and associate with evidence.

**Scope:**
- Claim extraction rules
- Claim → Evidence association
- Claim status management (unverified → verified/debunked/uncertain)
- Claim versioning

**Success criteria:**
- Claims are extracted from video content
- Claims are linked to supporting/refuting evidence
- Claim statuses can be updated

---

## Sprint 10 — Recommendation Engine
**Goal:** Generate actionable recommendations from claims.

**Scope:**
- Recommendation generation rules
- Recommendation → Claim linking
- Recommendation status workflow (draft → reviewed → approved/rejected/archived)
- Recommendation priority scoring

**Success criteria:**
- Recommendations are generated from claims
- Recommendations have priority scores
- Recommendations flow through the status workflow

---

## Sprint 11 — Experiments
**Goal:** Track A/B experiments on recommendations.

**Scope:**
- Experiment creation (based on recommendations)
- ExperimentResult recording
- Experiment → Recommendation linking
- Experiment status tracking (draft → running → completed/cancelled)

**Success criteria:**
- Experiments can be created from recommendations
- Experiment results are persisted with metric values
- Experiments show completion status

---

## Sprint 12 — Inspector
**Goal:** Build the pipeline inspection UI for debugging and monitoring.

**Scope:**
- ImportRun history view
- AnalysisRun detail view
- RuleExecution inspection (input/output snapshots)
- Pipeline timing breakdown
- Error log visualization

**Success criteria:**
- All pipeline runs are visible in the inspector
- Rule input/output snapshots are inspectable
- Pipeline timing (duration_ms) is visualized

---

## Sprint 13 — Frontend
**Goal:** Build the main creator dashboard and analysis UI.

**Scope:**
- Creator dashboard (channel overview)
- Video list with metrics
- Claim browser with evidence
- Recommendation queue
- Experiment dashboard
- Responsive design

**Success criteria:**
- All core views render with real data
- Navigation flows naturally between views
- Mobile-responsive layout

---

## Sprint 14 — Validation
**Goal:** End-to-end validation and hardening.

**Scope:**
- Full E2E test suite
- Error handling review
- Performance testing (100+ videos, multiple creators)
- Security review (OAuth token storage, API auth)
- Documentation audit

**Success criteria:**
- E2E tests cover all 13 previous sprints
- Performance tests pass with realistic data volumes
- Security review passes

---

## Sprint 15 — Beta
**Goal:** Prepare for beta launch.

**Scope:**
- Production configuration finalization
- Monitoring and alerting
- Rate limiting
- User feedback collection
- Launch checklist

**Success criteria:**
- System runs in production-like environment
- Monitoring dashboard operational
- Beta users can authenticate and onboard

---

# Beyond Sprints — Architectural Freeze & Next Milestones

The core architecture (Pipeline → Domain Models → Presentation) is declared frozen as of the Growth Review implementation.

## Freeze Rules

No new core abstractions may be introduced unless they satisfy **at least one** of:
1. Simplify an existing abstraction.
2. Enable a capability that cannot be built with the current model.
3. Reduce coupling between layers.

Everything else should be implemented within the existing architecture.

## Next Milestones

### Milestone 1: Longitudinal Coaching

**What to build:**
- `GrowthMemory` domain object (recurring strengths/weaknesses, successful/failed experiments, stable/abandoned patterns, strategy summary, confidence over time)
- Growth Review history endpoint and timeline UI
- Experiment timeline (visual history of completed experiments)

**Success criterion:** A creator can understand six months of progress in under two minutes.

### Milestone 2: Prediction Validation

**What to build:**
- `Prediction` model (metric, baseline, expected_range, deadline, confidence, actual_value, outcome)
- Accuracy tracking per recommendation type
- Confidence calibration ("we've been right X% of the time on this type of prediction")

**Success criterion:** The system can say not only what it predicts, but how often similar predictions have been correct.

### Milestone 3: AI Coach

**What to build:**
- Natural language interface grounded entirely in `GrowthReview`, `GrowthMemory`, and `Experiment` data
- Every answer references evidence already known about the creator (no generic YouTube advice)
- Answers cite specific Growth Reviews, experiments, and mission outcomes as sources

**Success criterion:** Every answer references evidence already known about the creator.
