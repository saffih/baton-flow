# Tasks: The Task Lifecycle (HLD-004)

**Input**: Design documents from `specs/018-task-lifecycle/`

**Feature**: Characterization spec for the four-state task lifecycle. `flow.py` already
implements all states and guards. SC-001..005 are covered by 51 existing tests. Only
SC-006 (HLD-004 VERIFY citation) needs a new test.

**Brownfield constraint**: TDD RED step = confirm test function absent before writing.
All new tests go in `test_flow.py`. No source file changes.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup — Slice A Baseline

**Purpose**: Confirm 51-test baseline is green before any additions.

**Independent Test**: `pytest test_flow.py` exits 0 with exactly 51 passed.

- [ ] T001 Run `pytest test_flow.py` and confirm exactly 51 tests pass — Slice A gate

---

## Phase 3: User Story 1 — Full Lifecycle (Priority: P1) — SC-001..005 + SC-006

**Goal**: All six SCs documented and guarded. SC-001..005 are satisfied by existing tests
(listed in plan.md coverage map). SC-006 requires one new test that cites the HLD-004
VERIFY invariant by ID.

**Independent Test**: `pytest test_flow.py::test_hld004_verify_invariant` passes; all 51
prior tests still green.

- [ ] T002 [US1] Confirm `test_hld004_verify_invariant` is absent from `test_flow.py` (RED gate: `grep test_hld004_verify_invariant test_flow.py` returns nothing)
- [ ] T003 [US1] Write `test_hld004_verify_invariant` in `test_flow.py`: docstring cites `"HLD-004 VERIFY"` and full text `"only four states exist; a task cannot be done with unfinished children; done is reopenable; blocked wakes to pending only when all dependencies resolve"`; assert `flow.STATES == ("pending", "in_progress", "blocked", "done")`; assert reopen callable on a done task; assert done raises on a task with an unfinished child
- [ ] T004 [US1] Run `pytest test_flow.py::test_hld004_verify_invariant` — confirm GREEN; then run `pytest test_flow.py` — confirm all 51 prior tests still pass (Slice B gate)

---

## Phase N: Polish & Validation

**Purpose**: Final SC-007 regression gate.

- [ ] T005 Run `pytest test_flow.py` — confirm all 52 tests pass (51 prior + 1 new)
- [ ] T006 Update `specs/018-task-lifecycle/plan.md` Agent Context between `<!-- SPECKIT START -->` and `<!-- SPECKIT END -->` markers to reflect implementation complete

---

## Dependencies & Execution Order

- **Phase 1**: Start immediately
- **Phase 3**: Depends on T001 (baseline confirmed)
- **Phase N**: Depends on T004 (all tests green)

### Within US1

1. RED confirmation (T002) MUST precede writing the test (T003)
2. Write test (T003) before running it (T004)
3. Run isolated test before full suite (T004)

---

## Implementation Strategy

### MVP

1. Phase 1: confirm 51 baseline
2. Phase 3: write test_hld004_verify_invariant
3. Phase N: final regression

---

## Notes

- All tests go in `test_flow.py` — no new test files
- No changes to `flow.py`, `core.md`, or any source files
- SC-001..005 are COVERED — no new tests needed for those SCs
- SC-007 gate: every slice confirms all 51 prior tests remain green
