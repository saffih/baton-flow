# Tasks: Escalation Triggers (Runner → Human) (HLD-006)

**Input**: Design documents from `specs/020-escalation-triggers/`

**Feature**: Characterization spec for four escalation triggers. SC-003 covered by existing
test. Two new tests needed: SC-001 (question on baton) and SC-002 (triggers in core.md).

## Phase 1: Setup — Baseline

- [ ] T001 Run `pytest test_flow.py` and confirm exactly 52 tests pass — Slice A gate

---

## Phase 3: User Story 1 — Escalation Mechanics (Priority: P1) — Slices B + C

**Goal**: Two new tests characterize the escalation question recording (SC-001) and the
four-trigger documentation in core.md (SC-002).

- [ ] T002 [P] [US1] Confirm `test_escalation_question_on_baton` absent from `test_flow.py` (RED gate: grep returns nothing)
- [ ] T003 [P] [US1] Confirm `test_escalation_triggers_in_core_md` absent from `test_flow.py` (RED gate: grep returns nothing)
- [ ] T004 [US1] Write `test_escalation_question_on_baton` in `test_flow.py`: add task; call `flow.escalate(conn, tid, "which path?")`; call `flow.context`; assert an entry with `kind == "escalation"` and `"which path?" in text` exists on the baton (Slice B)
- [ ] T005 [US1] Run `pytest test_flow.py::test_escalation_question_on_baton` — confirm GREEN; then run full suite — confirm all 52 prior tests still pass
- [ ] T006 [US1] Write `test_escalation_triggers_in_core_md` in `test_flow.py`: read `core.md`; assert each trigger name is present: `"Ambiguity"`, `"Authority"`, `"Irreversibility"`, `"Repeated failure"` (Slice C)
- [ ] T007 [US1] Run `pytest test_flow.py::test_escalation_triggers_in_core_md` — confirm GREEN; then run full suite — confirm all prior tests still pass

---

## Phase N: Polish

- [ ] T008 Run `pytest test_flow.py` — confirm 54 total tests pass (SC-004 gate)
- [ ] T009 Update `specs/020-escalation-triggers/plan.md` Agent Context to reflect implementation complete

---

## Notes

- All tests go in `test_flow.py`
- No changes to `flow.py`, `core.md`, or any source files
- SC-003 COVERED by test_cannot_escalate_done_task
