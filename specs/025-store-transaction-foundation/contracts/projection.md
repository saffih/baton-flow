# Contract: Markdown Projection

**Feature**: `025-store-transaction-foundation` | Traces: FR-002–FR-005, FR-010; HLD-003, HLD-008

## Read-path framing (T2)

The canonical read path is the CLI against the database; the markdown projection is a
derived handoff/integration surface, **never a write path** (HLD-008). Consumers that
need authoritative state use CLI verbs (`flow context <id>`, `flow list`). A projection
is non-authoritative by definition: stale or missing projections imply nothing about
store state (spec edge case 2).

## What a projection is

A markdown rendering of one task's baton, at `.flow/batons/<id>.md`, fully re-derivable
from the store at any time (FR-002). It carries three roles (FR-003):
1. Agent integration/handoff surface
2. Context state for work in progress
3. User-facing context and reporting

## Required preserved elements (FR-004)

A projection an agent reads directly MUST preserve:
- Stable IDs (task ID; per-escalation IDs where present)
- Task references (parent/children/related tasks)
- Baton/context state (state, assignee, label, outcome, appended entries in order)
- Reply context (questions asked and answers given)
- Links to relevant reports/logs

A projection missing any of these is a defective rendering — consumers fall back to the
CLI read path; they never patch the file.

## Write rules

- **Never a write path** (FR-005): the system provides no mechanism to persist changes
  through a projection. Edits to projection files are ignored by the system and
  overwritten on next regeneration. All writes go through the CLI.
- **Never part of a transaction** (FR-002): projection I/O occurs outside every store
  transaction.
- **Post-commit only** (FR-010): a projection is (re)generated only after the underlying
  transaction commits, from a fresh read of committed state.
- **Best-effort**: projection write failure never fails, blocks, or rolls back the
  committed operation. The store remains correct; the projection regenerates on the next
  touch.

## Regeneration & deletion

- Deleting any projection loses no data; the store re-derives it (CONTRACT-SINGLE-STORE).
- Regeneration is idempotent: same store state → same required elements present.
