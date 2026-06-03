# Implementation Plan: Work Routing (Soft Affinity by Label and Named Sessions) (HLD-010)

**Branch**: `023-work-routing` | **Date**: 2026-06-03 | **Spec**: [spec.md](spec.md)

**Input**: `specs/023-work-routing/spec.md` — HLD-010, architecture, HIGH risk

---

## Summary

Characterization spec for the soft-affinity work routing model. `flow.py` already implements
sessions, bound_label, and soft affinity in `next_task`. SC-001..SC-004 are covered by
existing tests. One new test needed: SC-005 (HLD-010 VERIFY invariant citation by ID).

---

## Technical Context

**Language/Version**: Python 3.x
**Primary Dependencies**: pytest, `flow.py` (brownfield)
**Testing**: All new tests in `test_flow.py`; baseline 57 green tests (after G03 complete)
**Constraints**: SC-006 regression, Principle IV TDD, no source/schema changes

---

## Constitution Check

| Principle | Assessment |
|---|---|
| I — HLD is SoT | HLD-010 governs; spec aligns. ✓ |
| II — SQLite is SoT | No schema changes; sessions table already in DB. ✓ |
| III — AI-Agnostic | No AI names; session routing is processing-layer. ✓ |
| IV — TDD + Ratchet | New test confirmed RED first. NON-NEGOTIABLE. |
| V — Build order + simplicity | 001 → 009 → 004 → 005 → 006 → 007 → 008 → **010** is correct. One new test. ✓ |

**Gate: PASS.**

---

## SC Coverage Map

| SC | Requirement | Existing coverage | Gap |
|---|---|---|---|
| SC-001 | `flow next` with no session returns oldest runnable task unchanged | `test_next_without_session_unchanged` (line 357) | COVERED |
| SC-002 | Session binds to label of first labeled task and prefers it | `test_session_binds_then_prefers_its_label` (line 364) | COVERED |
| SC-003 | Session falls back to any runnable task when its label is dry | `test_session_falls_back_when_label_dry` (line 373) | COVERED |
| SC-004 | Children inherit parent label after split | `test_children_inherit_label` (line 129) | COVERED |
| SC-005 | HLD-010 VERIFY invariant cited by ID in at least one test | No test cites "HLD-010 VERIFY" | Need `test_hld010_verify_invariant` |
| SC-006 | All 57 prior tests remain green | Baseline confirmed | No gap |

---

## Implementation Slices

### Slice A — Baseline

**Gate**: `pytest test_flow.py` exits 0 with exactly 57 passed.

### Slice B — SC-005: HLD-010 VERIFY invariant citation

**Test name**: `test_hld010_verify_invariant`

**Mechanism**: Docstring cites `"HLD-010 VERIFY"` + full invariant text. Assert:
1. `flow.next_task(conn, assignee="r")` with no session returns oldest task (backward compat).
2. A named session claiming a labeled task then preferring its label (bind + affinity).
3. That session falls back when its label is dry.
The docstring cites the full VERIFY text by ID to satisfy the ratchet.

---

## Agent Context

<!-- SPECKIT START -->
Active feature plan: `specs/023-work-routing/plan.md` (G04 — spec 010, specify + plan complete)
<!-- SPECKIT END -->
