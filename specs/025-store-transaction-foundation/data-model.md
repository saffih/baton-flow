# Data Model: Store & Transaction Foundation

**Feature**: `025-store-transaction-foundation` | **Date**: 2026-07-05

The store is the single source of truth (FR-001). All entities below are store-owned;
the Projection is explicitly **not** an entity of record — it is a derived rendering.

## Store (container)

One durable store file per repository (`.flow/flow.db`). Sole target of transactions.
Holds all tables below. Deleting any projection loses nothing (FR-002); deleting the
store loses everything — that asymmetry is the definition of source of truth.

## Task

The unit of work whose claim/lifecycle state is transactionally owned.

| Field | Type | Rules |
|---|---|---|
| id | INTEGER PK | Stable ID; referenced by projections, escalations, baton entries |
| text | TEXT NOT NULL | The work description |
| state | TEXT NOT NULL | CHECK-constrained to exactly `pending`, `in_progress`, `blocked`, `done` |
| assignee | TEXT NULL | Claimed-by session; cleared on park/reclaim |
| label | TEXT NULL | Affinity/grouping; inherited by split children |
| parent_id | INTEGER NULL → tasks.id | Split parentage |
| outcome | TEXT NULL | Mandatory at done |
| reclaim_count | INTEGER NOT NULL DEFAULT 0 | Recovery bookkeeping |
| created_at / updated_at | TEXT NOT NULL | UTC ISO timestamps; updated_at doubles as lease stamp |

**State transitions** (all applied transactionally, one operation each):

```
pending ──(flow next: claim)──► in_progress
in_progress ──(flow done)──► done
in_progress ──(escalate / split: park)──► blocked
blocked ──(all dependencies resolved: wake)──► pending
done ──(reopen: rare human/ops path)──► pending
```

**Validation rules relevant to this feature**:
- Claiming (FR-008): write lock taken before the queue is read; select runnable task,
  set `assignee`, record claimed-by on the baton — all in the same transaction.
- Runnable = no open escalation and no unfinished child (dependency guard; enforced
  inside the claim transaction so it cannot race).
- The state CHECK constraint is enforced by the store itself, so no crash or partial
  write can produce a fifth state.

## Baton entry

Append-only log rows carrying a task's declared context (notes, decisions, claims,
replies). This is what the projection renders.

| Field | Type | Rules |
|---|---|---|
| id | INTEGER PK | Stable ID |
| task_id | INTEGER NOT NULL → tasks.id | Owning task |
| kind | TEXT NOT NULL | e.g. note, decision, claim, escalation, reply |
| text | TEXT NOT NULL | Entry content |
| created_at | TEXT NOT NULL | Attribution/ordering |

Rules: append-only within operations; the claimed-by record written by `flow next` is a
baton entry inside the claim transaction (FR-008).

## Escalation

An open escalation is a dependency that blocks its task.

| Field | Type | Rules |
|---|---|---|
| id | INTEGER PK | Stable per-escalation ID (individually resolvable) |
| task_id | INTEGER NOT NULL → tasks.id | Owning task |
| question | TEXT NOT NULL | What was asked |
| answer | TEXT NULL | NULL = open (blocking) |
| created_at / answered_at | TEXT | Lifecycle timestamps |

Rules: open escalations make a task non-runnable; answering is transactional and wake
occurs only when every dependency resolves.

## Session

Named identity for every CLI call; durable across reclaims.

| Field | Type | Rules |
|---|---|---|
| name | TEXT PK | The declared session name |
| bound_label | TEXT NULL | Soft affinity binding |
| created_at / updated_at | TEXT NOT NULL | Lifecycle |

## Transaction (concept, not a table)

One CLI operation = exactly one all-or-nothing transaction (FR-007):
`BEGIN IMMEDIATE` → operation reads/writes → `COMMIT`, or `ROLLBACK` on any failure.
Properties: write lock acquired up front (serializes writers; enables safe
read-then-write claiming); crash at any point yields pre-operation state; concurrent
writer waits up to busy_timeout, then fails cleanly with no partial write. Durability
class per research Decision 3 (atomicity always; last committed transaction(s) may be
lost on power failure under synchronous=NORMAL).

## Projection (derived artifact — NOT source of truth)

Markdown rendering of one task's baton at `.flow/batons/<id>.md`, written only after
the transaction commits (FR-010).

- **Roles** (FR-003): agent integration/handoff surface; context state for WIP;
  user-facing context and reporting.
- **Required preserved elements** (FR-004): stable IDs, task references, baton/context
  state, reply context, links to relevant reports/logs.
- **Rules**: fully re-derivable from the store; never a write path (FR-005 — no
  mechanism exists to persist changes through it); never part of a transaction
  (FR-002); staleness or absence is never authoritative — the canonical read path is
  the CLI against the database (T2 / HLD-008).

## Relationships

```
Store 1─* Task 1─* BatonEntry
              1─* Escalation (open ones block the task)
              *─1 Task (parent_id, split)
Session *──claims──* Task (via assignee + claimed-by baton entry, same transaction)
Task 1──renders to──1 Projection (derived, post-commit, re-derivable)
```
