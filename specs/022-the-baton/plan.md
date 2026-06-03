# Implementation Plan: The Baton (Per-Task Document) (HLD-008)

**Branch**: `022-the-baton` | **Date**: 2026-06-03 | **Spec**: [spec.md](spec.md)

**Input**: `specs/022-the-baton/spec.md` — HLD-008, architecture, HIGH risk

---

## Summary

Characterization spec for the baton model. `flow.py` already implements the baton correctly.
SC-001 and SC-002 are covered by existing tests. One new test needed: SC-003 (HLD-008 VERIFY
invariant citation by ID).

---

## Technical Context

**Language/Version**: Python 3.x  
**Primary Dependencies**: pytest, `flow.py` (brownfield)  
**Testing**: All new tests in `test_flow.py`; baseline 55 green tests (after specs 004–007)  
**Constraints**: SC-004 regression, Principle IV TDD, no source/schema changes

---

## Constitution Check

| Principle | Assessment |
|---|---|
| I — HLD is SoT | HLD-008 governs; spec aligns. ✓ |
| II — SQLite is SoT | No schema changes; baton in DB confirmed. ✓ |
| III — AI-Agnostic | No AI names; baton model is session-agnostic. ✓ |
| IV — TDD + Ratchet | New test confirmed RED first. NON-NEGOTIABLE. |
| V — Build order + simplicity | 001 → 009 → 004 → 005 → 006 → 007 → **008** is correct. One new test. ✓ |

**Gate: PASS.**

---

## SC Coverage Map

| SC | Requirement | Existing coverage | Gap |
|---|---|---|---|
| SC-001 | Deleting markdown projection does not affect `flow context` (DB is SoT) | test_context_survives_markdown_deletion | COVERED |
| SC-002 | Markdown baton file created under `.flow/batons/` (projection exists) | test_projection_writes_markdown | COVERED |
| SC-003 | HLD-008 VERIFY invariant cited by ID in at least one test | No test cites "HLD-008 VERIFY" | Need `test_hld008_verify_invariant` |
| SC-004 | All 55 prior tests remain green | Baseline confirmed | No gap |

---

## Implementation Slices

### Slice A — Baseline

**Gate**: `pytest test_flow.py` exits 0 with exactly 55 passed.

### Slice B — SC-003: HLD-008 VERIFY invariant citation

**Test name**: `test_hld008_verify_invariant`

**Mechanism**: Docstring cites `"HLD-008 VERIFY"` + full invariant text. Assert:
1. Create a task with a note; delete the markdown projection; `flow.context` still returns
   the note (baton in DB, read via CLI).
2. The docstring of this test contains `"HLD-008 VERIFY"` to satisfy the ratchet.

---

## Agent Context

<!-- SPECKIT START -->
Active feature plan: `specs/022-the-baton/plan.md` (G03 — spec 008, plan phase complete)
<!-- SPECKIT END -->
