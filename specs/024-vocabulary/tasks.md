# Tasks: Vocabulary (HLD-002)

**Input**: Design documents from `specs/024-vocabulary/`

**Prerequisites**: plan.md ✓, spec.md ✓

## Phase 1: Baseline Verification

**Purpose**: Confirm 58 prior tests pass before adding any new test.

- [x] T001 Confirm `pytest test_flow.py` exits 0 with exactly 58 passed (baseline; requires spec 010 test first)

---

## Phase 2: SC-001 — Vocabulary Terms in core.md

**Purpose**: Add one new test confirming the five HLD-002 vocabulary terms appear in `core.md`.

- [x] T002 Confirm `test_hld002_vocabulary_in_core_md` is absent from `test_flow.py` (RED check)
- [x] T003 Add `test_hld002_vocabulary_in_core_md` to `test_flow.py`; read `core.md` and assert each term is present: "runner", "task", "baton", "handoff", "decision" (case-insensitive; terms appear lowercase in prose)
- [x] T004 Confirm `pytest test_flow.py -k test_hld002_vocabulary_in_core_md` passes (GREEN)
- [x] T005 Confirm `pytest test_flow.py` exits 0 with exactly 59 passed (ratchet: 58 + 1)

---

## Dependencies

- T001 depends on spec 010 implementation (test_hld010_verify_invariant) being done first
- T002 → T003 (must confirm RED before writing)
- T003 → T004 → T005 (sequential)
