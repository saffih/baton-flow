# Research: Store & Transaction Foundation

**Feature**: `025-store-transaction-foundation` | **Date**: 2026-07-05

The spec declares no unresolved clarification markers (spec.md, Assumptions). Research
therefore resolves the three inherited tensions carried into the plan (T1–T3) and fixes
the verification approach for the guarantees that existing tests do not yet cover.

## Decision 1 — Storage engine: SQLite as chosen implementation, engine-agnostic contract (T1)

**Decision**: Use SQLite (stdlib `sqlite3`) as the single durable store. Treat FR-009's
named pragmas (WAL, busy_timeout, synchronous=NORMAL) as binding on this chosen
implementation. Keep the contract engine-agnostic by expressing the required
**properties**: atomic all-or-nothing commit per operation, concurrent readers during a
write, bounded-wait (not fail-fast) writer contention, and the durability class defined
in Decision 3. A future engine swap must satisfy the properties, not the pragma names.

**Rationale**: This reconciles FR-009 with the spec's assumption that the engine is an
implementation choice (spec.md ~line 97) without weakening either: the requirement stays
testable against the real connection (`PRAGMA journal_mode`, `PRAGMA busy_timeout`,
`PRAGMA synchronous`), while HLD-003's "replaceable without product change" stays true
at the contract level. Zero-dependency, single-file store fits the tool's scale.

**Alternatives considered**:
- *Treat FR-009 as engine-neutral prose*: rejected — it names concrete settings; blurring
  them would make the requirement untestable.
- *Drop the agnostic assumption and hard-bind the contract to SQLite*: rejected —
  contradicts HLD-003 and the spec's own Assumptions section.
- *Other embedded stores (LMDB, flat files + locking)*: rejected — no property gap they
  close; new dependency or hand-rolled locking for no gain.

## Decision 2 — Transaction mechanism: explicit `BEGIN IMMEDIATE` per operation

**Decision**: Open connections with `isolation_level=None` (autocommit off the table;
transaction control is explicit) and wrap every mutating CLI operation in exactly one
`BEGIN IMMEDIATE … COMMIT`, rolling back on any exception. The claim path (`flow next`)
performs lease-reclaim scan, queue read, task claim, and claimed-by baton record inside
that single transaction (FR-008).

**Rationale**: `BEGIN IMMEDIATE` takes the write lock **before** the queue is read, which
is what makes read-then-write claiming race-free (two concurrent `flow next` calls
serialize; exactly one claims — SC-003). Python's implicit transaction management is
deferred-by-default and commits at surprising points; explicit control makes
"one operation = one transaction" (FR-007) inspectable in one wrapper.

**Alternatives considered**:
- *Deferred transactions + retry on conflict*: rejected — read-then-write races become
  possible between BEGIN and first write; retry logic is more code for a weaker property.
- *`BEGIN EXCLUSIVE`*: rejected — also blocks WAL readers' snapshots unnecessarily;
  IMMEDIATE is sufficient to serialize writers.
- *Advisory file locking around operations*: rejected — reimplements what the store's
  own locking already guarantees.

## Decision 3 — Durability class: synchronous=NORMAL under WAL; FR-007 is atomicity (T3)

**Decision**: Run WAL with synchronous=NORMAL and state the resulting durability class
explicitly in the contract: on **process crash**, all committed transactions survive and
an in-flight transaction fully rolls back; on **OS crash / power loss**, the most recent
committed transaction(s) may be lost, but the store is always consistent — pre- or
post-transaction state, never a partial mix. FR-007 ("crash at any point leaves no
partial state") is an **atomicity** guarantee and holds in every case; it is not a
power-loss durability guarantee.

**Rationale**: FR-009 mandates NORMAL, and NORMAL under WAL preserves exactly the
property FR-007 and SC-001 test for (no partial state). For a local task-coordination
store, losing the last committed claim on power failure is recoverable by the system's
own design (lease reclaim, re-derivable projections), whereas FULL's per-commit fsync
cost buys durability the product does not require. Making the distinction explicit
prevents the tension from resurfacing as a "bug" later.

**Alternatives considered**:
- *synchronous=FULL*: rejected — contradicts FR-009; pays fsync-per-commit for a
  durability class the feature does not promise.
- *synchronous=OFF*: rejected — sacrifices consistency on OS crash; violates FR-007.

## Decision 4 — Projection write ordering: post-commit, best-effort, re-derivable (T2)

**Decision**: Render the markdown projection only **after** the transaction commits
(FR-010), from a fresh read of the store, as a best-effort side effect. The canonical
read path is the CLI against the database; the projection is a derived
handoff/integration surface, never a write path (HLD-008). A missing, stale, or deleted
projection is never an error state — any consumer needing authoritative state uses
`flow context` / `flow list`.

**Rationale**: Keeping the projection out of the transaction (FR-002) means projection
I/O failures can never poison a committed state change, and re-derivability makes
repair trivial (regenerate on next touch). This is the T2 read-path framing applied to
writes: reads are architected against the store; projections serve handoff, WIP context,
and reporting roles only (FR-003).

**Alternatives considered**:
- *Write projection inside the transaction*: rejected — violates FR-002/FR-010 and
  couples filesystem failure modes to store atomicity.
- *Watcher/daemon regenerating projections*: rejected — new moving part; per-operation
  post-commit rendering already suffices at this scale.

## Decision 5 — Crash-safety verification: fault injection at the process boundary

**Decision**: Verify SC-001 with a crash-injection test: run a mutating operation in a
child process that is killed (SIGKILL) between the start of the transaction and commit
— injected via a hook/environment knob or by killing at a deterministic barrier — then
reopen the store and assert it equals the pre-operation state (and that a subsequent
writer is not blocked by a leftover lock; spec edge case 1).

**Rationale**: In-process exception tests already exercise ROLLBACK; only a killed
process exercises "crash at any point" and lock release for real. SIGKILL forbids
cleanup, making it the honest simulation.

**Alternatives considered**:
- *Exception-based rollback tests only*: rejected as sole coverage — does not test
  abrupt death or lock recovery.
- *Filesystem fault injection*: rejected — heavier harness than the guarantee needs.

## Decision 6 — Remaining verification gaps: busy-timeout clean failure, projection completeness

**Decision**: Add two targeted verifications alongside the existing suite (66 tests,
which already cover connection hardening, concurrent claim uniqueness, and
projection-deletion survivability): (a) a writer whose wait exceeds busy_timeout fails
cleanly with no partial write (spec edge case 3); (b) a regenerated projection preserves
all FR-004 elements — stable IDs, task references, baton/context state, reply context,
and links to relevant reports/logs.

**Rationale**: These are the only spec guarantees without a direct test today. Everything
else in FR-001–FR-010 traces to an existing test or to Decisions 2–5.

**Alternatives considered**:
- *Broad property-based concurrency suite*: rejected — the deterministic
  two-writer/timeout cases pin the contract; more machinery than the scale warrants.
