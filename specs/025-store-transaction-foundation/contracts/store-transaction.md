# Contract: Store & Transaction

**Feature**: `025-store-transaction-foundation` | Traces: FR-001, FR-006–FR-010; HLD-013

The external interface of this feature is the `flow` CLI. This contract states what any
caller (runner, human, script) may rely on for every CLI operation, and what any
storage-engine implementation must provide.

## Single store

- Exactly one durable state store per repository is the single source of truth for all
  system state (FR-001).
- No caller writes to the store except through a CLI verb (FR-005/FR-006). The execution
  loop depends only on the CLI and markdown/text and names no specific AI (FR-006).

## One operation = one transaction (FR-007)

- Every CLI operation executes as exactly one all-or-nothing transaction.
- If the operation succeeds, all of its effects are visible atomically.
- If the process crashes or fails **at any point** before commit, the store reflects the
  pre-operation state: no partial writes, no orphaned locks blocking the next writer.
- No transaction ever spans more than one CLI operation.

## Atomic claim protocol (FR-008) — `flow next`

Within a single transaction, in order:
1. Acquire the write lock **before** reading the queue (`BEGIN IMMEDIATE` in the chosen
   implementation).
2. Select the runnable task (no open escalations, no unfinished children; lease-expired
   orphans reclaimed inside this same transaction).
3. Record claimed-by `<session>` on the task's baton.
4. Mark the task claimed (assignee set, state `in_progress`).

Guarantee: two concurrent claim attempts on one runnable task never both succeed —
exactly one claims; the other observes it already claimed or waits (SC-003).

## Durability & concurrency properties (engine-agnostic — resolves T1)

Any storage engine backing this contract MUST provide:

| Property | Requirement |
|---|---|
| Atomic commit | All-or-nothing per operation; crash yields pre-operation state |
| Writer serialization | A write lock acquirable before reads within the transaction (safe read-then-write) |
| Reader concurrency | Readers proceed while a writer is active |
| Bounded-wait contention | A competing writer waits (bounded), rather than failing immediately |
| Clean timeout | A writer exceeding the wait bound fails with an error and **no partial write** |
| Durability class | Committed work survives process crash; at most the most recent committed transaction(s) may be lost on power failure, with the store still consistent |

### Chosen-implementation bindings (SQLite — FR-009)

The current implementation delivers the properties via, and MUST run with:
- `PRAGMA journal_mode=WAL` (reader concurrency + atomic commit)
- `PRAGMA busy_timeout=<bound>` (bounded-wait contention; currently 5000 ms)
- `PRAGMA synchronous=NORMAL` (durability class above — see atomicity note)
- Explicit transaction control (`isolation_level=None`; `BEGIN IMMEDIATE … COMMIT/ROLLBACK`)

These pragma names bind the SQLite implementation only; a replacement engine satisfies
this contract by meeting the property table, not by emulating pragmas.

### Atomicity vs durability (resolves T3)

FR-007 is an **atomicity** guarantee. Under synchronous=NORMAL, a power loss may drop
the most recent committed transaction(s); it can never produce partial state. Callers
MUST NOT treat commit acknowledgment as power-loss-durable; they MAY treat the store as
consistent (pre- or post-some-transaction) at every observable point.

## Error behavior

- A writer that exceeds the wait bound fails cleanly: nonzero exit, no partial write,
  no held lock (spec edge case 3).
- Any failure inside an operation rolls the entire operation back; the CLI reports the
  error and the store is untouched.
