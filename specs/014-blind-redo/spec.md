# Feature Specification: Orphaned-Work Recovery (Lease, Reclaim, Fence)

**Feature Branch**: `014-orphaned-work-recovery`

**Created**: 2026-05-31

**Status**: Draft

**Input**: HLD anchor HLD-014 — "Orphaned-work recovery (lease, reclaim, fence)"

## User Scenarios & Testing *(mandatory)*

<!--
  This feature is a liveness concern: a named session can claim a task and then vanish,
  leaving the task stuck in_progress forever. Recovery is separate from the correctness
  guarantees of HLD-013 (atomic claim, one transaction per operation). The three stories
  below are the independently-testable slices, ordered by the value each delivers alone.
-->

### User Story 1 - Stuck work is automatically reclaimed (Priority: P1)

A named session claims a task, begins working it, then disappears (crash, network loss, abandoned session) without completing, escalating, or splitting it. The task is left `in_progress` with no live owner. Later, when any runner asks for its next task, the system detects that the abandoned task has been silent past a generous lease window, returns it to `pending` so it can be worked again, records why it was reclaimed, and counts the reclaim.

**Why this priority**: Without this, a single vanished session can strand a task forever — work silently never finishes and no one is told. This is the core value of the feature: work is never lost to a dead session. It stands alone as a complete, demonstrable capability.

**Independent Test**: Claim a task with a named session, advance time (or the lease stamp) past `LEASE_TTL` without any further activity, then call `flow next`. Verify the task is `pending` again, its baton carries a `reclaimed: session X silent since T` entry, and `reclaim_count` increased by one.

**Acceptance Scenarios**:

1. **Given** a task held `in_progress` by a named session whose last activity is older than `LEASE_TTL`, **When** any runner calls `flow next`, **Then** the task is returned to `pending`, a note `reclaimed: session X silent since T` is appended to its baton, and `reclaim_count` is incremented before any task is selected.
2. **Given** a task held `in_progress` by a named session whose last activity is within `LEASE_TTL`, **When** `flow next` is called, **Then** the task is NOT reclaimed and remains `in_progress`.
3. **Given** a task in `blocked` state (parked by escalate or split), **When** its silence exceeds `LEASE_TTL` and `flow next` is called, **Then** the task is NOT reclaimed — only `in_progress` tasks are eligible for reclaim.
4. **Given** an `in_progress` task whose owning session appended progress via `flow note` or `flow decide` within `LEASE_TTL`, **When** `flow next` is called, **Then** the lease is treated as fresh and the task is NOT reclaimed.
5. **Given** two runners calling `flow next` concurrently against one orphaned task, **When** both run, **Then** the reclaim occurs under the same `BEGIN IMMEDIATE` as the claim, so the task is reclaimed-and-reassigned at most once and is never double-claimed.

---

### User Story 2 - A session that lost its task cannot act on it (Priority: P2)

A named session's task is reclaimed and possibly picked up by someone else; meanwhile the original (now-zombie) session comes back and tries to complete, escalate, or split it. Because that session no longer holds the task, the ownership-implying action is rejected with a clear message, so a returning ghost can't corrupt work that has moved on.

**Why this priority**: This prevents a returning vanished session — or any session acting on a task it does not hold — from finishing, parking, or restructuring work it no longer owns. It guards the integrity of the reclaim mechanism in Story 1, but reclaim already delivers value without it, so it is P2.

**Independent Test**: Claim a task with session A, then attempt `flow done` / `flow escalate` / `flow split` on that task while passing a different session (or no session) than the current holder. Verify each is rejected with `you no longer hold task N`, and that a no-session (legacy) task accepts the same verbs without a fence check.

**Acceptance Scenarios**:

1. **Given** a task currently held by named session A, **When** `flow done` is invoked carrying a different session (or no holding session), **Then** the operation is rejected with `you no longer hold task N` and the task state is unchanged.
2. **Given** a task currently held by named session A, **When** `flow escalate` is invoked not carrying session A, **Then** it is rejected with `you no longer hold task N`.
3. **Given** a task currently held by named session A, **When** `flow split` is invoked not carrying session A, **Then** it is rejected with `you no longer hold task N`.
4. **Given** a task held by named session A, **When** session A itself invokes `flow done` / `flow escalate` / `flow split`, **Then** the operation succeeds.
5. **Given** a task claimed with no session (the legacy HLD-010 path), **When** `flow done` / `flow escalate` / `flow split` is invoked, **Then** it is accepted with no fence check — behavior is exactly as before this feature.
6. **Given** any task held by a named session, **When** `flow note`, `flow decide`, or `flow reply` is invoked by any writer, **Then** the operation is accepted (never fenced) and is recorded with attribution.

