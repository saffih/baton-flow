# Tasks: Store & Transaction Foundation

**Input**: Design documents from `/specs/025-store-transaction-foundation/`

**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Test tasks are INCLUDED — they are the core deliverable of this feature. The plan
scopes this brownfield feature to (a) ratifying the existing implementation against
FR-001–FR-010 and (b) closing the three verification gaps named in research Decisions 5–6
(crash injection for SC-001, busy-timeout clean failure for spec edge case 3, FR-004
projection element completeness). No new modules, no new dependencies, no runtime rebuild.

**Organization**: Tasks are grouped by user story to enable independent implementation and
testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Single-file CLI tool at repository root (per plan.md Structure Decision — no `src/` split):

- Runtime: `flow.py` (not modified by this feature), CLI wrapper `flow`, loop contract `core.md`
- Tests: `test_flow.py` at repository root (existing pytest convention, 66 tests at baseline)
- Store: `.flow/flow.db`; projections: `.flow/batons/<id>.md` (runtime artifacts, not source files)

---

## Phase 1: Setup (Brownfield Baseline)

**Purpose**: Pin the green baseline before any change — this feature ratifies existing
behavior, so the starting state must be known-good.

- [X] T001 Confirm green brownfield baseline: run `python3 -m pytest test_flow.py -q` from the repository root and record that all 66 existing tests pass unmodified before any change in this feature

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Ratify the connection-level guarantees every user story's verification builds
on. Characterization before any test additions (brownfield rule).

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T002 Ratify FR-009 connection settings against the contract: in `test_flow.py`, verify `test_connection_hardening` asserts `journal_mode=WAL`, `busy_timeout` > 0 (bounded-wait contention), and `synchronous=NORMAL` for `flow.connect()` per `specs/025-store-transaction-foundation/contracts/store-transaction.md` § Chosen-implementation bindings; extend the test with any missing assertion, including explicit transaction control (`isolation_level=None` on the connection)

**Checkpoint**: Connection contract ratified — user story verification can begin

---

## Phase 3: User Story 1 - Crash-safe CLI operations (Priority: P1) 🎯 MVP

**Goal**: Prove FR-007/SC-001 on the existing runtime — a crash at any point before commit
leaves the store at exactly the pre-operation state, with no held lock blocking the next
writer.

**Independent Test**: Interrupt a CLI operation mid-transaction (kill the process) and
verify the store shows either the pre-operation state or the fully-completed
post-operation state, never a partial mix; a subsequent writer proceeds normally.

### Verification for User Story 1

- [X] T003 [US1] Characterize in-process rollback (FR-007, acceptance scenarios 1–2): verify existing rollback-on-failure coverage in `test_flow.py` asserts that an exception raised inside a `_tx()` operation leaves the store exactly at the pre-operation state (compare full task rows and baton entries before/after), and that a normally-completed operation applies as a single unit; add or extend a characterization test in `test_flow.py` if any of these assertions is missing
- [X] T004 [US1] Crash-injection test (SC-001, spec edge case 1, research Decision 5): add a test in `test_flow.py` that spawns a child Python process which opens the store via `flow.connect()`, executes `BEGIN IMMEDIATE` plus at least one write to a task row and a baton entry, signals readiness to the parent (deterministic barrier in the test harness — no changes to `flow.py`), then blocks; the test SIGKILLs the child, reopens the store, asserts the exact pre-operation state (no partial writes), and asserts a subsequent writer commits normally (no leftover lock)

**Checkpoint**: Crash atomicity (the foundational reliability guarantee) is verified end to
end — MVP complete

---

## Phase 4: User Story 2 - Reading context from a single derived view (Priority: P2)

**Goal**: Prove the projection is a complete, derived, read-only surface: it preserves all
FR-004 elements, offers no write path (FR-005), is fully re-derivable (FR-002), and is
written only after commit (FR-010).

**Independent Test**: Perform a store-changing CLI operation, then read only the
regenerated markdown projection and confirm it reflects the change with all required
elements present; confirm no mechanism persists changes made through the projection.

### Verification for User Story 2

- [X] T005 [US2] FR-004 projection completeness test (research Decision 6b): add a test in `test_flow.py` that builds one task exercising every required element class — claim (assignee), escalate + reply (reply context and per-escalation stable ID), split (parent/child task references), note/decide baton entries, done with outcome — regenerates the projection via `flow.project()`, and asserts the markdown at `.flow/batons/<id>.md` preserves stable IDs, task references, baton/context state (state, assignee, label, outcome, entries in order), reply context (question and answer), and links to relevant reports/logs, per `specs/025-store-transaction-foundation/contracts/projection.md` § Required preserved elements
- [X] T006 [US2] Characterize no-write-path and re-derivability (FR-002/FR-005, acceptance scenario 2, spec edge case 2): verify `test_context_survives_markdown_deletion` and `test_hld008_verify_invariant` in `test_flow.py` cover deletion-survivability and non-authoritative staleness; extend `test_flow.py` with an assertion that a hand-edited projection file at `.flow/batons/<id>.md` is ignored by the system and overwritten by the next regeneration
- [X] T007 [US2] Post-commit-only ordering test (FR-010): add a test in `test_flow.py` asserting that a failed (rolled-back) operation leaves the projection file untouched at its prior committed content, and that a successful operation regenerates the projection only after commit, per `specs/025-store-transaction-foundation/contracts/projection.md` § Write rules

**Checkpoint**: The derived-view read contract is verified independently of US1 and US3

---

## Phase 5: User Story 3 - Safe concurrent task claiming (Priority: P3)

**Goal**: Prove the atomic claim protocol (FR-008) and bounded-wait contention (FR-009):
exactly one of two concurrent claimers succeeds, and a writer blocked past busy_timeout
fails cleanly with no partial write (spec edge case 3).

