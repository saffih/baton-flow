# Feature Specification: The Task Lifecycle (HLD-004)

**Feature Branch**: `018-task-lifecycle`

**Created**: 2026-06-03

**Status**: Draft

**Source HLD**: HLD-004 — `HLD-ROLE: architecture`, `HLD-RISK: HIGH`, `HLD-SPECS: constitution`
**HLD-VERIFY**: only four states exist; a task cannot be done with unfinished children; done is reopenable; blocked wakes to pending only when all dependencies resolve

**Input**: HLD-004 — four-state task lifecycle, runnable-only-when-no-unmet-dependencies rule

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — A runner works a task through the full lifecycle (Priority: P1)

A runner claims a pending task, works it, and marks it done. The system tracks each
transition correctly. At no point does the task exist in an unlisted state.

**Why this priority**: The basic pending → in_progress → done path is the core flow.
All other behaviors depend on this working correctly.

**Independent Test**: Given an empty system, a runner can add a task, claim it, and
mark it done — with the system recording each state transition in order.

**Acceptance Scenarios**:

1. **Given** a newly added task, **When** the system records it, **Then** its state is `pending`.
2. **Given** a pending task, **When** a runner claims it, **Then** its state is `in_progress`.
3. **Given** an in-progress task, **When** a runner marks it done, **Then** its state is `done`.
4. **Given** a task exists, **When** its state is inspected, **Then** it is exactly one of: `pending`, `in_progress`, `blocked`, `done`.

---

### User Story 2 — The system blocks incorrect done transitions (Priority: P1)

A runner cannot mark a task done if it still has unfinished children. The system
enforces this constraint at the boundary.

**Why this priority**: This is the single most important safety constraint —
"the one rule that governs everything." Violating it breaks fork-join semantics.

**Independent Test**: Given a task with at least one unfinished child, marking it done
is rejected with an error; the task state is unchanged.

**Acceptance Scenarios**:

1. **Given** a task with an unfinished child task, **When** a runner attempts to mark it done, **Then** the transition is rejected and the task remains in its current state.
2. **Given** a task whose all children are done, **When** a runner marks it done, **Then** the transition succeeds.

---

### User Story 3 — A human can reopen a done task (Priority: P2)

A done task is not final. A human (or a late-arriving reply) can reopen it, returning
it to pending so a runner can pick it up again.

**Why this priority**: `done` is a resting state, not a grave. Reopening enables
correction and late-arriving context without creating duplicate tasks.

**Independent Test**: Given a done task, a human calls reopen and the task returns to
pending; a runner can then claim it again.

**Acceptance Scenarios**:

1. **Given** a done task, **When** a human calls reopen, **Then** the task transitions to `pending`.
2. **Given** a reopened task in `pending`, **When** a runner claims it, **Then** the runner succeeds and the task is `in_progress`.

---

### User Story 4 — A blocked task wakes when its dependencies resolve (Priority: P2)

A task that is blocked (waiting on a human answer or child completion) automatically
returns to pending when its blocking condition clears — no manual intervention needed.

**Why this priority**: This is the core "fork-join" semantics. Without automatic waking,
runners must poll or re-queue tasks manually, defeating the system's purpose.

**Independent Test**: Given a blocked task with one unresolved dependency, resolving
that dependency causes the task to transition to pending automatically.

**Acceptance Scenarios**:

1. **Given** a blocked task waiting on a child, **When** the child task is marked done, **Then** the parent task automatically transitions to `pending`.
2. **Given** a blocked task waiting on multiple children, **When** the last child is marked done, **Then** the parent transitions to `pending`.
3. **Given** a blocked task waiting on a human reply, **When** the reply is recorded, **Then** the task transitions to `pending`.

---

### Edge Cases

- A task in `in_progress` state is only `pending` again if reclaimed or woken — it cannot be re-claimed while held.
- Marking a `blocked` task done directly is rejected (it has unresolved dependencies by definition).
- `reopen` on a non-done task is rejected.
- No fifth state can be introduced; any attempt to set an unknown state is an error.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST support exactly four task states: `pending`, `in_progress`, `blocked`, `done`. No other states are valid.
- **FR-002**: A task MUST NOT transition to `done` while it has at least one unfinished (non-done) child task. Any such attempt MUST be rejected.
- **FR-003**: A `done` task MUST be transitionable back to `pending` via the reopen operation.
- **FR-004**: A `blocked` task MUST automatically transition to `pending` when all of its blocking dependencies (open escalations and unfinished children) are resolved.
- **FR-005**: A `pending` task transitions to `in_progress` when claimed by a runner.
- **FR-006**: An `in_progress` task transitions to `blocked` via escalate or split (when it is waiting on a dependency).

### Key Entities

- **Task**: The unit of work. Has exactly one state at all times from the four-state set.
- **Dependency**: A blocking condition (open escalation or unfinished child task) that keeps a task in `blocked` state.
- **State Transition**: A guarded change from one state to another. Violating a guard is an error.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A characterization test asserts all valid state transitions: `pending → in_progress`, `in_progress → done`, `in_progress → blocked`, `blocked → pending` (wake), `done → pending` (reopen).
- **SC-002**: A negative-invariant test asserts that `done` is rejected when unfinished children exist; the task state is unchanged after the rejected attempt.
- **SC-003**: A test asserts `done` is reopenable: a done task transitions to `pending` via reopen, and a runner can subsequently claim it.
- **SC-004**: A test asserts automatic waking: a blocked task transitions to `pending` when its last blocking dependency resolves.
- **SC-005**: A test asserts the four-state invariant: no task ever holds a state outside `{pending, in_progress, blocked, done}`.
- **SC-006**: The HLD-004 VERIFY invariant ("only four states exist; a task cannot be done with unfinished children; done is reopenable; blocked wakes to pending only when all dependencies resolve") is cited by ID in at least one test.
- **SC-007**: All prior tests (51 at time of writing) remain green after any changes introduced by this spec.

---

## Assumptions

- `flow.py` already implements the four-state lifecycle correctly; this spec drives characterization tests and contract documentation, not a new implementation.
- The state set is closed: adding a state requires an HLD-004 amendment.
- "Dependency" means either an open escalation record or an unfinished child task — both block the `done` transition and the `wake` condition in the same way.
- Session/assignee management (HLD-010/014) is treated as already built; this spec tests state semantics only.
- Characterization tests are added to `test_flow.py` — no new test files.
