# Feature Specification: Work Routing (Soft Affinity by Label and Named Sessions) (HLD-010)

**Feature Branch**: `023-work-routing`

**Created**: 2026-06-03

**Status**: Draft

**Input**: HLD-010 — Work routing (soft affinity by label and named sessions)

## User Scenarios & Testing

### User Story 1 — Backward-compatible task pickup (Priority: P1)

A runner calls `flow next` with no `--session` argument and gets the oldest runnable task,
exactly as before. The routing extension does not change this path.

**Why this priority**: Backward compatibility is a hard guarantee in HLD-010.

**Independent Test**: Can be verified by calling `flow.next_task(conn, assignee="runner")` with no
session argument and confirming the oldest pending task is returned.

**Acceptance Scenarios**:

1. **Given** no session argument, **When** `flow next` is called, **Then** the oldest runnable task is returned.
2. **Given** no session argument, **When** the queue is empty, **Then** "none" is returned.

---

### User Story 2 — Session binds to label and prefers it (Priority: P2)

A named session (`flow next --session <name>`) claims the oldest runnable task. If that
task is labeled, the session binds to the label and thereafter prefers tasks of the same
label. The session stays bound even when falling back to unlabeled tasks.

**Why this priority**: Soft affinity is the core value of HLD-010 — keeps context warm.

**Independent Test**: Verify that after claiming a labeled task, `flow.next_task(conn, session="S")` returns a second task with the same label before returning unlabeled tasks.

**Acceptance Scenarios**:

1. **Given** a session has claimed a labeled task, **When** tasks of the same label are available, **Then** the session claims those first.
2. **Given** a session has no label yet, **When** it claims an unlabeled task, **Then** the session remains unbound.

---

### User Story 3 — Fallback when label is dry (Priority: P3)

A session whose bound label has no runnable tasks falls back to any runnable task rather
than idling. Returning "none" means no runnable work exists at all, not just no label match.

**Why this priority**: The session is the scarce resource and must keep working.

**Independent Test**: Verify that a bound session claims an unlabeled task when no labeled tasks remain, and returns "none" only when the queue is empty.

**Acceptance Scenarios**:

1. **Given** a session is bound to label L and no L tasks are runnable, **When** unlabeled tasks exist, **Then** the session claims one.
2. **Given** no runnable tasks exist, **When** any session calls `flow next`, **Then** "none" is returned.

---

### Edge Cases

- Children created by `flow split` inherit the parent's label; label propagates through the task tree.
- A session that never claims a labeled task remains unbound and always picks the oldest runnable task.
- Capability routing and must-halt tasks (future extensions noted in HLD-010) are out of scope and not tested.

## Requirements

### Functional Requirements

- **FR-001**: `flow next` with no `--session` MUST return the oldest runnable task without change.
- **FR-002**: `flow next --session <name>` MUST bind the session to the label of the first labeled task it claims.
- **FR-003**: A bound session MUST prefer tasks matching its bound label before taking others.
- **FR-004**: A bound session MUST fall back to any runnable task when none of its label remain.
- **FR-005**: A runner MUST see "none" only when no runnable work exists at all.
- **FR-006**: Children created by `split` MUST inherit the parent task's label.
- **FR-007**: HLD-010 VERIFY invariant MUST be cited by ID in at least one test.

### Key Entities

- **Session**: A named runner identified by `--session <name>`; records a bound label in the `sessions` table.
- **Label**: An optional field on a task identifying its subject (component, directory, topic).

## Success Criteria

### Measurable Outcomes

- **SC-001**: `flow next` with no session returns the oldest runnable task unchanged — COVERED by `test_next_without_session_unchanged`.
- **SC-002**: A session binds to label of first labeled task and prefers it — COVERED by `test_session_binds_then_prefers_its_label`.
- **SC-003**: A session falls back to any runnable task when its label is dry — COVERED by `test_session_falls_back_when_label_dry`.
- **SC-004**: Children inherit parent label after `split` — COVERED by `test_children_inherit_label`.
- **SC-005**: HLD-010 VERIFY invariant cited by ID in at least one test — GAP: need `test_hld010_verify_invariant`.
- **SC-006**: All 57 prior tests remain green.

## Assumptions

- `flow.py` already implements sessions, bound_label, and soft affinity in `next_task` — this is a brownfield characterization spec.
- No source or schema changes are needed.
- "Extensibility (deferred, not built)" in the bundle label refers only to capability routing and must-halt tasks (explicitly deferred in HLD-010), not to the soft-affinity routing which is fully built.
- The deferred extensions are documented as out-of-scope boundary; no absence tests are written for them.
