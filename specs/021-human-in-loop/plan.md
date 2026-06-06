# Implementation Plan: Human-in-the-Loop (Human → Runner) (HLD-007)

**Branch**: `021-human-in-loop` | **Date**: 2026-06-03 | **Spec**: [spec.md](spec.md)

**Input**: `specs/021-human-in-loop/spec.md` — HLD-007, processing, MEDIUM risk

---

## Summary

Characterization spec for the human reply routing rule. `flow.py` already implements
reply append-plus-wake. The work here is to keep docs and tests aligned with the actual
dependency model: off-topic replies create a new related task on pickup; they do not
implicitly invent a new blocking dependency. SC-001 is covered by existing tests.
SC-002 and SC-003 require doc/test alignment.

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
| SC-002 | core.md states binary routing rule (continue this task vs create new related task) | Existing test assumes stale wording | Update `test_binary_reply_rule_in_core_md` |
| SC-003 | HLD-007 VERIFY invariant cited by ID in at least one test | Existing test cites stale invariant text | Update `test_hld007_verify_invariant` |
| SC-004 | All 54 prior tests remain green | Baseline confirmed | No gap |

---

## Implementation Slices

### Slice A — Baseline

**Gate**: `pytest test_flow.py` exits 0 with exactly 54 passed.

### Slice B — SC-002/SC-003: align docs/tests to actual reply-routing semantics

**Test names**:
- `test_binary_reply_rule_in_core_md`
- `test_hld007_verify_invariant`

**Mechanism**:
1. `core.md` must say the reply is already on the baton, new scope becomes a new related
   task, and the original task is handled explicitly by the runner.
2. The HLD-007 ratchet test cites the new invariant text and still proves reply
   append-plus-wake behavior.

Concretely: update the doc assertion strings; keep the runtime characterization that a
blocked task wakes and the reply is visible on the baton.

---

## Agent Context

<!-- SPECKIT START -->
Active feature plan: `specs/021-human-in-loop/plan.md` (G03 — spec 007, implementation complete)
<!-- SPECKIT END -->
