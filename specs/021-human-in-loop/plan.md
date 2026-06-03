# Implementation Plan: Human-in-the-Loop (Human → Runner) (HLD-007)

**Branch**: `021-human-in-loop` | **Date**: 2026-06-03 | **Spec**: [spec.md](spec.md)

**Input**: `specs/021-human-in-loop/spec.md` — HLD-007, processing, MEDIUM risk

---

## Summary

Characterization spec for the human reply routing rule. `flow.py` and `core.md` already
implement and document the reply unblocking and binary routing rule. SC-001 and SC-002 are
covered by existing tests. One new test needed: SC-003 (HLD-007 VERIFY invariant citation).

---

## Technical Context

**Language/Version**: Python 3.x  
**Primary Dependencies**: pytest, `flow.py`, `core.md` (brownfield)  
**Testing**: All new tests in `test_flow.py`; baseline 55 green tests (after specs 004+005+006)  
**Constraints**: SC-004 regression, Principle IV TDD, no source/schema changes

---

## Constitution Check

| Principle | Assessment |
|---|---|
| I — HLD is SoT | HLD-007 governs; spec aligns. ✓ |
| II — SQLite is SoT | No schema changes. ✓ |
| III — AI-Agnostic | No AI names; routing decision is runner's own. ✓ |
| IV — TDD + Ratchet | New test confirmed RED first. NON-NEGOTIABLE. |
| V — Build order + simplicity | 001 → 009 → 004 → 005 → 006 → **007** is correct. One new test. ✓ |

**Gate: PASS.**

---

## SC Coverage Map

| SC | Requirement | Existing coverage | Gap |
|---|---|---|---|
| SC-001 | flow reply appends to baton and transitions blocked→pending | test_reply_wakes_task + test_reply_recorded_on_baton | COVERED |
| SC-002 | core.md states binary routing rule (both branches; "leaves the original blocked") | test_binary_reply_rule_in_core_md | COVERED |
| SC-003 | HLD-007 VERIFY invariant cited by ID in at least one test | No test cites "HLD-007 VERIFY" | Need `test_hld007_verify_invariant` |
| SC-004 | All 54 prior tests remain green | Baseline confirmed | No gap |

---

## Implementation Slices

### Slice A — Baseline

**Gate**: `pytest test_flow.py` exits 0 with exactly 54 passed.

### Slice B — SC-003: HLD-007 VERIFY invariant citation

**Test name**: `test_hld007_verify_invariant`

**Mechanism**: Docstring cites `"HLD-007 VERIFY"` + full invariant text. Assert:
1. `flow.reply` appends to the baton and wakes a blocked task.
2. The docstring of this test contains `"HLD-007 VERIFY"` to satisfy the ratchet.

Concretely: add task, escalate it (blocked), call `flow.reply`, assert state==pending and
a reply entry appears on the baton context. The key addition is the docstring VERIFY citation.

---

## Agent Context

<!-- SPECKIT START -->
Active feature plan: `specs/021-human-in-loop/plan.md` (G03 — spec 007, plan phase complete)
<!-- SPECKIT END -->