---

### User Story 3 - Chronically-reclaimed work is escalated, not endlessly requeued (Priority: P3)

A task keeps being claimed and abandoned, cycling through reclaim after reclaim. Rather than requeue it forever, after a reclaim threshold the system escalates it to a human — reusing the same escalation path as repeated failure — so a persistently-orphaned task gets human attention instead of thrashing.

**Why this priority**: This is a refinement of Story 1's loop that prevents pathological requeue churn. It only matters once reclaim exists and only triggers after repeated reclaims, so it is the lowest priority of the three while still being independently testable.

**Independent Test**: Drive a single task through `RECLAIM_MAX` reclaim cycles, then trigger one more orphan-detection pass via `flow next`. Verify that instead of returning to `pending`, the task becomes `blocked` (escalated, waiting on a human) rather than being requeued again.

**Acceptance Scenarios**:

1. **Given** a task whose `reclaim_count` is below `RECLAIM_MAX`, **When** it is detected orphaned during `flow next`, **Then** it is requeued to `pending` (per Story 1).
2. **Given** a task whose reclaim count has reached `RECLAIM_MAX`, **When** it is detected orphaned during `flow next`, **Then** it is escalated (parked `blocked`, waiting on a human) via the existing escalation primitive rather than requeued.

---

### Edge Cases

- **Within-window silence**: A task silent for less than `LEASE_TTL` is never reclaimed, even if it has had no activity since the claim.
- **Blocked tasks**: A `blocked` task is parked by design and is never reclaimed regardless of how long it has been silent.
- **Concurrent detection**: Two simultaneous `flow next` calls hitting the same orphan must not both reclaim/reassign it; reclaim is serialized under the claim's `BEGIN IMMEDIATE`.
- **Lease refresh by progress only**: Only `note` and `decide` refresh the lease stamp. `reply` (human/ops-facing) and read-only `context` do not own the task and are not lease refreshes.
- **No-session tasks**: A task claimed without a named session is unfenced; ownership-implying verbs on it behave exactly as before this feature.
- **Exactly at threshold**: When a task reaches `RECLAIM_MAX` reclaims, the next orphan detection escalates instead of requeuing.

## Requirements *(mandatory)*

### Functional Requirements

**Lease**

- **FR-001**: System MUST treat a held task's last-activity timestamp (`updated_at`) as its lease stamp.
- **FR-002**: System MUST refresh the lease stamp on any progress recorded via `flow note` or `flow decide`.
- **FR-003**: System MUST classify an `in_progress` task as *orphaned* when its lease stamp is older than `LEASE_TTL`. No heartbeat or ping is required; silence alone defines an orphan.

**Reclaim**

- **FR-004**: System MUST detect and reclaim orphaned tasks lazily inside `flow next`, before a task is selected for the caller. No background process or daemon performs reclaim.
- **FR-005**: System MUST reclaim ONLY tasks in the `in_progress` state. Tasks in `blocked` MUST NOT be reclaimed.
- **FR-006**: On reclaim, System MUST return the task to `pending`.
- **FR-007**: On reclaim, System MUST append a reclaim record to the task's baton of the form `reclaimed: session X silent since T`.
- **FR-008**: On reclaim, System MUST increment the task's `reclaim_count`.
- **FR-009**: System MUST perform reclaim under the same `BEGIN IMMEDIATE` transaction as the claim in `flow next`, so reclaim cannot race a concurrent claim and a task is reclaimed/reassigned at most once.

**Escalate-on-repeat**

- **FR-010**: When an orphaned task has been reclaimed `RECLAIM_MAX` times, System MUST escalate it (park it `blocked`, waiting on a human) instead of requeuing it to `pending`, reusing the existing escalation primitive.

**Fence (ownership-implying transitions)**

