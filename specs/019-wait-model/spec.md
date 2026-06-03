# Feature Specification: The Wait Model (Fork-Join) (HLD-005)

**Feature Branch**: `019-wait-model`

**Created**: 2026-06-03

**Status**: Draft

**Source HLD**: HLD-005 — `HLD-ROLE: architecture`, `HLD-RISK: HIGH`, `HLD-SPECS: constitution`
**HLD-VERIFY**: escalate and split both park the task as blocked and free the runner; a task is runnable only when it has no unmet dependencies

**Input**: HLD-005 — unified fork-join wait model; escalate and split are the same primitive

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — A runner escalates and immediately moves to next work (Priority: P1)

A runner hits an ambiguity or authority gate, calls `flow escalate`, and the task becomes
blocked. The runner does not idle — it calls `flow next` and receives the next available
task. The session is the scarce resource and must keep working.

**Why this priority**: This is the core promise of the wait model: parking a task never
blocks the runner. Everything else depends on this.

**Independent Test**: After escalating a task, the runner can immediately claim the next
available task without waiting for a human reply.

**Acceptance Scenarios**:

1. **Given** a runner holds an in-progress task, **When** it calls escalate, **Then** the task becomes `blocked` and the runner is freed.
2. **Given** a blocked escalated task and another pending task, **When** the runner calls `flow next`, **Then** it receives the other pending task without waiting.
3. **Given** a task blocked on escalation, **When** the human replies, **Then** the task wakes to `pending` and re-enters the runnable queue.

---

### User Story 2 — A runner splits a task and moves to child work (Priority: P1)

A runner decomposes a task into children via `flow split`. The parent parks as `blocked`.
The runner can immediately pick up one of the children. When all children are done, the
parent wakes automatically.

**Why this priority**: Split is the fork-join mechanism. It must work identically to
escalate in terms of parking semantics — same primitive, different dependency type.

**Independent Test**: After splitting a task, the runner can immediately claim a child;
after all children complete, the parent is runnable again.

**Acceptance Scenarios**:

1. **Given** a runner holds an in-progress task, **When** it calls split with two children, **Then** the parent becomes `blocked`, two child tasks are created (`pending`), and the runner can immediately claim a child.
2. **Given** a split parent with two children and one child done, **When** the other child is still pending/in_progress, **Then** the parent remains `blocked`.
3. **Given** a split parent with all children done, **When** the system processes the last child completion, **Then** the parent automatically transitions to `pending`.

---

### User Story 3 — The runner session never idles (Priority: P2)

A runner that parks a task (via escalate or split) always has more work available as long
as other pending tasks exist. The runner never needs to poll or wait.

**Why this priority**: The no-idle guarantee is the system's key efficiency property. A
runner that idles wastes the scarce session resource.

**Independent Test**: With multiple pending tasks, a runner that escalates task A can
immediately claim task B — the runner holds two tasks simultaneously: task A (blocked)
and task B (in_progress).

**Acceptance Scenarios**:

1. **Given** tasks A and B both pending, **When** a runner claims A then escalates A, **Then** `flow next` returns B immediately; task A is blocked, task B is in_progress.
2. **Given** `flow next` on an empty queue after parking all work, **Then** it returns "none"; the runner waits correctly without thrashing.

---

### Edge Cases

- A task can be split into a single child (degenerate fork-join; parent waits on one child).
- Splitting with zero children is rejected.
- A blocked task cannot be escalated again (it is already parked); done → reopen is the path back.
- The parent never wakes until **every** child is done — partial completion does not wake the parent.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `flow escalate` MUST transition the task from `in_progress` to `blocked` and free the runner immediately.
- **FR-002**: `flow split` MUST transition the parent from `in_progress` to `blocked`, create the specified child tasks as `pending`, and free the runner immediately.
- **FR-003**: Both `escalate` and `split` are the same blocking primitive: they park the task as `blocked` and the runner moves on — the system MUST treat them identically in terms of parking semantics.
- **FR-004**: A blocked task MUST NOT become runnable until ALL of its blocking conditions clear (all open escalations answered AND all children done).
- **FR-005**: `flow next` MUST return the next runnable task (or "none") regardless of how many tasks the calling session has parked.
- **FR-006**: Splitting with zero children MUST be rejected.

### Key Entities

- **Escalation**: A blocking condition created by `flow escalate`. Cleared by a human reply.
- **Child task**: A blocking condition created by `flow split`. Cleared when the child transitions to `done`.
- **Parking**: The act of transitioning a task to `blocked` and freeing the runner. Escalate and split both park.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A test asserts that after escalating a task, the runner can immediately claim the next pending task (runner is not blocked by its parked work).
- **SC-002**: A test asserts that after splitting a task, the parent is `blocked`, children are `pending`, and the runner can immediately claim a child.
- **SC-003**: A test asserts the waking condition: a split parent does not wake until the LAST child is done (partial completion does not wake).
- **SC-004**: A test asserts that splitting with zero children is rejected.
- **SC-005**: The HLD-005 VERIFY invariant ("escalate and split both park the task as blocked and free the runner; a task is runnable only when it has no unmet dependencies") is cited by ID in at least one test.
- **SC-006**: All prior tests (51 at time of writing) remain green after any changes introduced by this spec.

---

## Assumptions

- `flow.py` already implements both escalate and split correctly; this spec drives characterization tests, not a new implementation.
- "Free the runner" means the session can call `flow next` and receive another task — it does not mean the session loses hold of the parked task.
- The wait model (HLD-005) builds on the four-state lifecycle (HLD-004); both specs are characterization-only for the same brownfield implementation.
- All new tests go in `test_flow.py`.
