# Tasks: Orphaned-work recovery (HLD-014)

**Input**: ./spec.md, ./plan.md  ·  **Tests**: required (HIGH-risk anchor; TDD).

Format: `[ID] [P?] [Story] Description`. Tests are written first and must fail (red)
before the implementation makes them pass (green).

## Foundation

- [ ] T001 Add `tasks.reclaim_count INTEGER NOT NULL DEFAULT 0` to `SCHEMA`, and an
  idempotent migration in `connect()` (`PRAGMA table_info` → `ALTER TABLE` if missing).
  Add index `idx_tasks_state_updated (state, updated_at)`.
- [ ] T002 Add module constants `LEASE_TTL` (seconds, generous) and `RECLAIM_MAX`.

## User Story 1 — reclaim orphaned tasks (P1)

- [ ] T010 [US1] Test: `test_orphaned_task_reclaimed` — claim as A, age `updated_at` past
  TTL, `flow next` as B reclaims it (pending→in_progress to B, reclaim_count=1, baton has
  `reclaimed`). Cite HLD-014.
- [ ] T011 [US1] Test: `test_fresh_claim_not_reclaimed` — in-TTL task is not reclaimed.
- [ ] T012 [US1] Test: `test_blocked_task_never_reclaimed` — a blocked task past TTL stays blocked.
- [ ] T013 [US1] Test: `test_progress_refreshes_lease` — `note` bumps `updated_at`, preventing reclaim.
- [ ] T014 [US1] Implement `_reclaim_orphans(conn)` and call it inside `next_task`'s tx
  before the SELECT. Make T010–T013 green.

## User Story 2 — fence stale owners (P1)

- [ ] T020 [US2] Test: `test_stale_owner_cannot_done` — A reclaimed to B; A's
  `done`/`escalate`/`split --session A` rejected. Cite HLD-014.
- [ ] T021 [US2] Test: `test_owner_can_complete` — holding session's verbs succeed.
- [ ] T022 [US2] Test: `test_blackboard_not_fenced` — `note`/`decide`/`reply` succeed for anyone.
- [ ] T023 [US2] Test: `test_no_session_task_unfenced` — legacy no-session done/escalate/split work.
- [ ] T024 [US2] Implement `_require_owner` + `session` param on `done`/`escalate`/`split`
  and the `--session` CLI flag. Make T020–T023 green.

## User Story 3 — escalate chronic orphans (P2)

- [ ] T030 [US3] Test: `test_repeated_reclaim_escalates` — after `RECLAIM_MAX` reclaims,
  the next would-be reclaim escalates instead (state blocked, open escalation). Cite HLD-014.
- [ ] T031 [US3] Implement the escalate-on-repeat branch in `_reclaim_orphans`. Make T030 green.

## Polish

- [ ] T040 Update `core.md` runner loop note if the fence changes the verb contract surface.
- [ ] T041 Full suite green; `hld_verify_coverage --strict` passes for HLD-014.
