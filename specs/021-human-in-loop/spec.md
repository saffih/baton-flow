# Feature Specification: Human-in-the-Loop (Human → Runner) (HLD-007)

**Feature Branch**: `021-human-in-loop`

**Created**: 2026-06-03

**Status**: Draft

**Source HLD**: HLD-007 — `HLD-ROLE: processing`, `HLD-RISK: MEDIUM`, `HLD-SPECS: constitution`
**HLD-VERIFY**: a human reply is appended to the baton and resolves the open escalation; when the task wakes, the runner either continues this task or creates a new related task from the reply without silently merging scopes

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
it as new scope and adds a new related task. The original task is then handled
explicitly by the runner — continue, re-park, or finish — so scope is never silently
merged and no fake dependency is implied.

**Why this priority**: This is the lossless-steering invariant. If off-topic replies
modified the original task, work would be silently mis-directed.

**Independent Test**: The runner loop definition (core.md) explicitly states the binary
routing rule: on-topic → continue this task from the baton; off-topic → create a new
related task and handle the original task explicitly.

**Acceptance Scenarios**:

1. **Given** core.md, **When** its reply routing section is read, **Then** it states that an on-topic reply means continue this task and an off-topic reply means create a new related task and handle the original task explicitly.

---

### Edge Cases

- A reply always appends to the baton and resolves the open escalation; the runner decides afterward whether it is on-topic or new scope.
- Replying to a non-blocked task is permitted (the task was already running or pending); the reply is still recorded.
- The "off-topic → new related task" branch is the runner's responsibility, not system enforcement.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `flow reply` MUST append the reply text to the task's baton and transition a `blocked` task to `pending` by resolving the open escalation.
- **FR-002**: The runner loop documentation (core.md) MUST state the binary reply routing rule: on-topic reply means continue this task; off-topic reply means create a new related task and handle the original task explicitly.

### Key Entities

- **Reply**: Human text recorded on the baton via `flow reply`. Always appended; always visible to the next runner.
- **Binary routing rule**: The runner's decision on pickup: is this reply about the original task (→ continue) or new scope (→ add a related task)?

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A test asserts that `flow reply` appends the text to the baton and transitions a blocked task to `pending`.
- **SC-002**: A test asserts that core.md documents the binary routing rule (both branches named; `new related task` and explicit original-task handling are required forms for the off-topic branch).
- **SC-003**: The HLD-007 VERIFY invariant ("a human reply is appended to the baton and resolves the open escalation; when the task wakes, the runner either continues this task or creates a new related task from the reply without silently merging scopes") is cited by ID in at least one test.
- **SC-004**: All prior tests (52 at time of writing) remain green.

---

## Assumptions

- `flow.py` already implements `flow reply` correctly; this spec drives characterization tests and documentation alignment.
- The binary routing decision is the runner's judgment call; the system enforces append-plus-wake, not whether the runner continues this task or creates a new related task.
- All new tests go in `test_flow.py`.
