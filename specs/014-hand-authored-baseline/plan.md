# Implementation Plan: Orphaned-work recovery (HLD-014)

**Spec**: ./spec.md  ·  **HLD**: HLD-014 (HIGH)  ·  **Constitution**: `.specify/memory/constitution.md`

## Technical context

- Language: Python 3.10+ · Store: SQLite (WAL), single source of truth (HLD-003/012).
- Builds directly on HLD-013 (atomic claim, `_tx` BEGIN IMMEDIATE) and HLD-010 (`sessions`,
  `assignee` = holding session). No new dependencies, no daemon (HLD-011).

## Data model

- `tasks.reclaim_count INTEGER NOT NULL DEFAULT 0` — new column. Add via migration
  (`ALTER TABLE` if missing) so existing DBs upgrade; `CREATE TABLE IF NOT EXISTS` alone
  will not add a column to an old DB.
- Lease = existing `tasks.updated_at` (already bumped by every `_set_state` / claim /
  baton append). No new lease column.
- Constants in `flow.py`: `LEASE_TTL` (generous, e.g. 1 hour) and `RECLAIM_MAX` (e.g. 3).

## Approach

1. **Migration.** In `connect()`, after `executescript(SCHEMA)`, add `reclaim_count` to
   `tasks` if absent (introspect `PRAGMA table_info`). Idempotent.
2. **Reclaim (US1, US3).** New `_reclaim_orphans(conn, now_ts)` called inside `next_task`'s
   transaction, *before* the queue SELECT:
   - find `state='in_progress' AND updated_at < (now - LEASE_TTL)`;
   - for each: if `reclaim_count + 1 > RECLAIM_MAX` → escalate (open escalation + state
     `blocked`, append reason); else → state `pending`, `reclaim_count += 1`, append
     `reclaimed: session <assignee> silent since <updated_at>`, clear `assignee`.
   - Index `(state, updated_at)` to keep the per-`next` scan cheap.
3. **Fence (US2).** A new guard `_require_owner(conn, task_id, session)` used by `done`,
   `escalate`, `split`: load the task; if `assignee` is set (session-owned) and
   `assignee != session` → raise `FlowError("you no longer hold task N")`. If `assignee`
   is NULL (legacy/no-session) → allow. `note`/`decide`/`reply` do NOT call it.
   - This means `done`/`escalate`/`split` gain an optional `session=None` parameter and a
     `--session` CLI flag, mirroring `next`.

## Constitution check

- SQLite stays single source of truth; markdown projected after commit (HLD-003/013). ✓
- Runner contract stays minimal: `--session` is optional and additive; no-session behavior
  is unchanged (HLD-010 invariant). ✓
- Test-first / regression ratchet: HLD-014 is HIGH-risk, so it MUST have tests citing it
  (enforced by `test_every_high_risk_invariant_has_a_test`). ✓

## Risks / mitigations

- **False reclaim of a long, legitimately-silent operation** → mitigated by generous
  `LEASE_TTL` and by the fence: the original runner's later `done` is rejected and the work
  is safely redone, not double-completed.
- **Reclaim race** → runs under the claim's `BEGIN IMMEDIATE`; no separate transaction.
- **Time injection for tests** → `next_task` computes "now" via `now()`; tests fast-forward
  by writing an old `updated_at` directly, not by mocking the clock.
