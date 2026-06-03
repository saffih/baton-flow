# Tasks: The Baton (Per-Task Document) (HLD-008)

**Input**: Design documents from `specs/022-the-baton/`

**Feature**: Characterization spec for the baton model. SC-001 and SC-002 covered by
existing tests. One new test needed: SC-003 (HLD-008 VERIFY invariant citation).

## Phase 1: Setup — Baseline

- [ ] T001 Run `pytest test_flow.py` and confirm exactly 56 tests pass — Slice A gate

---

## Phase 3: User Story 1 — Baton in Database (Priority: P1) — Slice B

**Goal**: One new test cites the HLD-008 VERIFY invariant by ID (SC-003).

- [ ] T002 [P] [US1] Confirm `test_hld008_verify_invariant` absent from `test_flow.py` (RED gate: grep returns nothing)
- [ ] T003 [US1] Write `test_hld008_verify_invariant` in `test_flow.py`: docstring cites "HLD-008 VERIFY" + full invariant text; add task; note it; delete markdown projection if it exists; assert `flow.context` still returns the note (baton lives in DB, read via CLI) (Slice B)
- [ ] T004 [US1] Run `pytest test_flow.py::test_hld008_verify_invariant` — confirm GREEN; then run full suite — confirm all 55 prior tests still pass

---

## Phase N: Polish

- [ ] T005 Run `pytest test_flow.py` — confirm 57 total tests pass (SC-004 gate)
- [ ] T006 Update `specs/022-the-baton/plan.md` Agent Context to reflect implementation complete

---

## Notes

- All tests go in `test_flow.py`
- No changes to `flow.py` or any source files
- SC-001 COVERED by test_context_survives_markdown_deletion
- SC-002 COVERED by test_projection_writes_markdown
