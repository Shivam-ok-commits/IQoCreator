# Agent Execution Protocol

> **Never confuse momentum with progress. If required information is missing, stopping is the correct behavior.**
>
> This document overrides all implementation behavior. Every task follows these phases in order. No phase may be skipped. No phase may be combined.

---

## Phase 0 — Requirements Audit

Before writing any code, determine whether implementation is possible.

**Three categories of requirements:**

| Category | Description | Blocks? |
|----------|-------------|---------|
| **USER PROVIDED** | Secrets, credentials, keys — only the user has these | YES — STOP |
| **USER CONFIRMATION** | Infrastructure state, account existence — the agent should attempt to verify automatically first, ask only if verification fails | YES — STOP, but only after attempting verification |
| **IMPLEMENTATION DEFAULTS** | Config classes, .env values, dev URLs — the agent creates these using sensible defaults | NO — create automatically |

**If a USER PROVIDED or USER CONFIRMATION item is missing:**

STOP. Do not write code. Do not create placeholder code. Do not generate TODOs. Do not invent values. Do not continue.

Produce the following block exactly (tool-agnostic — never reference terminals, shells, or specific tooling):

```
──────────────────────────────
REQUIREMENTS AUDIT

Ready: YES / BLOCKED

USER MUST PROVIDE
□ [item]
□ [item]

USER MUST CONFIRM
□ [item]
   Status: Not verified
   Evidence: [verification result or why unavailable]

□ [item]
   Status: Not verified
   Evidence: [verification result or why unavailable]

AGENT WILL CREATE
✓ [item]
✓ [item]

Summary
Waiting for: [N] provided values, [M] confirmations

No code written.
──────────────────────────────
```

**Report format rules:**
- USER MUST PROVIDE items have no Evidence — only the user knows these values
- USER MUST CONFIRM items MUST include Status and Evidence for every item
- AGENT WILL CREATE items use checkmarks — these are not blockers
- The last line MUST be "No code written." to make protocol compliance explicit

> **Only external dependencies provided by the user may block implementation. Internal project configuration should be created by the agent using sensible development defaults unless the user specifies otherwise.**

Resume implementation only after all USER PROVIDED items have been supplied and all USER CONFIRMATION items have been resolved.

---

## Evidence Rule

When reporting a blocker, separate it into precisely three categories:

1. **User must provide** — values only the user can supply (secrets, credentials, API keys, domain names)
2. **User must confirm** — state the agent attempted but could not verify automatically
3. **Agent will generate** — implementation defaults the agent creates automatically

**Verification hierarchy (apply in this order):**

1. **Verify automatically** — attempt to connect, call API, check service health
2. **Ask for confirmation** — only when automatic verification fails or is impossible
3. **Ask for values** — only when the user is the sole source of truth

**Examples:**

| Instead of asking | Do this |
|-------------------|---------|
| "Is PostgreSQL running?" | Attempt connection → report result → if failed: "Action required: Start PostgreSQL" |
| "Is YouTube Data API enabled?" | Call the API after OAuth → specific error proves disabled → report: "Enable YouTube Data API v3" |
| "What is your Client ID?" | Ask — only the user has this value |

**General principle:** The protocol should evolve toward this hierarchy: Verify automatically whenever possible. Ask for confirmation only when automatic verification is impossible. Ask for values only when the user is the only source of truth (API secrets, credentials, domain names, etc.).

**Never ask the user for something the agent can determine automatically. Never ask the user to confirm something the agent can verify automatically.**

---

## Phase 0.5 — Scope Lock

Before implementation, explicitly define what is and is not within scope.

**Deliver:**

```
IN SCOPE
- Item 1
- Item 2
- ...

OUT OF SCOPE
- Item 1
- Item 2
- ...
```

**Rules:**

- The agent may NOT create files, APIs, models, database tables, frontend pages, or abstractions outside the IN SCOPE list.
- The IN SCOPE list comes from the sprint's goal and acceptance criteria. It is not negotiable.
- The OUT OF SCOPE list is equally important. It prevents "while I'm here" creep.

**If implementation reveals a need outside the IN SCOPE list:**

1. STOP
2. Report the need
3. Do NOT implement it
4. Wait for approval

> "While I'm here" is the most dangerous phrase in software architecture.

---

## Phase 1 — Architecture Review

Review the existing project before writing any new code.

**Actions:**

- Read existing models, APIs, services, repositories, and configuration
- Understand naming conventions, patterns, and code style
- Identify existing code that satisfies the requirement

**Rules:**

- Reuse existing code. Never duplicate functionality.
- Extend existing code. Never rewrite it without reason.
- Never rename files without reason.
- Never reorganize folders without reason.
- Never change public interfaces unless required.

---

## Phase 2 — Implementation Plan

Before writing code, produce an implementation plan.

**Deliver:**

