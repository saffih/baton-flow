---
description: "Task list for What It Is (HLD-001) — README.md + core.md documentation spec"
---

# Tasks: What It Is (HLD-001)

**Branch**: `016-what-it-is`
**Input**: `specs/016-what-it-is/plan.md`, `spec.md`, `research.md`, `data-model.md`
**Baseline**: 45 tests green in `test_flow.py`; all tasks must keep the suite green

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to

---

## Phase 1: Setup

**Purpose**: No new project structure needed — brownfield doc spec against existing files.
This phase is a no-op; real work begins in Phase 2.

- [ ] T001 Verify baseline: run `pytest test_flow.py` and confirm 45 tests pass

---

## Phase 2: Foundational — Fix AI-Agnostic Violation (Slice A gate)

**Purpose**: README.md currently names specific AI systems, violating Principle III
and FR-008. This BLOCKS all other work — the constitution gate must be green first.

**⚠️ CRITICAL**: No user story work begins until T002–T004 are complete and green.

**Goal**: `README.md` contains no named AI systems; test guards it from regression.

**Independent Test**: `pytest test_flow.py -k "agnostic"` passes on both `core.md`
and `README.md`.

> **TDD**: Write T002 (test) first and confirm it fails. Then fix (T003). Then verify (T004).

- [ ] T002 In `test_flow.py`, add `test_ai_agnostic_readme`: assert `README.md` contains none of `["Claude", "Devin", "Codex", "GPT", "Gemini"]` — confirm test is RED before proceeding
- [ ] T003 In `README.md`, replace `"an AI session — Claude now, Devin/Codex later — or you"` with `"an AI session, or you"` — make T002 green
- [ ] T004 Run `pytest test_flow.py` — all 46 tests (45 prior + T002) must pass; no regressions

**Checkpoint**: Constitution Principle III gate is green. User story work can begin.

---

## Phase 3: User Story 1 — New User Understands What Baton Flow Is (P1)

**Goal**: README.md explicitly names the three pains and how the baton addresses each
(FR-002). A reader answers SC-001 without opening any other file.

**Independent Test**: After T005–T007, a human reading only `README.md` can answer:
(1) What is a baton? (2) What three pains does it solve? (3) Who is the runner?

- [ ] T005 [US1] In `README.md`, add an explicit three-pains paragraph after the opening
  description, lifted verbatim from HLD-001:
  - "Context loss between AI sessions on multi-step work."
  - "No visibility into what the AI is doing while it works."
  - "No way to steer without starting over."
  Add a closing sentence: "The baton solves all three: it is the durable context,
  readable at any moment, and you steer by replying to it."
- [ ] T006 [P] [US1] Run `pytest test_flow.py` — all 46 tests still pass
- [ ] T007 [US1] Manual spot-check: re-read the README opening and confirm the three
  pains are present and match SC-001 criteria

**Checkpoint**: US1 satisfied — new user onboarding complete.

---

## Phase 4: User Story 2 — Runner Knows How to Interact (P2)

**Goal**: `core.md` states the binary reply rule as a named invariant in one sentence
(FR-005), matching the HLD-007 VERIFY line verbatim.

**Independent Test**: After T008–T010, a runner given only `core.md` can state the
routing rule without inference.

> **TDD**: T008 adds the assertion; confirm it fails on the current core.md before T009.

- [ ] T008 [US2] In `test_flow.py`, add `test_binary_reply_rule_in_core_md`: assert
  `core.md` contains the string `"about this task"` AND `"new task"` in the same
  paragraph — confirm RED before proceeding
- [ ] T009 [US2] In `core.md`, in the "On a woken task" section, add one sentence
  before the bullet list: "A reply **about this task** appends to the baton and
  unblocks it; a reply about anything else becomes a new task — the original stays
  blocked." — make T008 green
- [ ] T010 [US2] Run `pytest test_flow.py` — all 47 tests (46 + T008) pass

**Checkpoint**: US2 satisfied — runner contract fully explicit.

---

## Phase 5: User Story 3 — Contributor Understands Scope and Limits (P3)

**Goal**: `README.md` states the stripped-scope boundaries from HLD-011 (FR-007).
A contributor knows what is deliberately excluded before proposing a change.

**Independent Test**: After T011–T013, `README.md` names at least the HLD-011
stripped-scope categories (sockets, web UI, health daemons, migration tooling).

- [ ] T011 [US3] In `README.md`, add a "What it is not" section (brief) citing the
  HLD-011 stripped-scope list: no Unix-socket delivery, no web UI / HTTP API, no
  health daemons, no connection pools, no migration tooling — deliberately excluded.
  One sentence of rationale: "These were removed to keep the loop lean; adding them
  requires an HLD amendment."
- [ ] T012 [P] [US3] Run `pytest test_flow.py` — all 47 tests still pass
- [ ] T013 [US3] Manual spot-check: re-read README and confirm stripped-scope note is
  present and matches SC-001 contributor test

**Checkpoint**: US3 satisfied — scope boundaries documented.

---

## Phase 6: Polish & Verification

**Purpose**: Final suite pass, cross-check all SCs, confirm no regressions.

- [ ] T014 [P] Run `pytest test_flow.py -v` — all 47 tests pass, output clean
- [ ] T015 [P] Run `python3 -m py_compile flow.py` — no syntax errors (sanity check)
- [ ] T016 Verify SC-004: `pytest test_flow.py -k "agnostic"` — both core.md and
  README.md pass the AI-agnostic assertion
- [ ] T017 Review final `README.md` against all 8 FRs — mark each ✅ or ❌; no ❌
  allowed before closing the feature

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 — BLOCKS all user stories
- **Phase 3 (US1)**: Depends on Phase 2 completion
- **Phase 4 (US2)**: Depends on Phase 2 completion (can run in parallel with US1)
- **Phase 5 (US3)**: Depends on Phase 2 completion (can run in parallel with US1/US2)
- **Phase 6 (Polish)**: Depends on all desired user stories complete

### Within Each Phase

- Test task must be written and confirmed RED before the fix task
- Run full pytest after each fix to confirm no regressions
- Commit after each phase checkpoint (auto-commit hook fires)

### Parallel Opportunities

US1, US2, US3 all depend only on Phase 2 (foundational gate) — they can proceed in
parallel once T002–T004 are done. T006, T012, T014, T015 are marked [P] for the same
reason (different files, independent assertions).

---

## Implementation Strategy

### MVP (US1 only — new user onboarding)

1. T001 — baseline
2. T002–T004 — Principle III gate (required)
3. T005–T007 — three-pains paragraph
4. T014–T016 — verify
5. **STOP and validate**: README.md answers onboarding questions

### Full delivery

Add US2 (T008–T010) → US3 (T011–T013) → Polish (T014–T017).

---

## Notes

- Test-First is NON-NEGOTIABLE (Principle IV): T002 and T008 must be confirmed RED
  before their paired fix tasks.
- Total tasks: 17
- New tests introduced: 2 (T002 → `test_ai_agnostic_readme`; T008 → `test_binary_reply_rule_in_core_md`)
- Final test count: 47 (45 baseline + 2 new)
- No code changes — documentation + test guards only
