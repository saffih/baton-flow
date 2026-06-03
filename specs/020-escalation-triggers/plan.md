# Implementation Plan: Escalation Triggers (Runner → Human) (HLD-006)

**Branch**: `020-escalation-triggers` | **Date**: 2026-06-03 | **Spec**: [spec.md](spec.md)

**Input**: `specs/020-escalation-triggers/spec.md` — HLD-006, processing, MEDIUM risk

---

## Summary

Characterization spec for the four escalation triggers. `flow.py` and `core.md` already
implement and document the triggers. SC-003 is covered by an existing test.
Two new tests needed: SC-001 (question on baton) and SC-002 (four triggers in core.md).

---

## Technical Context

**Language/Version**: Python 3.x  
**Primary Dependencies**: pytest, `flow.py`, `core.md` (brownfield)  
**Testing**: All new tests in `test_flow.py`; baseline 53 green tests (after specs 004+005)  
**Constraints**: SC-004 regression, Principle IV TDD, no source/schema changes

---

## Constitution Check

| Principle | Assessment |
|---|---|
| I — HLD is SoT | HLD-006 governs; spec aligns. ✓ |
| II — SQLite is SoT | No schema changes. ✓ |
| III — AI-Agnostic | No AI names; trigger judgments are runner's own. ✓ |
| IV — TDD + Ratchet | New tests confirmed RED first. NON-NEGOTIABLE. |
| V — Build order + simplicity | 001 → 009 → 004 → 005 → **006** is correct. Two new tests. ✓ |

**Gate: PASS.**

---

## SC Coverage Map

| SC | Requirement | Existing coverage | Gap |
|---|---|---|---|
| SC-001 | Escalate records question on baton AND transitions to blocked | test_escalate_blocks (→blocked only); question-on-baton not asserted | Need `test_escalation_question_on_baton` |
| SC-002 | Four triggers documented in core.md | No test asserts trigger names in core.md | Need `test_escalation_triggers_in_core_md` |
| SC-003 | Escalating a done task is rejected | test_cannot_escalate_done_task | COVERED |
| SC-004 | All 52 prior tests remain green | Baseline confirmed | No gap |

---

## Implementation Slices

### Slice A — Baseline

**Gate**: `pytest test_flow.py` exits 0 with exactly 52 passed.

### Slice B — SC-001: escalation question on baton

**Test name**: `test_escalation_question_on_baton`

**Mechanism**: Add task; escalate with a question; call `flow.context`; assert an entry
with `kind=="escalation"` and the question text exists on the baton.

### Slice C — SC-002: four triggers in core.md

**Test name**: `test_escalation_triggers_in_core_md`

**Mechanism**: Read `core.md`; assert each trigger name is present as a substring:
"Ambiguity", "Authority", "Irreversibility", "Repeated failure".

---

## Agent Context

<!-- SPECKIT START -->
Active feature plan: `specs/020-escalation-triggers/plan.md` (G03 — spec 006, plan phase complete)
<!-- SPECKIT END -->