| Item | Description |
|------|-------------|
| Files to create | List of new files with their purpose |
| Files to modify | List of existing files and what changes |
| Database changes | New tables, columns, indexes, migrations |
| API changes | New endpoints, modified routes, request/response schemas |
| Frontend changes | New pages, components, hooks, services |
| Migration impact | Whether existing data is affected, rollback strategy |
| Potential risks | Areas of uncertainty, failure modes, security concerns |

**Decision Gate:**

If there are multiple reasonable implementation choices:

1. Present each option with its pros and cons
2. Recommend one
3. Wait for approval before implementing

```
DECISION GATE

Option A: [name]
Pros:
- ...
Cons:
- ...

Option B: [name]
Pros:
- ...
Cons:
- ...

Recommendation: [A/B]
Waiting for approval.
```

Do not choose an option without presenting tradeoffs.

---

## Phase 3 — Implementation

Only after all previous phases have completed successfully.

**Rules:**

- No placeholders. Never write: `TODO`, `FIXME`, `placeholder`, `dummy`, `change-me`, `replace-me`, `example-key`, `your-api-key`
- No empty environment variables. If a real value is required, stop and ask.
- No invented secrets or credentials. The agent may not assume defaults.
- Vertically complete. Every feature must be fully wired: Database → Repository → Service → API → Frontend → Test → Verification.
- Never break a previous sprint to implement a new one.
- Google OAuth is the sole identity provider. No JWT, no email/password, no user management system.

---

## Phase 4 — Verification

After implementation, verify that the sprint is complete.

**Checklist:**

- [ ] Build succeeds (backend + frontend)
- [ ] Database migrations run on a clean database
- [ ] Backend starts without errors
- [ ] Frontend starts without errors
- [ ] End-to-end user flow works
- [ ] Regression check: all previous sprints still functional
- [ ] No placeholder or stub code
- [ ] No dead code or unused files
- [ ] No TODO comments
- [ ] Documentation updated
- [ ] Sprint 2 freeze contract not violated

---

## Phase 5 — Summary

Produce a complete summary of what was delivered.

**Deliver:**

| Item | Description |
|------|-------------|
| Files created | List with purpose |
| Files modified | List with change summary |
| Database changes | Tables, columns, migrations |
| API changes | Endpoints, schemas |
| Frontend changes | Pages, components |
| Tests added | What was tested |
| Known limitations | What does not work yet |
| Next sprint | Recommended next step |

---

## Phase 6 — Completion Audit

Before marking a sprint complete, verify the user story — not just the build.

**Answer every question:**

| Question | Answer |
|----------|--------|
| Did the requested user story work? | YES / NO |
| Can the feature be demonstrated? | YES / NO |
| What database rows were created? | [list] |
| What API endpoints changed? | [list] |
| What frontend pages changed? | [list] |
| What manual steps verify it? | [steps] |
| Did this sprint violate ROADMAP? | YES / NO |
| Did this sprint violate SPRINT_FREEZE? | YES / NO |
| What technical debt was introduced? | [list or NONE] |

**Only after this audit may the sprint be declared complete.**

---

## Phase 7 — Critical Self Review

Before declaring the sprint complete, critique your own work. Do not skip this phase.

**Answer every question:**

1. **What assumptions did I make?**
   - List every assumption that could be wrong

2. **What could be wrong?**
   - Think about edge cases, race conditions, auth failures, missing error handling

3. **Which part of the implementation is least trustworthy?**
   - Be honest. What would you fix if you had more time?

4. **What would an experienced engineer review first?**
   - Security? Error handling? Data integrity? Performance?

5. **If this sprint failed tomorrow, what is the most likely root cause?**
   - Not "None." Every project has risk. Identify it.

**This phase exists because your own assessment is the most valuable feedback you will receive before shipping.**

---

## Information That Requires Stopping

The following types of information may **never** be invented, assumed, or defaulted. If any of these are required and not provided by the user, implementation must stop:

- Google Client ID
- Google Client Secret
- OpenAI API key
- YouTube Data API key
- Stripe Secret Key
- Domain name
- OAuth Redirect URI
- Production URLs
- Database passwords
- Database host/port (unless localhost defaults are confirmed)
- SMTP credentials
- Webhook secrets
- Cloud credentials (AWS, GCP, etc.)
- Any secret, token, or credential

The agent may not:
- Assume defaults for sensitive configuration
- Generate placeholder values like `change-me` or `your-api-key`
- Continue implementing while missing required credentials
- Leave empty environment variables in `.env` files

**Correct behavior:** Stop. Produce the Requirements Audit block. Ask the user for the missing information.

---

## Protocol Freeze

> **This protocol is frozen during feature development.**

- Do not modify this document during feature implementation.
- Protocol changes require an explicit user request.
- Feature implementation may not alter governance.
- If a protocol rule conflicts with a user request, obey the user and flag the conflict.

This prevents the agent from quietly editing its own operating rules while implementing unrelated features. The protocol is the contract — it stays stable while the product grows.
