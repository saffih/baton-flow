# Baton Flow — Constitution (PROPOSAL)

**Status:** PROPOSAL ONLY. This is authored by Journey 2 as a proposal.
It is applied to `.specify/memory/constitution.md` only at
`CONSTITUTION_APPROVAL_GATE`, where SpecKit owns the applied constitution.

**Source:** Derived from the 11 constitution-backed HLD sections
(HLD-003/004/005/007/008/009/010/013/014/015/016).

---

## Identity

Baton Flow is a context-management system for AI-assisted sessions. It produces
durable deliverables (reports) across handoffs under human steering.

## Core Principles

1. **Single source of truth.** One durable state store holds all state. Markdown
   projections are derived, re-derivable, and never part of a transaction.
   (HLD-003)

2. **CLI-only writes.** Every mutation goes through named CLI verbs. No direct
   database access. (HLD-009)

3. **Named identity.** Every action is taken by a named session. There is no
   anonymous path. (HLD-009, HLD-010)

4. **Five invariants, nothing more.** The engine constrains only: dependency,
   identity, ownership, lifecycle, existence. Everything above that floor is
   agent judgment. (HLD-015)

5. **Means vs output.** The baton is context (the means); the outcome is the
   task's account; the report is the deliverable (the output). They are
   different kinds, not different sizes. (HLD-008, HLD-016)

---

## CONTRACT Rules

### CONTRACT-SINGLE-STORE
The single durable store (currently SQLite) is the sole source of truth.
Projections are derived and never canonical. A projection may be deleted and
re-derived without data loss. (HLD-003)

### CONTRACT-ONE-TX-PER-VERB
Every CLI operation is exactly one all-or-nothing transaction. A crash
mid-operation leaves no partial state. (HLD-013)

### CONTRACT-SESSION-ENFORCEMENT
Every CLI call carries a recognized session, enforced at the CLI entry point.
A missing session is an error — reads included. (HLD-009)

### CONTRACT-FOUR-STATES
Tasks have exactly four states: pending, in_progress, blocked, done.
Transitions follow the defined state machine. The CHECK constraint in the
schema is a lifecycle invariant. (HLD-004)

### CONTRACT-DEPENDENCY-GUARD
A task is runnable only when it has no unmet dependencies (open escalations or
unfinished children). A task cannot be done with unmet dependencies. (HLD-004,
HLD-005)

### CONTRACT-CONCURRENT-ESCALATIONS
A task may hold multiple escalations open concurrently. Each is a distinct
dependency with its own stable ID/reference, owner/reply routing, and status.
(HLD-005)

### CONTRACT-ALL-RESOLVED-WAKE
A task wakes to pending only when ALL its dependencies resolve — every open
escalation answered and every child finished. (HLD-005)

### CONTRACT-ANSWER-FEEDBACK-SPLIT
Answer resolves a specific open escalation by ID. Feedback steers (output
update or new scope). Answer with no matching escalation is rejected. (HLD-007)

### CONTRACT-ATOMIC-CLAIM
`flow next` takes the write lock (BEGIN IMMEDIATE) before reading the queue,
selects the runnable task, records claimed-by on the baton, and claims in the
same transaction. Two runners can never both hold one task. (HLD-013)

### CONTRACT-SOFT-AFFINITY
A session binds to the label of the first labeled task it claims. Bound, it
prefers its label but falls back rather than idle. "None" only when no
runnable work exists. (HLD-010)

### CONTRACT-OWNERSHIP-FENCE
done/escalate/split are rejected when the task is held by a different named
session. An unowned task stays operable by any named session. note/decide are
multi-writer, never fenced. feedback is unfenced (creation verb). (HLD-014)

### CONTRACT-LEASE-RECLAIM
A task in_progress past LEASE_TTL is reclaimable. Reclaim returns to pending,
clears assignee, records reason, runs under BEGIN IMMEDIATE. Only in_progress
is reclaimed. (HLD-014)

### CONTRACT-FLAKY-MARK
reclaim_count saturates at RECLAIM_MAX. At/past the ceiling, further
orphaning escalates immediately with a scoped escalation. The mark never
resets — a fresh start is a new task. (HLD-014)

### CONTRACT-MANDATORY-OUTCOME
Every task states a mandatory outcome at done — its bound account
(what/how/why). Outcome size is a UX detail, not a kind change. (HLD-016)

### CONTRACT-REPORT-LIFECYCLE
Reports have lifecycle: active → deprecated (superseded or obsolete). A
deprecated report is immutable. References are deprecation-aware — resolve to
the live successor. Every update is attributed. (HLD-016)

---

## DATA Rules

### DATA-BATON-OWNERSHIP
The baton lives in the database. Its canonical read path is the CLI. The
markdown projection is derived product surface. (HLD-008, HLD-003)

### DATA-REPORT-OWNERSHIP
Reports are DB-owned. Markdown projections are derived product surface. A
report's lifecycle is independent of any task's. (HLD-016, HLD-003)

### DATA-PROJECTION-ROLES
Markdown projections carry three roles: (1) agent integration/handoff,
(2) context state for WIP, (3) user-facing context and reporting. They are
product surface, not just display. An agent may read directly when the
projection preserves stable IDs, references, context state, reply context,
and report/log links. (HLD-003)

### DATA-ESCALATION-IDENTITY
Each escalation carries its own stable ID/reference, owner/reply routing, and
status. These are distinct dependencies, individually traceable and resolvable.
(HLD-005)

### DATA-SESSION-DURABLE
A session row persists across reclaims. Reclaim takes the task, not the
identity. The bound label survives. (HLD-010)

---

## Invariant Boundary (HLD-015)

The engine constrains ONLY:
- **dependency** — no done with unmet deps; split requires ≥1 child.
- **identity** — every action by a named session; no anonymous path.
- **ownership** — held task can't be transitioned by another session.
- **lifecycle** — four states, legal transitions, deprecated-report immutability.
- **existence** — operations target a real task/report.

Everything above this floor is the agent's call. The tagging audit
(`raise FlowError` → invariant tag) enforces this boundary. A guard that
can't be tagged is candidate overreach.
