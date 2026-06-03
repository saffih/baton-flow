# Tasks: The CLI Contract (HLD-009)

**Input**: Design documents from `specs/017-cli-contract/`

**Feature**: Characterization tests and contract documentation for the 11-verb CLI surface
(8 runner + 3 human/ops). `flow.py` already implements all verbs correctly — no source
code changes. All new tests added to `test_flow.py`.

**Brownfield constraint**: TDD RED step = confirm test function absent before writing it.
After writing, run isolated → then full suite. Constitution Principle IV: NON-NEGOTIABLE.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no incomplete-task dependencies)
- **[Story]**: User story this task belongs to

---

## Phase 1: Setup — Slice A Baseline

**Purpose**: Confirm the 47-test baseline is green before any additions.

**Independent Test**: `pytest test_flow.py` exits 0 with exactly 47 passed.

- [x] T001 Run `pytest test_flow.py` and confirm exactly 47 tests pass — Slice A gate

---

## Phase 3: User Story 1 — Runner Work Cycle (Priority: P1) — Slice B

**Goal**: Each runner verb (`add`, `next`, `context`, `note`, `done`, `escalate`, `decide`)
has at least one characterization test in `test_runner_verb_contracts` that exercises its
core contract in isolation.

**Independent Test**: `pytest test_flow.py::test_runner_verb_contracts` passes; all 47 prior
tests still green.

- [x] T002 [US1] Confirm `test_runner_verb_contracts` is absent from `test_flow.py` (RED gate: `grep test_runner_verb_contracts test_flow.py` returns nothing)
- [x] T003 [US1] Write `test_runner_verb_contracts` in `test_flow.py` covering: `flow add` creates a pending task; `flow next` on empty DB returns "none"; `flow next` on non-empty DB returns and claims a task; `flow context` returns baton for claimed task; `flow note` appends text to baton; `flow done` completes task with stated outcome; `flow escalate` transitions task to blocked; `flow decide` records decision on baton
- [x] T004 [US1] Run `pytest test_flow.py::test_runner_verb_contracts` — confirm GREEN; then run `pytest test_flow.py` — confirm all 47 prior tests still pass

---

## Phase 4: User Story 2 — Fork-Join via Split (Priority: P2) — Slice B (split)

**Goal**: `flow split` behavior is characterized in `test_runner_verb_contracts`: split
creates child tasks (pending), transitions parent to blocked, and parent wakes to pending
when all children are done.

**Independent Test**: `pytest test_flow.py::test_runner_verb_contracts` passes including
split scenario; full suite still green.

- [x] T005 [US2] Extend `test_runner_verb_contracts` in `test_flow.py` with split scenario: assert `flow split <id> "A" "B"` creates two child tasks (pending), transitions parent to blocked, and parent returns to pending after both children are marked done
- [x] T006 [US2] Run `pytest test_flow.py::test_runner_verb_contracts` — confirm split assertions GREEN; then run `pytest test_flow.py` — confirm all prior tests still pass

---

## Phase 5: User Story 3 — Human/Ops Separation (Priority: P3) — Slices C + D

**Goal**: Two new tests: (1) assert `reply`, `reopen`, `list` are absent from the
runner-permitted verb set in `core.md` (SC-002 — Slice C); (2) cite the HLD-009 VERIFY
invariant by ID and assert its structural guarantees (SC-003 — Slice D).

**Independent Test**: Both `test_human_ops_verbs_absent_from_runner_loop` and
`test_hld009_verify_invariant` pass; full suite still green.

