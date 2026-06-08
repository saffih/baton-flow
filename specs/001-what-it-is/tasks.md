# Tasks: What it is

**Input**: Design documents from `/specs/001-what-it-is/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/purpose-contract.md, quickstart.md

**Tests**: Test/check tasks are included because the constitution requires verifiable preservation of product behavior and product-facing wording.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing after explicit implementation approval.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish the implementation guardrails for this purpose slice.

- [ ] T001 Read `specs/001-what-it-is/spec.md` and `specs/001-what-it-is/contracts/purpose-contract.md`; record the approved implementation surface before editing any product file.
- [ ] T002 Identify product-facing documentation or help surfaces that describe Baton Flow's purpose; do not include `flow.py` or `test_flow.py` unless a later human approval explicitly expands scope.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Create purpose-preservation checks before changing product-facing wording.

**CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T003 Add or update a purpose-preservation check that fails if Baton Flow is described without report-first language.
- [ ] T004 Add or update a check that fails if baton/task mechanics are described as the final product purpose instead of the means.

**Checkpoint**: Purpose-preservation checks exist and can fail before product-facing wording is changed.

---

## Phase 3: User Story 1 - Recognize the deliverable (Priority: P1) MVP

**Goal**: Product-facing wording identifies reports as Baton Flow's durable deliverable.

**Independent Test**: The purpose-preservation check fails before the wording update and passes after the wording clearly names trustworthy reports as the primary output.

### Tests for User Story 1

- [ ] T005 [P] [US1] Add a failing check for report-first product purpose in an approved documentation/help test location.

### Implementation for User Story 1

- [ ] T006 [US1] Update approved product-facing wording so the report is the primary durable deliverable.
- [ ] T007 [US1] Verify the updated wording still presents tasks, runners, and baton context as supporting mechanisms.

**Checkpoint**: User Story 1 is independently reviewable and preserves HLD-001.

---

## Phase 4: User Story 2 - Preserve value across handoffs (Priority: P2)

**Goal**: Product-facing wording explains context survival across AI-assisted handoffs.

**Independent Test**: The relevant check confirms that durable context survives handoffs and supports report quality without defining lower-level mechanics.

### Tests for User Story 2

- [ ] T008 [P] [US2] Add a failing check that product-facing wording ties handoff context to report quality.

### Implementation for User Story 2

- [ ] T009 [US2] Update approved product-facing wording to explain that baton context survives handoffs so work can continue toward the report.
- [ ] T010 [US2] Verify the wording does not introduce CLI, lifecycle, persistence, routing, or recovery rules.

**Checkpoint**: User Story 2 is independently reviewable and remains bounded to HLD-001.

---

## Phase 5: User Story 3 - See and steer work (Priority: P3)

**Goal**: Product-facing wording explains visibility and steering without restart.

**Independent Test**: The relevant check confirms that the human can see and steer work without losing accumulated context.

### Tests for User Story 3

- [ ] T011 [P] [US3] Add a failing check for visibility and steering without restart in an approved documentation/help test location.

### Implementation for User Story 3

- [ ] T012 [US3] Update approved product-facing wording to state that the human can see and steer work at any moment.
- [ ] T013 [US3] Verify the wording preserves human steering without implying the system replaces human decision ownership.

**Checkpoint**: User Story 3 is independently reviewable and preserves HLD-001.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final verification for this purpose slice.

- [ ] T014 Run the purpose-preservation checks added for this feature.
- [ ] T015 Review `README.md` and `docs/` changes, if any were approved, against `specs/001-what-it-is/contracts/purpose-contract.md`.
- [ ] T016 Run `git diff --check`.
- [ ] T017 Stop and report before any implementation beyond the approved task IDs.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Setup completion and blocks all user stories.
- **User Stories (Phase 3+)**: Depend on Foundational completion.
- **Polish (Phase 6)**: Depends on implemented approved stories.

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational phase.
- **User Story 2 (P2)**: Can start after Foundational phase; should not require User Story 1.
- **User Story 3 (P3)**: Can start after Foundational phase; should not require User Story 1 or 2.

### Parallel Opportunities

- T005, T008, and T011 can be prepared in parallel after T003 and T004 define the check pattern.
- Story wording updates can proceed in parallel only if they touch different approved files.

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1.
2. Complete Phase 2.
3. Complete Phase 3.
4. Stop and validate the report-first wording before broader purpose wording changes.

### Incremental Delivery

1. Preserve report-first purpose.
2. Add handoff context language.
3. Add visibility and steering language.
4. Re-run purpose-preservation checks and `git diff --check`.

## Implementation Gate

Implementation is blocked. Do not execute any task above until explicit human implementation approval exists for spec `001`.
