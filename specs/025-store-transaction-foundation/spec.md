# Feature Specification: Store & Transaction Foundation

**Feature Branch**: `025-store-transaction-foundation`

**Created**: 2026-07-05

**Status**: Draft

**Input**: User description: "Store and Transaction Foundation: one durable state store as single source of truth for all system state, with markdown projections as re-derivable derived views never part of a transaction; every CLI operation is one all-or-nothing transaction with WAL journaling and busy_timeout so a crash leaves no partial state"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Crash-safe CLI operations (Priority: P1)

An agent or engineer runs a CLI operation (e.g. claiming or completing a task). If the process is interrupted at any point — including mid-write — the system state must never be left half-updated.

**Why this priority**: This is the foundational reliability guarantee every other feature depends on. Without all-or-nothing transactions, every downstream task-lifecycle, escalation, or recovery feature would be exposed to silent corruption.

**Independent Test**: Can be fully tested by interrupting a CLI operation (e.g. killing the process mid-transaction) and verifying the store shows either the pre-operation state or the fully-completed post-operation state, never a partial mix.

**Acceptance Scenarios**:

1. **Given** the store is in a known state, **When** a CLI operation is interrupted before it commits, **Then** the store reflects the pre-operation state with no partial writes.
2. **Given** the store is in a known state, **When** a CLI operation completes normally, **Then** the store reflects the fully-applied result of that operation as a single unit.

---

### User Story 2 - Reading context from a single derived view (Priority: P2)

An agent needs to read current task/context state (stable IDs, task references, baton/context state, reply context, links to reports/logs) without querying the store's internal representation directly.

**Why this priority**: This is the read-side contract that lets agents integrate without depending on store internals, decoupling the CLI/store implementation from every consumer.

**Independent Test**: Can be fully tested by performing a store-changing CLI operation, then reading only the generated markdown projection and confirming it reflects the change with all required elements (stable IDs, task references, baton/context state, reply context, report/log links) present.

**Acceptance Scenarios**:

1. **Given** a completed CLI operation that changed store state, **When** the markdown projection is regenerated, **Then** it reflects the new state and preserves stable IDs, task references, baton/context state, reply context, and links to relevant reports/logs.
2. **Given** a markdown projection, **When** an agent or user attempts to use it as a write path, **Then** the system provides no mechanism to persist changes through the projection — all writes must go through the CLI.

---

### User Story 3 - Safe concurrent task claiming (Priority: P3)

Two CLI invocations (e.g. two `flow next` calls) run at, or close to, the same time. Only one may claim a given runnable task; the other must wait or see the already-claimed state, never a race that claims the same task twice.

**Why this priority**: Concurrency safety is what makes the store trustworthy under real multi-agent or multi-process usage, but it builds on (and is testable independently of) the single-operation atomicity guaranteed by User Story 1.

**Independent Test**: Can be fully tested by issuing two concurrent claim operations against the same runnable task and confirming exactly one succeeds in claiming it while the other observes the task as already claimed (or waits and then observes it as claimed).

**Acceptance Scenarios**:

1. **Given** one runnable task and two concurrent claim attempts, **When** both attempts execute, **Then** exactly one attempt records claimed-by on the task/baton and the other does not claim the same task.
2. **Given** a claim operation in progress, **When** a second, concurrent writer attempts to write, **Then** the second writer waits rather than failing immediately or corrupting state.

---

### Edge Cases

- What happens when the CLI process is killed between taking the write lock and committing the transaction? The store must show no trace of the in-flight change (rolled back), and the lock must not remain held.
- How does the system handle a markdown projection that is out of date relative to the store (e.g. regeneration was skipped or failed)? The projection is always re-derivable from the store, so a missing or stale projection must never be treated as authoritative — the store remains the source of truth.
- What happens if a second writer's wait for the write lock exceeds the busy timeout? The waiting operation must fail cleanly (no partial write) rather than silently proceeding with an inconsistent read.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST maintain exactly one durable state store that is the single source of truth for all system state.
- **FR-002**: The system MUST generate markdown projections as derived views of the store; a projection MUST be fully re-derivable from the store and MUST NOT be part of any transaction.
- **FR-003**: Markdown projections MUST carry three roles: an agent integration/handoff surface, context state for work in progress, and user-facing context and reporting.
- **FR-004**: A projection that an agent reads directly MUST preserve stable IDs, task references, baton/context state, reply context, and links to relevant reports/logs.
- **FR-005**: The system MUST NOT accept writes through a projection; all writes MUST go through the CLI.
- **FR-006**: The execution loop MUST depend on exactly two interfaces — a CLI and markdown/text — and MUST NOT name or depend on a specific AI implementation.
- **FR-007**: Every CLI operation MUST execute as one all-or-nothing transaction, such that a crash at any point leaves no partial state.
- **FR-008**: The task-claiming operation (`flow next`) MUST take the write lock before reading the queue, select the runnable task, record claimed-by on the baton, and claim the task — all within the same transaction.
- **FR-009**: The store connection MUST run with WAL journaling enabled, a busy_timeout configured so a concurrent writer waits rather than fails immediately, and synchronous mode set to NORMAL.
- **FR-010**: The system MUST write the markdown projection only after the underlying transaction commits, since the projection is a re-derivable view and never part of the transaction.

### Key Entities

- **Store**: The single durable source of truth for all system state; the only entity that transactions apply to.
- **Projection**: A markdown-rendered, re-derivable view of the store's state; never a write path; serves agent handoff, WIP context, and user reporting roles.
- **Transaction**: A single all-or-nothing unit of change applied to the store by one CLI operation.
- **Task / Baton**: The unit of work whose claimed-by state is recorded transactionally when claimed by a CLI operation such as `flow next`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of interrupted CLI operations (simulated crash at any point before commit) leave the store in either the pre-operation or fully-completed post-operation state — never a partial mix.
- **SC-002**: Users and agents can determine current task/context state entirely from the generated markdown projection, without needing to inspect the store directly.
- **SC-003**: Under concurrent task-claiming attempts against the same runnable task, exactly one attempt succeeds in every observed trial — zero double-claims.
- **SC-004**: Every requirement in this feature traces to a specific HLD section (HLD-003 or HLD-013), so reviewers can verify no untraceable behavior was introduced.

## Assumptions

- The specific storage engine is an implementation choice; this spec constrains only the durability, transactionality, and concurrency properties described in REQ-001 through REQ-010 (single source of truth, WAL journaling, busy_timeout, synchronous=NORMAL), not a named product.
- "Markdown projections" refers to the same class of generated, derived-view files described elsewhere in the HLD (agent handoff surface, WIP context, user-facing reporting); this feature defines their write/regeneration contract, not their specific layout.
- No implementation detail beyond what HLD-003 and HLD-013 state is assumed; all ten requirements (REQ-001–REQ-010) are already fully specified by the source HLD, so no [NEEDS CLARIFICATION] markers are required for this feature.