**Independent Test**: Issue two concurrent claim operations against one runnable task —
exactly one records claimed-by; the other observes it already claimed or waits. A writer
whose wait exceeds the busy timeout fails cleanly.

### Verification for User Story 3

- [X] T008 [US3] Characterize the atomic claim protocol (FR-008, SC-003, acceptance scenario 1): verify `test_concurrent_next_claims_each_task_once` and `test_claim_recorded_on_baton` in `test_flow.py` together assert single-winner claiming and the claimed-by baton record; extend `test_flow.py` with an all-or-nothing pairing assertion — after a failed (rolled-back) claim attempt, neither the assignee/state change nor the claimed-by baton entry is present; they appear together or not at all (same-transaction property of the claim protocol in `specs/025-store-transaction-foundation/contracts/store-transaction.md` § Atomic claim protocol)
- [X] T009 [US3] Busy-timeout clean-failure test (spec edge case 3, acceptance scenario 2, research Decision 6a): add a test in `test_flow.py` that holds `BEGIN IMMEDIATE` on one connection while a second connection — with a short per-connection `PRAGMA busy_timeout` set inside the test for speed — attempts a write; assert the second writer fails cleanly (`sqlite3.OperationalError`, no partial write visible after failure) and that the same writer succeeds once the first connection releases the lock, per `specs/025-store-transaction-foundation/contracts/store-transaction.md` § Error behavior

**Checkpoint**: All three user stories independently verified

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Close the traceability loop and align feature docs with the delivered
verification.

- [X] T010 [P] Update `specs/025-store-transaction-foundation/quickstart.md` § 6 to move the crash-injection, busy-timeout clean-failure, and FR-004 completeness tests from "planned additions" to existing coverage, with the final test count
- [X] T011 [P] Traceability sweep (SC-004): confirm each of FR-001–FR-010 maps to at least one test in `test_flow.py` or a stated property in `specs/025-store-transaction-foundation/contracts/store-transaction.md` / `specs/025-store-transaction-foundation/contracts/projection.md`, and that each maps to HLD-003 or HLD-013; including an explicit FR-006 mechanical check: scan `core.md` and `flow.py` for named AI-implementation/model/vendor references (expect zero matches), confirming the loop depends only on the CLI and markdown/text interfaces; add any missing test to `test_flow.py` before closing this task
- [X] T012 Full validation: run `python3 -m pytest test_flow.py -q` from the repository root (all tests green, zero regressions against the T001 baseline) and walk `specs/025-store-transaction-foundation/quickstart.md` scenarios 1–6 end to end

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on T001 — BLOCKS all user stories
- **User Stories (Phases 3–5)**: All depend on Phase 2 completion
  - No hard dependency between stories: US1 (crash atomicity), US2 (projection contract), and US3 (concurrent claiming) verify disjoint guarantees and are independently testable (per spec.md Independent Test criteria)
  - Recommended order is priority order: US1 (P1) → US2 (P2) → US3 (P3)
- **Polish (Phase 6)**: T010 and T011 depend on all story phases; T012 depends on T010 and T011

### User Story Dependencies

- **US1 (P1)**: Starts after Phase 2 — no dependency on other stories
- **US2 (P2)**: Starts after Phase 2 — independent of US1/US3
- **US3 (P3)**: Starts after Phase 2 — spec notes it conceptually builds on US1's atomicity, but its tests (claim uniqueness, busy-timeout) run independently

### Within Each User Story

- Characterization of existing coverage precedes new test additions (T003 before T004; T008 before T009) — brownfield rule
- Each story phase is a complete, independently runnable verification increment

### Parallel Opportunities

Limited by design: T002–T009 all modify the single `test_flow.py`, so they are sequential
for a single implementer and require file-level coordination if split across implementers
([P] requires different files). Genuinely parallel:

- T010 (`specs/025-store-transaction-foundation/quickstart.md`) and T011 (audit; touches `test_flow.py` only if a gap is found) can run alongside each other after Phase 5

---

## Parallel Example: Polish Phase

```bash
# After Phase 5 completes, launch together:
Task: "Update specs/025-store-transaction-foundation/quickstart.md § 6 coverage list"   # T010
Task: "Traceability sweep FR-001..FR-010 against test_flow.py and contracts/"            # T011

# Then finish with:
Task: "Full validation: pytest test_flow.py + quickstart scenarios 1-6"                  # T012
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001 — green baseline)
2. Complete Phase 2: Foundational (T002 — connection contract ratified)
3. Complete Phase 3: User Story 1 (T003–T004 — crash atomicity verified)
4. **STOP and VALIDATE**: Run `python3 -m pytest test_flow.py -q`; the foundational reliability guarantee (SC-001) is now proven
5. This is the MVP: every downstream feature's trust in the store rests on US1

### Incremental Delivery

1. Setup + Foundational → baseline pinned, FR-009 ratified
2. Add US1 → crash atomicity proven (MVP)
3. Add US2 → projection read contract proven (SC-002)
4. Add US3 → concurrency safety proven (SC-003)
5. Polish → docs aligned, traceability closed (SC-004)

Each increment adds verified guarantees without modifying the runtime — `flow.py` is not
changed by any task in this feature.

---

## Notes

- This feature ratifies and verifies; it does not rebuild. No task modifies `flow.py`, adds modules, or adds dependencies (plan.md Summary)
- Task counts: Setup 1, Foundational 1, US1 2, US2 3, US3 2, Polish 3 — 12 total
- [P] tasks = different files, no dependencies; most tasks share `test_flow.py` and are therefore sequential
- Stop at any checkpoint to validate the story increment independently
