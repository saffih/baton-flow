# Feature Specification: Escalation Triggers (Runner → Human) (HLD-006)

**Feature Branch**: `020-escalation-triggers`

**Created**: 2026-06-03

**Status**: Draft

**Source HLD**: HLD-006 — `HLD-ROLE: processing`, `HLD-RISK: MEDIUM`, `HLD-SPECS: TBD`
**HLD-VERIFY**: (none — HLD-006 carries no HLD-VERIFY line; the triggers are documented in core.md)

**Input**: HLD-006 — four escalation triggers that govern when a runner must stop and ask

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — A runner stops and escalates on ambiguity (Priority: P1)

When a task has two valid interpretations, the runner does not invent requirements.
It escalates with a question and moves on to the next task.

**Why this priority**: Ambiguity is the most common escalation trigger. If runners
invent answers, the system produces wrong outcomes silently.

**Independent Test**: Given a task that a runner judges as ambiguous, the runner can
escalate it with a question, the task goes blocked, and the runner proceeds.

**Acceptance Scenarios**:

1. **Given** a runner encounters an ambiguous task, **When** it calls `flow escalate`, **Then** the task transitions to `blocked` and the runner is freed to call `flow next`.
2. **Given** a task blocked with a question, **When** the context is read, **Then** the escalation question is present on the baton.

---

### User Story 2 — A runner escalates on authority, irreversibility, and repeated failure (Priority: P1)

A runner must also escalate when a call is beyond its authority (product direction,
credentials, spend), before any irreversible action (delete, deploy, external send,
money), and after ~3 failed attempts.

**Why this priority**: These triggers protect the system from unauthorized or irreversible
actions and from runners thrashing on unfixable problems.

**Independent Test**: The runner loop definition (core.md) explicitly names all four
triggers as required escalation conditions.

**Acceptance Scenarios**:

1. **Given** core.md, **When** its escalation section is read, **Then** all four triggers are documented: Ambiguity, Authority, Irreversibility, Repeated failure.
2. **Given** a question on the baton, **When** context is inspected, **Then** the question is visible and the task is `blocked`.

---

### Edge Cases

- A runner that escalates and then calls `flow next` is not considered to be holding the escalated task — the task is parked and belongs to the queue.
- A done task cannot be escalated; it must be reopened first.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A runner MUST be able to call `flow escalate` with a question; the task MUST transition to `blocked` and the question MUST be recorded on the baton.
- **FR-002**: The escalation question MUST be visible in the task's baton context after escalation.
- **FR-003**: The runner loop documentation (core.md) MUST name all four escalation triggers: Ambiguity, Authority, Irreversibility, and Repeated failure.
- **FR-004**: A done task MUST NOT be escalatable; the attempt MUST be rejected.

### Key Entities

- **Escalation trigger**: One of four conditions requiring a runner to stop and ask (Ambiguity, Authority, Irreversibility, Repeated failure).
- **Escalation question**: The text recorded on the baton when `flow escalate` is called.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A test asserts that escalating a task records the question on the baton and transitions the task to `blocked`.
- **SC-002**: A test asserts that all four escalation triggers are documented in core.md by name.
- **SC-003**: A test asserts that escalating a done task is rejected.
- **SC-004**: All prior tests (52 at time of writing) remain green.

---

## Assumptions

- `flow.py` and `core.md` already implement and document all four triggers correctly; this spec drives characterization tests only.
- "Repeated failure" is documented in core.md as a trigger condition; it is the runner's judgment call when to apply it (not enforced by the system).
- All new tests go in `test_flow.py`.
