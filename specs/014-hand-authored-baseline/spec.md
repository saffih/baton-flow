# Feature Specification: Orphaned-work recovery (lease, reclaim, fence)

**Feature Branch**: `014-orphaned-work-recovery`

**Created**: 2026-05-30

**Status**: Draft

**Source HLD**: HLD-014 (HIGH). Depends on HLD-013 (atomic claim, one-tx-per-op),
HLD-010 (named sessions), HLD-008 (baton multi-writer), HLD-006 (escalation primitive).

**Input**: "A session can claim a task and then vanish, leaving it stuck in_progress
forever. Recover it — a liveness concern, separate from HLD-013's correctness."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Reclaim an orphaned task (Priority: P1)

A named session claims a task and then disappears (crash, killed shell, lost network).
The task must not stay `in_progress` forever; after the session has been silent past a
generous lease TTL, the next `flow next` returns it to the runnable pool for another
session, with the reclaim recorded on the baton.

**Why this priority**: This is the entire point of the feature — without it, a vanished
runner strands work permanently. Everything else is refinement on top.

**Independent Test**: Claim a task as session A, fast-forward its `updated_at` past the
TTL, call `flow next` as session B, assert the task is claimed by B and the baton shows
a `reclaimed` entry.

**Acceptance Scenarios**:

1. **Given** a task `in_progress` whose holder has been silent past `LEASE_TTL`, **When**
   any `flow next` runs, **Then** the task returns to `pending`, `reclaim_count` is
   incremented, and a `reclaimed: session X silent since T` entry is appended.
2. **Given** a task `in_progress` within its TTL, **When** `flow next` runs, **Then** the
   task is NOT reclaimed.
3. **Given** an orphaned task, **When** its original holder later does `note`/`decide`,
   **Then** the lease is refreshed (no premature reclaim while genuinely progressing).
4. **Given** a `blocked` task (parked by design), **When** time passes, **Then** it is
   NEVER reclaimed — only `in_progress` is subject to reclaim.

---

### User Story 2 - Fence a stale owner (Priority: P1)

After a task is reclaimed (or while held by a session), a different or returning runner
must not be able to complete, escalate, or split a task it no longer holds. Only
ownership-implying transitions are fenced; the baton stays a shared blackboard.

**Why this priority**: Reclaim creates the possibility of two runners believing they own
one task. Without fencing, the stale one could `done` work the new one is redoing,
corrupting outcomes. Correctness-critical, so P1 alongside reclaim.

**Independent Test**: Session A claims a task; reclaim it to B; assert A's
`done`/`escalate`/`split` are rejected while `note`/`decide`/`reply` still succeed.

**Acceptance Scenarios**:

1. **Given** a task whose session owner is B, **When** session A calls
   `done`/`escalate`/`split` with `--session A`, **Then** it is rejected with "you no
   longer hold task N".
2. **Given** a session-owned task, **When** the holding session calls those verbs with
   its own `--session`, **Then** they succeed.
3. **Given** any task, **When** `note`/`decide`/`reply` are called by anyone, **Then**
   they succeed (multi-writer blackboard, HLD-008).
4. **Given** a task claimed with NO session (legacy path), **When** `done`/`escalate`/
   `split` are called without `--session`, **Then** they succeed unfenced — `flow next`
   without a session behaves exactly as before (HLD-010 invariant).

---

### User Story 3 - Escalate chronically-orphaned work (Priority: P2)

A task that keeps being reclaimed (every runner that takes it vanishes, or it is
genuinely stuck) should stop being silently requeued and instead be raised to a human.

**Why this priority**: Prevents an infinite reclaim loop on poison work. Valuable but
only reachable after US1 exists, so P2.

**Acceptance Scenarios**:

1. **Given** a task reclaimed `RECLAIM_MAX` times, **When** it would be reclaimed again,
   **Then** it is escalated (state `blocked`, open escalation) instead of requeued.

## Requirements *(mandatory)*

- **FR-001**: A task's lease is its `updated_at`; any state change or baton write refreshes it.
- **FR-002**: Reclaim runs lazily inside `flow next`, before task selection, under the
  same `BEGIN IMMEDIATE` transaction as the claim (no daemon — HLD-011).
- **FR-003**: Only `in_progress` tasks past `LEASE_TTL` are reclaimed; `blocked` never is.
- **FR-004**: Reclaim increments `reclaim_count` and records the reason on the baton.
- **FR-005**: After `RECLAIM_MAX` reclaims, escalate instead of requeue.
- **FR-006**: `done`/`escalate`/`split` on a session-owned task require the owning session;
  reject otherwise. No-session (legacy) tasks are unfenced.
- **FR-007**: `note`/`decide`/`reply` are never fenced.

### Key Entities

- **Lease**: reuses `tasks.updated_at`; no new column.
- **reclaim_count**: new `INTEGER DEFAULT 0` column on `tasks`.
- **LEASE_TTL / RECLAIM_MAX**: module constants (generous TTL; small max).

## Out of Scope

- Heartbeat obligation (none — silence alone defines an orphan).
- Cross-process liveness detection beyond the lease timestamp.
- A background sweeper/daemon (forbidden by HLD-011).
