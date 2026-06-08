# Feature Specification: What it is

**Feature Branch**: `001-what-it-is`

**Created**: 2026-06-08

**Status**: Draft

**Input**: User description: "Build What it is. Planned spec id: 001. Source HLD sections: HLD-001."

## Source Trace

- **HLD-001**: What Baton Flow is: producing trustworthy outputs across AI-assisted sessions.
- **Scope boundary**: This spec defines the product purpose and user-visible value model. It does not define CLI verbs, persistence schema, task lifecycle mechanics, baton internals, recovery, or implementation behavior.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Recognize the deliverable (Priority: P1)

A human steering AI-assisted work can identify the report as the durable deliverable Baton Flow exists to produce, not as a side effect of task execution.

**Why this priority**: HLD-001 says the report is the point of the system; all other mechanics exist to make good reports possible.

**Independent Test**: Review the product-facing description and verify that it names trustworthy report output as the primary outcome before describing the baton or task mechanics.

**Acceptance Scenarios**:

1. **Given** a human asks what Baton Flow is for, **When** they read the product description, **Then** they can state that the system exists to produce trustworthy reports across AI-assisted sessions.
2. **Given** a runner or human sees references to tasks and baton context, **When** they compare those references to the product purpose, **Then** tasks and baton are presented as means to produce the report, not as the final deliverable.

---

### User Story 2 - Preserve value across handoffs (Priority: P2)

A human can start multi-step AI-assisted work with confidence that context survives handoffs so the output improves over time instead of restarting from scratch.

**Why this priority**: HLD-001 names context survival across AI sessions as the durable mechanism that lets reports accumulate value.

**Independent Test**: Verify that the specification distinguishes persistent handoff context from ephemeral session memory and ties that persistence to report quality.

**Acceptance Scenarios**:

1. **Given** work spans multiple AI sessions, **When** a new runner claims work, **Then** the system purpose requires enough durable context for the runner to continue toward the report without starting over.
2. **Given** context is handed off, **When** the work result is added, **Then** the result becomes part of the output path rather than isolated session-only text.

---

### User Story 3 - See and steer work (Priority: P3)

A human can see ongoing work and steer it without discarding the accumulated context or restarting the report.

**Why this priority**: HLD-001 identifies visibility and steering as core pains the system must remove, while keeping the report as the primary outcome.

**Independent Test**: Verify that visibility and steering are described as product needs without specifying implementation-specific commands or storage.

**Acceptance Scenarios**:

1. **Given** AI-assisted work is underway, **When** the human checks progress, **Then** the system purpose requires visible work state and accumulated context.
2. **Given** the human needs to steer the work, **When** they provide direction, **Then** the direction must guide continued work without forcing a new start.

### Edge Cases

- If a description focuses only on baton mechanics, task queues, or handoff mechanics, it must be corrected to state that those are means and the report is the deliverable.
- If a report is treated as transient session output, it must be corrected to a durable deliverable that accumulates value as work proceeds.
- If visibility or steering is described as replacing human decision ownership, it must be corrected: the human sees and steers at any moment.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The product definition MUST state that Baton Flow exists to produce trustworthy report outputs across AI-assisted sessions.
- **FR-002**: The product definition MUST distinguish reports as durable deliverables that accumulate value as work proceeds.
- **FR-003**: The product definition MUST describe tasks as claimable units of work whose results become part of an output path.
- **FR-004**: The product definition MUST describe runners as AI sessions or humans that claim tasks and contribute work results.
- **FR-005**: The product definition MUST describe baton context as the durable, readable, steerable context that survives handoffs.
- **FR-006**: The product definition MUST state that the baton is the means for producing good reports, not the product's final purpose.
- **FR-007**: The product definition MUST cover the three baseline pains HLD-001 names: context loss between sessions, lack of visibility, and inability to steer without restarting.
- **FR-008**: The product definition MUST keep implementation details out of this purpose spec; CLI contract, persistence, task lifecycle, and recovery behavior belong to later specs.
- **FR-009**: Any future product, spec, or task wording for this feature MUST preserve the source-of-truth relationship to HLD-001 and must not demote the report below baton mechanics.

### Key Entities

- **Report**: The durable deliverable Baton Flow is for; it accumulates value from work results across AI-assisted sessions.
- **Task**: A claimable unit of work created by a human or the system; its result contributes to an output path.
- **Runner**: An AI session or human that claims and works a task.
- **Baton Context**: Durable, readable, steerable context that survives handoffs and lets work continue toward a good report.
- **Human Steering**: Human visibility and direction applied while preserving accumulated context.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A reviewer can identify the report as the primary deliverable from the generated spec, plan, and task list without reading implementation files.
- **SC-002**: Every user story and functional requirement in this spec traces to HLD-001 and avoids introducing behavior from unrelated HLD sections.
- **SC-003**: The spec contains zero unresolved clarification placeholders before planning.
- **SC-004**: The implementation task list for this feature contains no code-changing task that is not explicitly tied to preserving or surfacing the HLD-001 purpose model.

## Assumptions

- This feature is a governance and product-purpose slice; it may update product-facing descriptions, tests, or documentation later, but it does not by itself define new runtime mechanics.
- "Report", "task", "runner", and "baton" are used in the HLD-001 sense. Dedicated vocabulary and interface details are owned by later specs.
- Existing product code is not inspected or modified during this pre-implementation bundle.
