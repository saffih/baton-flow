# Tasks: Work Routing (Soft Affinity by Label and Named Sessions) (HLD-010)

**Input**: Design documents from `specs/023-work-routing/`

**Prerequisites**: plan.md ✓, spec.md ✓

## Phase 1: Baseline Verification

**Purpose**: Confirm 57 prior tests pass before adding any new test.

- [x] T001 Confirm `pytest test_flow.py` exits 0 with exactly 57 passed (baseline)

---

## Phase 2: SC-005 — HLD-010 VERIFY Invariant Citation

**Purpose**: Add one new test that cites the HLD-010 VERIFY text by ID, exercising the full routing invariant end-to-end.

- [x] T002 Confirm `test_hld010_verify_invariant` is absent from `test_flow.py` (RED check)
- [x] T003 Add `test_hld010_verify_invariant` to `test_flow.py` with docstring citing `"HLD-010 VERIFY"` and full text; assert backward compat (no session), session bind + affinity, and fallback
- [x] T004 Confirm `pytest test_flow.py -k test_hld010_verify_invariant` passes (GREEN)
- [x] T005 Confirm `pytest test_flow.py` exits 0 with exactly 58 passed (ratchet: 57 + 1)

---

## Dependencies

- T002 → T003 (must confirm RED before writing)
- T003 → T004 → T005 (sequential)
- T001 must pass before T002
