# IQoCreator — Project Context

> A snapshot of the project's current state. Updated at the start of each sprint.

---

## Project

**Name:** IQoCreator
**Purpose:** Help YouTube creators grow using deterministic, explainable recommendations.

---

## Current Sprint

**Sprint 3 — Identity**
Goal: Connect a YouTube account via Google OAuth. Nothing else.

---

## Current Architecture

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI |
| Database | PostgreSQL (SQLAlchemy 2.x, Alembic) |
| Cache | Redis |
| Frontend | Next.js 15, React 19, TailwindCSS |
| Auth | Google OAuth (sole identity provider) |

---

## Current Pipeline

Not implemented yet. Sprint 3 is the first functional sprint.

---

## Completed

| Sprint | Status |
|--------|--------|
| Sprint 1 — Foundation | ✅ FastAPI + Next.js skeleton, Docker Compose, health endpoint |
| Sprint 2 — Database Schema | ✅ 16 tables, 21 FKs, 17 indexes, Alembic migrations |
| Governance | ✅ Constitution, Roadmap, Freeze, Engineering Rules, Agent Protocol |

---

## Current Goal

Connect a YouTube account successfully:

```
Click "Connect YouTube" → Google consent screen → Grant permission →
OAuth callback → User + ConnectedAccount + CreatorProfile created →
Redirect to /connected → Refresh → Still logged in → Logout → Session destroyed
```

---

## Out of Scope (Current Sprint)

- Import
- Analysis
- Recommendations
- Experiments
- Pipeline
- Dashboard analytics

---

## Next Sprint

**Sprint 4 — Import:** Import a creator's YouTube channel and videos into the database.

---

## Key Documents

| Document | Purpose |
|----------|---------|
| `docs/PROJECT_CONSTITUTION.md` | Philosophy and principles |
| `docs/ROADMAP.md` | Sprint plan and Definition of Done |
| `docs/SPRINT_2_FREEZE.md` | Database schema contract |
| `docs/ENGINEERING_RULES.md` | Coding standards |
| `docs/AGENT_EXECUTION_PROTOCOL.md` | Agent behavior phases |
