# Tasks: Human-in-the-Loop (Human → Runner) (HLD-007)

**Input**: Design documents from `specs/021-human-in-loop/`

**Feature**: Characterization spec for the human reply routing rule. SC-001 and SC-002 covered
by existing tests. One new test needed: SC-003 (HLD-007 VERIFY invariant citation).

## Phase 1: Setup — Baseline

- [ ] T001 Run `pytest test_flow.py` and confirm exactly 55 tests pass — Slice A gate

---

## Phase 3: User Story 1 — Reply Unblocks Task (Priority: P1) — Slice B

**Goal**: One new test cites the HLD-007 VERIFY invariant by ID (SC-003).

- [ ] T002 [P] [US1] Confirm `test_hld007_verify_invariant` absent from `test_flow.py` (RED gate: grep returns nothing)
- [ ] T003 [US1] Write `test_hld007_verify_invariant` in `test_flow.py`: docstring cites "HLD-007 VERIFY" + full invariant text; add task; escalate it (blocked); call `flow.reply(conn, tid, "answer")`; assert state==pending and a reply entry appears on context (Slice B)
- [ ] T004 [US1] Run `pytest test_flow.py::test_hld007_verify_invariant` — confirm GREEN; then run full suite — confirm all 54 prior tests still pass

---

## Phase N: Polish

- [ ] T005 Run `pytest test_flow.py` — confirm 56 total tests pass (SC-004 gate)
- [ ] T006 Update `specs/021-human-in-loop/plan.md` Agent Context to reflect implementation complete

---

## Notes

- All tests go in `test_flow.py`
- No changes to `flow.py`, `core.md`, or any source files
- SC-001 COVERED by test_reply_wakes_task + test_reply_recorded_on_baton
- SC-002 COVERED by test_binary_reply_rule_in_core_md