- **FR-011**: For a task held by a named session, System MUST reject `flow done`, `flow escalate`, and `flow split` unless the operation carries the session that currently holds the task; the rejection message MUST be `you no longer hold task N`.
- **FR-012**: System MUST NOT fence tasks claimed with no session (the legacy HLD-010 path); ownership-implying verbs on such tasks behave exactly as before this feature, and `flow next` without a session is unchanged.
- **FR-013**: System MUST NOT fence `flow note`, `flow decide`, or `flow reply`; these remain multi-writer and are recorded with attribution per the baton model.

**Configuration parameters**

- **FR-014**: System MUST support a configurable lease window [NEEDS CLARIFICATION: `LEASE_TTL` is described as "generous" but the HLD states no concrete value].
- **FR-015**: System MUST support a configurable reclaim threshold [NEEDS CLARIFICATION: `RECLAIM_MAX` count is not specified in the HLD].

### Key Entities *(include if feature involves data)*

- **Task**: The unit of work being recovered. Relevant attributes for this feature: its state (`in_progress` is the only reclaimable one; `blocked` is excluded), its lease stamp (`updated_at`), its current holding session (`assignee`), and `reclaim_count`.
- **Lease**: Not a separate record — the held task's `updated_at` interpreted as a time-to-live. A task whose lease stamp predates `now − LEASE_TTL` while `in_progress` is orphaned.
- **`reclaim_count`**: A per-task counter, new for this feature, incremented on each reclaim and compared against `RECLAIM_MAX` to decide requeue-vs-escalate.
- **Session**: The named runner identity (from HLD-010) that holds a task. Whether a task is held by a named session vs. no session determines whether the fence applies.
- **Baton**: The per-task document (HLD-008). Reclaim appends a `reclaimed: …` entry to it; it remains multi-writer for `note`/`decide`/`reply`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: No task remains `in_progress` past `LEASE_TTL` of silence once any `flow next` runs — it is either reclaimed to `pending` or (at threshold) escalated.
- **SC-002**: Reclaim never produces a duplicate or double claim: under concurrent `flow next` calls, an orphaned task is reclaimed/reassigned at most once.
- **SC-003**: A task is never reclaimed before it is silent past `LEASE_TTL`, and a `blocked` task is never reclaimed at all (0% false reclaims of in-window or blocked tasks).
- **SC-004**: 100% of ownership-implying transitions (`done`/`escalate`/`split`) attempted on a session-held task by a non-holding session are rejected; 100% of the same transitions by no-session (legacy) tasks are accepted unchanged.
- **SC-005**: `note`/`decide`/`reply` succeed for any writer on any task (0% fenced), with attribution recorded.
- **SC-006**: Every reclaim leaves an audit trail: the baton carries a `reclaimed: session X silent since T` entry and `reclaim_count` reflects the number of reclaims.

## Assumptions

- **Liveness only**: This feature addresses liveness (work not getting stuck), and relies on — but does not re-specify — HLD-013's correctness guarantees (atomic claim, one transaction per operation). It only constrains reclaim to run inside the existing `BEGIN IMMEDIATE`.
- **Builds on named sessions**: The fence and the notion of "the session that holds a task" depend on named sessions and the `assignee` field from HLD-010.
- **Reclaim clears the holder**: When a task returns to `pending` on reclaim, it is no longer held by the vanished session. The HLD states the task returns to `pending` and that the prior holder can no longer act on it (the fence rejects it); it does not explicitly state the `assignee` column is cleared. This spec assumes the holder is effectively released on reclaim. *(Judgment call — see report.)*
- **`LEASE_TTL` is generous**: A concrete value is not given by the HLD; a generous default is assumed pending clarification (FR-014).
- **`RECLAIM_MAX` threshold**: A concrete count is not given by the HLD (FR-015).

## Out of Scope

- **No daemon / no background process**: Reclaim is lazy — it happens only inside `flow next`. No health-monitoring daemon, polling loop, or background sweeper performs reclaim (consistent with HLD-011's excluded health-monitoring daemon and automatic failover).
- **No heartbeat obligation**: Sessions are not required to send pings or heartbeats. Silence alone — not a missing ping — defines an orphan.
- **Re-specifying HLD-013**: The atomic-claim and one-transaction-per-operation guarantees are owned by HLD-013 and are not redefined here.
- **Fencing the blackboard**: `note`/`decide`/`reply` are deliberately never fenced; fencing them would break the multi-writer baton model (HLD-008).
- **Reclaiming `blocked` tasks**: Parked (`blocked`) tasks are out of scope for reclaim by design; they are waiting on a dependency, not orphaned.
