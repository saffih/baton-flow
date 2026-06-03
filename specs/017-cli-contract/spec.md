# Feature Specification: The CLI Contract (HLD-009)

**Feature Branch**: `017-cli-contract`

**Created**: 2026-06-03

**Status**: Draft

**Source HLD**: HLD-009 — `HLD-ROLE: api`, `HLD-RISK: HIGH`, `HLD-SPECS: constitution`
**HLD-VERIFY**: runners use only the listed verbs; no direct database access; reply and reopen are human/ops-facing and not part of the runner loop

**Input**: HLD-009 — the agnostic CLI surface, runner verbs, human/ops verbs, no-DB constraint

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — A runner completes a work cycle using only published verbs (Priority: P1)

A runner (AI or human) picks up a task, works it, appends findings, records a decision,
and marks it done — all through the published CLI verbs. It never reads or writes the
database directly. Any AI system executing this story uses identical verbs.

**Why this priority**: This is the core execution contract. Every other behavior depends
on runners following it faithfully.

**Independent Test**: Given only the verb list, a runner can claim a task, add notes,
escalate, and finish — with the system correctly tracking state — without any knowledge
of the underlying storage.

**Acceptance Scenarios**:

1. **Given** a pending task, **When** a runner calls `flow next`, **Then** the task is
   returned and marked in-progress; the runner holds it.
2. **Given** an in-progress task, **When** a runner calls `flow note <id> <text>` and
   then `flow context <id>`, **Then** the note appears on the baton.
3. **Given** an in-progress task, **When** a runner calls `flow decide <id> <decision>`,
   **Then** the decision is recorded on the baton.
4. **Given** an in-progress task, **When** a runner calls `flow done <id> <outcome>`,
   **Then** the task transitions to done with the stated outcome.
5. **Given** an in-progress task, **When** a runner calls `flow escalate <id> <question>`,
   **Then** the task transitions to blocked and the question is on the baton.

---

### User Story 2 — A runner handles fork-join via split (Priority: P2)

A runner that cannot finish a task in one pass decomposes it into children via
`flow split`. The parent parks until all children are done; the runner moves on.

**Why this priority**: Split is the only way a runner creates subtasks. It is part of
the published contract and must be stable.

**Independent Test**: A runner can split a task into two children, complete both
children, and observe the parent wake to pending — all via CLI verbs only.

**Acceptance Scenarios**:

1. **Given** an in-progress task, **When** a runner calls `flow split <id> "A" "B"`,
   **Then** two child tasks are created (pending), the parent transitions to blocked,
   and `flow next` returns one of the children.
2. **Given** a split parent with all children done, **When** a runner calls `flow next`,
   **Then** the parent is returned as pending (woken).

---

### User Story 3 — The human steers via reply and reopen (Priority: P3)

A human answers a blocked task via `flow reply` and reopens a done task via
`flow reopen`. These verbs are explicitly not part of the runner loop — runners never
call them.

**Why this priority**: Separating human/ops verbs from the runner surface is the
contract boundary. Mixing them breaks the agnostic guarantee.

**Independent Test**: A runner loop that enumerates all verbs it is permitted to use
does not include `reply` or `reopen`. A human can reply to a blocked task and the
task wakes.

**Acceptance Scenarios**:

1. **Given** a blocked task, **When** a human calls `flow reply <id> <text>`,
   **Then** the task transitions to pending and the reply appears on the baton.
2. **Given** a done task, **When** a human calls `flow reopen <id>`,
   **Then** the task transitions to pending.
3. **Given** the runner loop definition (core.md), **When** its verb list is enumerated,
   **Then** `reply` and `reopen` are absent from the runner section.

---

### Edge Cases

- `flow next` when no runnable tasks exist → returns "none"; runner must not idle.
- `flow done` on a task with unfinished children → rejected.
- `flow escalate` / `flow split` / `flow done` by a session that no longer holds the
  task (reclaimed) → rejected with a clear error.
- `flow add` used by a runner (off-topic reply branch): permitted but produces a new
  independent task; does not unblock the original.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST expose exactly 8 runner verbs: `add`, `next`, `context`,
  `note`, `done`, `escalate`, `split`, `decide`. No additional runner verbs exist.
- **FR-002**: The system MUST expose exactly 2 human/ops verbs: `reply`, `reopen`.
  These MUST NOT appear in runner loop documentation or be called within a runner loop.
- **FR-003**: Any runner MUST be able to complete a full work cycle (claim → work →
  finish or escalate) using only the 8 runner verbs, with no knowledge of the
  underlying storage technology.
- **FR-004**: The system MUST reject `flow done` when the task has unfinished children.
- **FR-005**: The system MUST reject `flow escalate`, `flow split`, and `flow done`
  when the calling session no longer holds the task (HLD-014 fence).
- **FR-006**: `flow reply` MUST record the reply on the baton and transition the
  blocked task to pending. The runner decides on pickup whether it is on-topic or
  new scope (HLD-007).
- **FR-007**: The contract MUST be AI-agnostic: no verb, argument, or response names
  a specific AI system.
- **FR-008**: `flow next` MUST return "none" (not an error) when no runnable task exists.

### Key Entities

- **Verb**: A named CLI command with defined arguments, preconditions, and effects.
  Split into: runner verbs (8) and human/ops verbs (2).
- **Baton**: The per-task append-only context document. All verbs that write state
  do so via the baton.
- **Session**: The identity claiming a task. Determines fence eligibility (HLD-014).

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every runner verb (`add`, `next`, `context`, `note`, `done`, `escalate`,
  `split`, `decide`) has at least one passing test that exercises its contract
  in isolation.
- **SC-002**: A contract test asserts that `reply` and `reopen` are absent from the
  runner-permitted verb set (core.md enumerates only runner verbs).
- **SC-003**: The HLD-009 VERIFY invariant ("runners use only the listed verbs; no
  direct database access; reply and reopen are human/ops-facing") is cited by ID in
  at least one test.
- **SC-004**: The `test_cli_contract_is_agnostic` test (or equivalent) confirms that
  no verb name, argument name, or output string contains a specific AI system name.
- **SC-005**: All 47 prior tests remain green after any change introduced by this spec.

---

## Assumptions

- `flow.py` already implements all 10 verbs correctly; this spec drives
  characterization tests and contract documentation, not a new implementation.
- The verb set is stable and closed: adding a verb requires an HLD-009 amendment.
- `flow add` is in the runner verb set because runners use it in the off-topic reply
  branch (HLD-007); it is also the primary human creation verb — this dual use is
  intentional and already in the HLD.
- Session identity is passed via `--assignee` (HLD-010/014); the spec treats the
  session/assignee mechanism as already-built.
