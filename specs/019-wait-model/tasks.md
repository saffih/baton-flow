# Tasks: The Wait Model (Fork-Join) (HLD-005)

**Input**: Design documents from `specs/019-wait-model/`

**Feature**: Characterization spec for escalate/split as unified parking primitives.
SC-001..004 covered by 52 existing tests. Only SC-005 (HLD-005 VERIFY citation) needs a new test.

## Phase 1: Setup — Baseline

- [ ] T001 Run `pytest test_flow.py` and confirm exactly 52 tests pass — Slice A gate

---

## Phase 3: User Story 1 — Parking Primitives (Priority: P1) — SC-005

**Goal**: `test_hld005_verify_invariant` cites HLD-005 VERIFY by ID and asserts escalate
and split both park as blocked, and `flow next` is callable after both.

- [ ] T002 [US1] Confirm `test_hld005_verify_invariant` is absent from `test_flow.py` (RED gate: grep returns nothing)
- [ ] T003 [US1] Write `test_hld005_verify_invariant` in `test_flow.py`: docstring cites `"HLD-005 VERIFY"` and full text `"escalate and split both park the task as blocked and free the runner; a task is runnable only when it has no unmet dependencies"`; assert escalating a task transitions it to `blocked`; assert splitting a task transitions parent to `blocked`; assert `flow.next_task` is callable (returns None or a task) after both operations
- [ ] T004 [US1] Run `pytest test_flow.py::test_hld005_verify_invariant` — confirm GREEN; then run `pytest test_flow.py` — confirm all 52 prior tests still pass

---

## Phase N: Polish

- [ ] T005 Run `pytest test_flow.py` — confirm 53 total tests pass (SC-006 gate)
- [ ] T006 Update `specs/019-wait-model/plan.md` Agent Context to reflect implementation complete

---

## Notes

- All tests go in `test_flow.py` — no new test files
- No changes to `flow.py` or any source files
- SC-001..004 COVERED by existing tests
