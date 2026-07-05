# Quickstart: Store & Transaction Foundation

**Feature**: `025-store-transaction-foundation`

How to exercise and verify the foundation guarantees locally. All commands run from the
repository root. Note: mandatory sessions on every call (HLD-009, reads included) are
target design; the current CLI accepts `--session` only on `next`, `done`, `escalate`,
and `split` — the commands below match the current CLI.

## 1. Basic operation → store → projection

```bash
./flow add "demo task"
./flow next --session me            # atomic claim: prints the claimed task id
./flow context 1                    # canonical read path: CLI against the store
cat .flow/batons/1.md               # derived projection (read-only surface)
```

Verify: the projection reflects the claim (state, claimed-by) and preserves the FR-004
elements — stable ID, references, baton/context state, reply context, report/log links.

## 2. Projection is derived, never authoritative

```bash
rm .flow/batons/1.md                # delete the projection
./flow context 1                    # nothing lost: the store is the source of truth
./flow note 1 "still here"
cat .flow/batons/1.md               # regenerated after the commit (FR-010)
```

Editing `.flow/batons/1.md` by hand changes nothing: there is no write path through a
projection (FR-005) — the next regeneration overwrites it.

## 3. Crash safety (SC-001)

Interrupt a mutating operation before commit (e.g. kill the process mid-transaction) and
reopen the store:

- The store shows the pre-operation state — no partial writes.
- No lock remains held: the next writer proceeds normally.

The automated version is the crash-injection test (research Decision 5): a child process
is SIGKILLed between BEGIN and COMMIT; the test asserts pre-operation state and a
functioning subsequent writer.

## 4. Concurrent claiming (SC-003)

```bash
./flow add "contested task"
./flow next --session runner-a & ./flow next --session runner-b & wait
```

Exactly one session claims the task; the other observes `none` or an already-claimed
state. Never a double claim — the claim takes the write lock before reading the queue
(FR-008).

## 5. Connection settings (FR-009)

```bash
python3 - <<'EOF'
import sqlite3
c = sqlite3.connect(".flow/flow.db")
print("journal_mode:", c.execute("PRAGMA journal_mode").fetchone()[0])   # wal
print("busy_timeout:", c.execute("PRAGMA busy_timeout").fetchone()[0])   # >= 1000
print("synchronous:",  c.execute("PRAGMA synchronous").fetchone()[0])    # 1 (NORMAL)
EOF
```

Note the durability class (research Decision 3): commits survive process crash; on power
loss the most recent committed transaction(s) may be lost, but the store is never left
in a partial state — atomicity holds at every point.

## 6. Run the test suite

```bash
python3 -m pytest test_flow.py -q
```

Foundation-relevant coverage: connection hardening, concurrent claim uniqueness,
projection write + deletion-survivability, rollback on failure. Planned additions per
research Decisions 5–6: process-kill crash injection, busy-timeout clean failure,
FR-004 projection element completeness.
