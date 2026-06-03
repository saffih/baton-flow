# Implementation Plan: The Wait Model (Fork-Join) (HLD-005)

**Branch**: `019-wait-model` | **Date**: 2026-06-03 | **Spec**: [spec.md](spec.md)

**Input**: `specs/019-wait-model/spec.md` — HLD-005, constitution-source, HIGH risk

---

## Summary

Characterization spec for the unified fork-join wait model (escalate == split). `flow.py`
already implements both parking primitives correctly. SC-001..004 are satisfied by existing
tests. One new test needed: SC-005 (HLD-005 VERIFY citation by ID).

---

## Technical Context

**Language/Version**: Python 3.x  
**Primary Dependencies**: pytest, `flow.py` (brownfield)  
**Testing**: All new tests added to `test_flow.py`; baseline is 52 green tests (after spec 004)  
**Constraints**: SC-006 regression, Principle IV TDD, no source/schema changes

---

## Constitution Check

| Principle | Assessment |
|---|---|
| I — HLD is SoT | HLD-005 governs; spec aligns. ✓ |
| II — SQLite is SoT | No schema changes. Tests via flow API. ✓ |
| III — AI-Agnostic | No AI names. Parking primitives are processing, not contract. ✓ |
| IV — TDD + Ratchet | New test confirmed RED first. NON-NEGOTIABLE. |
| V — Build order + simplicity | 001 → 009 → 004 → **005** is correct. One new test. ✓ |

**Gate: PASS.**

---

## SC Coverage Map

| SC | Requirement | Existing coverage | Gap |
|---|---|---|---|
| SC-001 | After escalate, runner claims next task | test_next_skips_blocked (runner calls next after escalating); test_runner_verb_contracts (escalate semantics) | COVERED |
| SC-002 | After split, parent blocked, children pending, runner claims child | test_split_blocks_parent_and_creates_children; test_runner_verb_contracts_split | COVERED |
| SC-003 | Partial completion does not wake parent | test_parent_wakes_when_all_children_done line 117 (`assert state == "blocked"` after first child done) | COVERED |
| SC-004 | Empty split rejected | test_split_empty_children_rejected | COVERED |
| SC-005 | HLD-005 VERIFY cited by ID | No test cites "HLD-005 VERIFY" as invariant text | Need `test_hld005_verify_invariant` |
| SC-006 | All 52 prior tests remain green | Baseline confirmed | No gap |

---

## Implementation Slice

### Slice A — Baseline

**Gate**: `pytest test_flow.py` exits 0 with exactly 52 passed.

### Slice B — SC-005: HLD-005 VERIFY invariant cited by ID

**Test name**: `test_hld005_verify_invariant`

**Mechanism**:
- Docstring cites "HLD-005 VERIFY" and full text: `"escalate and split both park the task as blocked and free the runner; a task is runnable only when it has no unmet dependencies"`
- Assert escalating a task transitions it to blocked
- Assert splitting a task transitions it to blocked
- Assert `flow.next_task` is callable after both operations (runner is freed)

**TDD**: confirm absent → write → GREEN → full suite green.

---

## Agent Context

<!-- SPECKIT START -->
Active feature plan: `specs/019-wait-model/plan.md` (G03 — spec 005, plan phase complete)
<!-- SPECKIT END -->