- [x] T007 [P] [US3] Confirm `test_human_ops_verbs_absent_from_runner_loop` is absent from `test_flow.py` (RED gate: grep returns nothing)
- [x] T008 [P] [US3] Confirm `test_hld009_verify_invariant` is absent from `test_flow.py` (RED gate: grep returns nothing)
- [x] T009 [US3] Write `test_human_ops_verbs_absent_from_runner_loop` in `test_flow.py`: read `core.md`; assert `"flow reply"`, `"flow reopen"`, `"flow list"` are NOT substrings; assert all 8 runner verbs (`"flow add"`, `"flow next"`, `"flow context"`, `"flow note"`, `"flow done"`, `"flow escalate"`, `"flow split"`, `"flow decide"`) ARE present as substrings (Slice C)
- [x] T010 [US3] Run `pytest test_flow.py::test_human_ops_verbs_absent_from_runner_loop` — confirm GREEN; then run `pytest test_flow.py` — confirm all prior tests still pass (Slice C gate)
- [x] T011 [US3] Write `test_hld009_verify_invariant` in `test_flow.py`: function docstring cites `"HLD-009 VERIFY"` and the full invariant text `"runners use only the listed verbs; no direct database access; reply, reopen, and list are human/ops-facing and not part of the runner loop"`; assert `core.md` does not contain `"sqlite3"` or `".db"` as direct file references; assert only runner verbs appear as `"flow <verb>"` commands in `core.md` (Slice D)
- [x] T012 [US3] Run `pytest test_flow.py::test_hld009_verify_invariant` — confirm GREEN; then run `pytest test_flow.py` — confirm all prior tests still pass (Slice D gate)

---

## Phase N: Polish & Validation

**Purpose**: Final SC-005 regression gate — all prior + all new tests pass together.

- [x] T013 Run `pytest test_flow.py` — confirm all new tests and all 47 prior tests pass (total ≥ 50); this is the SC-005 gate
- [x] T014 [P] Review test names in `test_flow.py`: confirm `test_runner_verb_contracts`, `test_human_ops_verbs_absent_from_runner_loop`, `test_hld009_verify_invariant` are present and named exactly as specified
- [x] T015 Update `specs/017-cli-contract/plan.md` Agent Context between `<!-- SPECKIT START -->` and `<!-- SPECKIT END -->` markers to reflect tasks phase complete

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 3 (US1)**: Depends on Phase 1 (T001 baseline confirmed green)
- **Phase 4 (US2)**: Depends on Phase 3 (T003 written; T004 green before extending)
- **Phase 5 (US3)**: Depends on Phase 4 (T006 clean before adding more tests)
- **Phase N (Polish)**: Depends on all user story phases complete

### Within Each User Story

1. RED confirmation (grep absence) MUST precede writing the test
2. Write the test function in `test_flow.py`
3. Run the isolated test (e.g., `pytest test_flow.py::test_name`)
4. Run full suite — confirm all prior tests still green

### Parallel Opportunities

- T007 and T008 (both RED-gate greps on test_flow.py) can run together
- T014 and T015 (Polish phase review tasks) can run together

---

## Parallel Example: User Story 3 RED gate

```bash
# Both grep checks are read-only and independent — run together:
Task T007: "grep test_human_ops_verbs_absent_from_runner_loop test_flow.py"
Task T008: "grep test_hld009_verify_invariant test_flow.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (47 tests confirmed)
2. Complete Phase 3: US1 (`test_runner_verb_contracts` — 7 work-cycle verbs)
3. **STOP and VALIDATE**: full suite passes with 48+ tests

### Incremental Delivery

1. Phase 1 + Phase 3 → `test_runner_verb_contracts` (7 verbs) ✓
2. Phase 4 → split assertions added → 8-verb coverage complete ✓
3. Phase 5 → `test_human_ops_verbs_absent` + `test_hld009_verify_invariant` ✓
4. Phase N → SC-005 final gate (50+ tests, all green) ✓

---

## Notes

- All tests go in `test_flow.py` — no new test files (research.md decision)
- No changes to `flow.py`, `core.md`, or any source files — characterization only
- Constitution Principle IV: RED → write → GREEN → full suite green, every slice
- SC-005 gate: every slice run confirms all 47 prior tests remain green
