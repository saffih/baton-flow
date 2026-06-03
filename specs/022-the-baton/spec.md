# Feature Specification: The Baton (Per-Task Document) (HLD-008)

**Feature Branch**: `022-the-baton`

**Created**: 2026-06-03

**Status**: Draft

**Source HLD**: HLD-008 — `HLD-ROLE: architecture`, `HLD-RISK: HIGH`, `HLD-SPECS: constitution`
**HLD-VERIFY**: the baton lives in the database and is read via the CLI; markdown batons are a one-way projection; declared context is the only context the contract touches

**Input**: HLD-008 — blackboard model; database-owned baton; markdown is projection only

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — The baton is the durable, database-owned task document (Priority: P1)

All progress, decisions, escalations, replies, and notes live in the baton. The baton
persists in the database. Deleting the markdown projection does not lose any data; the
next runner reads the same complete baton from the CLI.

**Why this priority**: This is the lossless-handoff guarantee. If the baton lived outside
the database, any file deletion or sync issue would destroy declared context.

**Independent Test**: Delete the markdown projection for a task; verify that
`flow context` still returns the full baton from the database.

**Acceptance Scenarios**:

1. **Given** a task with notes recorded on its baton, **When** the markdown projection file is deleted, **Then** `flow context` still returns all baton entries from the database.
2. **Given** a task, **When** `flow context` is called, **Then** the runner receives the baton via the CLI, not by reading a file path directly.

---

### User Story 2 — Markdown batons are a one-way projection for human reading (Priority: P1)

Markdown files under `.flow/batons/` are generated from the database. They are convenient
for human inspection but are never the source of truth. Runners never read `.md` files
directly; they use `flow context`.

**Why this priority**: Confusing the projection with the source of truth would allow markdown
edits to silently diverge from the real baton, corrupting declared context.

**Independent Test**: The render function writes a markdown file; the database content is
unchanged if the file is deleted.

**Acceptance Scenarios**:

1. **Given** a task, **When** a markdown baton is rendered, **Then** a `.md` file is created under `.flow/batons/` that reflects the baton entries.
2. **Given** a markdown baton file, **When** it is deleted or modified, **Then** the database-sourced baton (via `flow context`) is unaffected.

---

### Edge Cases

- Declared context is the only context the contract touches. Runner working memory (session-internal state) is out of scope.
- The markdown projection is created as a side-effect of operations; runners must never rely on its existence.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The baton MUST reside in the database; all baton entries MUST be readable via `flow context`.
- **FR-002**: Markdown files under `.flow/batons/` MUST be a one-way projection: generated from the database, not authoritative.
- **FR-003**: Deleting a markdown projection MUST NOT cause any loss of baton data.

### Key Entities

- **Baton**: The per-task declared context. Lives in `baton_entries` table; rendered to `.flow/batons/<id>.md` as a read-only projection.
- **Declared context**: Notes, decisions, escalations, replies, done outcomes — everything appended via the CLI verbs.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A test asserts that deleting the markdown projection does not affect `flow context` output (database is SoT).
- **SC-002**: A test asserts that a markdown baton file is created under `.flow/batons/` when a task is created or updated (projection exists).
- **SC-003**: The HLD-008 VERIFY invariant ("the baton lives in the database and is read via the CLI; markdown batons are a one-way projection; declared context is the only context the contract touches") is cited by ID in at least one test.
- **SC-004**: All prior tests (55 at time of writing) remain green.

---

## Assumptions

- `flow.py` already implements the baton model correctly; this spec drives characterization tests only.
- The markdown projection path is `.flow/batons/<id>.md` relative to the database location.
- All new tests go in `test_flow.py`.
