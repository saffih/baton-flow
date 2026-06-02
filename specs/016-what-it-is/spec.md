# Feature Specification: What It Is (HLD-001)

**Feature Branch**: `016-what-it-is`

**Created**: 2026-06-02

**Status**: Draft

**Source HLD**: HLD-001 — `HLD-ROLE: purpose`, `HLD-RESOURCES: README.md, core.md`

**Input**: HLD-001 — Baton Flow purpose, baton concept, three pains solved

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — New user understands what Baton Flow is (Priority: P1)

A person evaluating the tool reads the README and understands in under two minutes:
what problem it solves, who uses it, and what the baton is. They can explain it back
in plain language without reading any code.

**Why this priority**: If the purpose is unclear, no one uses the tool. Everything else
depends on this.

**Independent Test**: README.md exists and a reader who knows nothing about the project
can answer: (1) What is a baton? (2) What are the three pains this solves? (3) Who is
the "runner"? — without consulting any other file.

**Acceptance Scenarios**:

1. **Given** a fresh README.md, **When** a reader scans it, **Then** they can identify
   the three specific pains (context loss, no visibility, no steering) and explain how
   the baton addresses each.
2. **Given** the README.md, **When** a reader looks for "what is a baton?", **Then**
   they find a plain-language definition that doesn't require following a code link.

---

### User Story 2 — A runner knows how to interact with the system (Priority: P2)

An AI runner or human picking up a task reads `core.md` and knows exactly what they
can do: which CLI verbs exist, what the baton looks like, when to escalate, when to
split, and how to hand off.

**Why this priority**: The runner contract is the execution seam. A runner that
doesn't understand it either idles or breaks tasks.

**Independent Test**: A runner given only `core.md` can enumerate all allowed actions
and produce a correct `flow reply` or `flow escalate` call without reading any other
document.

**Acceptance Scenarios**:

1. **Given** `core.md`, **When** a runner needs to hand off a blocked task, **Then**
   they find explicit guidance on when to escalate vs. split — and what happens to the
   task in each case.
2. **Given** `core.md`, **When** a runner finishes a work unit, **Then** they know how
   to mark it done and what the system expects next.
3. **Given** `core.md`, **When** a human sends a reply to a blocked task, **Then** the
   binary routing rule is stated: on-topic reply unblocks the task; off-topic reply
   becomes a new task.

---

### User Story 3 — Someone setting up understands scope and limits (Priority: P3)

A user who wants to extend or operate the tool reads the README and understands what
is deliberately excluded (sockets, web UI, health daemons) and why. They don't try
to build what was stripped on purpose.

**Why this priority**: The stripped-scope list prevents well-meaning contributors from
re-introducing complexity the HLD explicitly removed.

**Independent Test**: README.md or an associated document names at least the stripped-scope
categories from HLD-011 so a contributor knows the boundaries before proposing a change.

**Acceptance Scenarios**:

1. **Given** the README.md, **When** a contributor considers adding a web API or
   Unix-socket delivery, **Then** they find a note that those are out of scope and why.

---

### Edge Cases

- What if `core.md` is absent when a runner starts? The runner must be able to discover
  it is required from the README.
- What if the README references a CLI verb that doesn't exist in the current `flow` binary?
  The spec documents the intended state; gaps between spec and implementation are
  flagged as test failures, not spec defects.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `README.md` MUST define "baton" in plain language without requiring
  the reader to open any source file.
- **FR-002**: `README.md` MUST name the three pains Baton Flow solves (context loss,
  no visibility, no way to steer) and explain how the baton addresses each.
- **FR-003**: `README.md` MUST identify the two actor types: the human who creates
  tasks and the runner (AI or human) who executes them.
- **FR-004**: `core.md` MUST enumerate every CLI verb a runner is permitted to use,
  with a one-line description of each.
- **FR-005**: `core.md` MUST state the binary reply rule explicitly: a reply that is
  about the task unblocks it and appends to the baton; a reply that is not about the
  task becomes a new task and leaves the original blocked (HLD-007).
- **FR-006**: `core.md` MUST describe the escalate/split primitives and make clear
  that both park the task as blocked and free the runner.
- **FR-007**: `README.md` MUST state the stripped-scope boundaries (no sockets, no
  web UI, no health daemons, no migration tooling) so contributors know what is
  deliberately excluded.
- **FR-008**: Both documents MUST NOT name a specific AI system; all runner references
  MUST be AI-agnostic (HLD-003, HLD-009).

### Key Entities

- **Baton**: The per-task document that carries durable context from runner to runner.
  Attributes: task identity, accumulated notes, current status.
- **Runner**: Any agent (AI session or human) that picks up and executes a task.
- **Task**: The unit of work. Has a lifecycle (pending → in_progress → blocked/done).
- **Human**: Creates tasks, steers via replies, reviews output.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A reader unfamiliar with the project can answer the three onboarding
  questions (What is a baton? What three pains does it solve? Who is the runner?)
  correctly after reading only `README.md` — with no prior knowledge required.
- **SC-002**: A runner given only `core.md` can produce a syntactically correct
  invocation of every CLI verb without consulting `flow.py` or any other file.
- **SC-003**: Every `HLD-VERIFY` invariant that touches HLD-001's scope (the runner
  contract, the baton, the binary reply rule) is cited by ID in at least one test.
- **SC-004**: Neither `README.md` nor `core.md` names a specific AI system; the
  "names no AI" test (`test_flow.py`) remains green after any update to either file.

---

## Assumptions

- `README.md` and `core.md` are the two primary deliverables; no other documentation
  files are in scope for this spec.
- The current `flow.py` CLI is the reference implementation; the spec describes the
  intended documented state, not a new implementation.
- HLD-011's stripped-scope list is already correct and stable; this spec records it,
  not decides it.
- The brownfield implementation (`flow.py`, 45 tests green) is the baseline; this spec
  drives documentation completeness, not code changes.
