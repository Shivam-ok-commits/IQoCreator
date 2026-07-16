# Engineering Rules

> **Execution protocol:** All implementation work must follow the phases in `docs/AGENT_EXECUTION_PROTOCOL.md`. That document overrides any conflicting behavior described here.

## Rule 1 — No Regression

> Never break a previous sprint to implement a new one.
>
> Every sprint must remain fully functional after the next sprint.
>
> Regression is treated as a failed sprint.

**Enforcement:**
- Before marking a sprint complete, verify that all previous sprints' end-to-end flows still work
- If a change causes a regression in an earlier sprint, the change must be reverted or fixed before the sprint can ship
- CI must include regression tests that cover all completed sprints

---

## Rule 2 — Capability Principle

> Every sprint must leave the user with a new capability they can actually use.

| Sprint | Capability Delivered |
|--------|---------------------|
| 3 | Connect a YouTube account |
| 4 | Import videos |
| 5 | See imported videos in the UI |
| 6 | See extracted metrics |
| 7 | Receive the first recommendation |

If a sprint cannot be framed as a user-facing capability, it is not a sprint — it is infrastructure. Infrastructure-only sprints are permitted only for Sprint 1 (Foundation) and Sprint 2 (Database Schema). From Sprint 3 onward, every sprint delivers working software.

---

## Rule 3 — Architecture Freeze

> Before implementing a sprint, verify that it does not violate the Sprint 2 freeze contract.

- Tables and columns may be **added**
- Tables and columns may **not** be renamed or dropped without explicit approval
- FK rules may **not** be changed without explicit approval
- Violations must be flagged during code review before any code is written

---

## Rule 4 — No Speculative Architecture

> Build only what the current sprint requires.

- Do not build for Instagram, TikTok, or any platform except YouTube
- Do not create generic providers when a concrete implementation suffices
- Generalize later when a real need emerges across multiple platforms
- Every abstraction must have at least two existing callers before it is extracted

---

## Rule 5 — Vertically Complete Features

> Every feature must be fully wired before the sprint is complete.

Database → Repository → Service → API → Frontend → Test → Verification.

Nothing may stop halfway. A model without an API is unfinished. An API without a frontend is unfinished. A frontend without a test is unfinished.

---

## Rule 6 — No Placeholders

> If a file exists, it must be functional.

- No `TODO` comments
- No `# future use` stubs
- No empty functions with `pass`
- No `return ctx` execute methods that do nothing
- No mock implementations unless explicitly requested

---

## Rule 7 — No Dead Code

> Do not create files that are never imported.
> Do not create abstractions that have zero callers.
> Remove deprecated files immediately — do not leave empty or commented-out files.

---

## Rule 8 — No Code Duplication

> Prefer simplicity over cleverness.

- Reuse existing helper functions, components, and classes
- If code appears in three places, extract it
- If a design feels complex, simplify it before shipping

---

## Rule 9 — Explain Before Building

> If a design decision is questionable, stop and explain before implementing.

When in doubt:
1. State the problem
2. Propose 2–3 approaches
3. Explain tradeoffs
4. Get confirmation
5. Implement

---

## Rule 10 — Maintainability Over Cleverness

> Write code that your future self can understand in 6 months.

- Clear variable names over cryptic abbreviations
- Simple functions over clever one-liners
- Explicit error handling over silent failures
- Documented design decisions over implicit assumptions

---

## Rule 11 — Identity Provider Constraint

> Google OAuth is the sole identity provider. Do not build JWT authentication, email/password login, or a user management system.

YouTube is the identity source. If email/password or other auth methods are needed later, they can be added as a separate sprint. Do not prematurely generalize the auth system.
