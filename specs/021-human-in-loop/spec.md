# Feature Specification: Human-in-the-Loop (Human → Runner) (HLD-007)

**Feature Branch**: `021-human-in-loop`

**Created**: 2026-06-03

**Status**: Draft

**Source HLD**: HLD-007 — `HLD-ROLE: processing`, `HLD-RISK: MEDIUM`, `HLD-SPECS: constitution`
**HLD-VERIFY**: a human reply about the task itself appends to the baton and unblocks; a reply about anything else becomes a new task and leaves the original blocked

**Input**: HLD-007 — binary reply routing rule; steering is lossless

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — A human reply unblocks a task (Priority: P1)

When a human answers a blocked task, the reply is appended to the baton and the task
returns to pending. A runner can then pick it up, read the baton, and continue.

**Why this priority**: This is the human→runner handoff path. Without it, escalated tasks
stay blocked forever.

**Independent Test**: Given a blocked task, a human calls reply; the task becomes pending
and the reply is visible on the baton.

**Acceptance Scenarios**:

1. **Given** a blocked task, **When** a human calls `flow reply <id> <text>`, **Then** the task transitions to `pending` and the reply text appears on the baton.
2. **Given** a task unblocked by reply, **When** a runner calls `flow next`, **Then** the runner can claim and continue working the task.

---

### User Story 2 — Off-topic replies do not merge scope (Priority: P1)

When a human's reply is about something other than the blocked task, the runner treats
it as new scope and adds a new task. The original task stays blocked — scope is never
silently merged.

**Why this priority**: This is the lossless-steering invariant. If off-topic replies
modified the original task, work would be silently mis-directed.

**Independent Test**: The runner loop definition (core.md) explicitly states the binary
routing rule: on-topic → baton + unblock; off-topic → new task, original stays blocked.

**Acceptance Scenarios**:

1. **Given** core.md, **When** its reply routing section is read, **Then** it states that an on-topic reply unblocks the task and an off-topic reply becomes a new task leaving the original blocked.

---

### Edge Cases

- A reply always appends to the baton; the runner decides afterward whether it is on-topic or new scope.
- Replying to a non-blocked task is permitted (the task was already running or pending); the reply is still recorded.
- The "off-topic → new task" branch is the runner's responsibility, not system enforcement.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `flow reply` MUST append the reply text to the task's baton and transition a `blocked` task to `pending`.
- **FR-002**: The runner loop documentation (core.md) MUST state the binary reply routing rule: on-topic reply unblocks; off-topic reply becomes a new task and leaves the original blocked.

### Key Entities

- **Reply**: Human text recorded on the baton via `flow reply`. Always appended; always visible to the next runner.
- **Binary routing rule**: The runner's decision: is this reply about the original task (→ continue) or new scope (→ add new task)?

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A test asserts that `flow reply` appends the text to the baton and transitions a blocked task to `pending`.
- **SC-002**: A test asserts that core.md documents the binary routing rule (both branches named; "leaves the original blocked" is the required form for the off-topic branch).
- **SC-003**: The HLD-007 VERIFY invariant ("a human reply about the task itself appends to the baton and unblocks; a reply about anything else becomes a new task and leaves the original blocked") is cited by ID in at least one test.
- **SC-004**: All prior tests (52 at time of writing) remain green.

---

## Assumptions

- `flow.py` already implements `flow reply` correctly; this spec drives characterization tests only.
- The binary routing decision is the runner's judgment call; the system only enforces that reply appends and unblocks — it does not enforce which branch the runner takes.
- All new tests go in `test_flow.py`.
