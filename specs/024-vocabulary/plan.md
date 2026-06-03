# Implementation Plan: Vocabulary (HLD-002)

**Branch**: `024-vocabulary` | **Date**: 2026-06-03 | **Spec**: [spec.md](spec.md)

**Input**: `specs/024-vocabulary/spec.md` — HLD-002, reference, LOW risk

---

## Summary

Reference spec for the five HLD-002 vocabulary terms. No behavior is introduced.
One new test needed: SC-001 (confirm vocabulary terms appear in `core.md`).
Baseline at implementation time will be 58 tests (57 G03 + 1 from spec 010).

---

## Technical Context

**Language/Version**: Python 3.x
**Primary Dependencies**: pytest, `core.md` (brownfield reference)
**Testing**: All new tests in `test_flow.py`; baseline 58 green tests (after spec 010)
**Constraints**: SC-002 regression, Principle IV TDD, no source/schema changes

---

## Constitution Check

| Principle | Assessment |
|---|---|
| I — HLD is SoT | HLD-002 governs; spec aligns. ✓ |
| II — SQLite is SoT | No schema changes; reference spec only. ✓ |
| III — AI-Agnostic | No AI names; vocabulary terms are system-agnostic. ✓ |
| IV — TDD + Ratchet | New test confirmed RED first. NON-NEGOTIABLE. |
| V — Build order + simplicity | 001 → 009 → 004 → 005 → 006 → 007 → 008 → 010 → **002** is correct. One new test. ✓ |

**Gate: PASS.**

---

## SC Coverage Map

| SC | Requirement | Existing coverage | Gap |
|---|---|---|---|
| SC-001 | All five HLD-002 vocabulary terms appear in `core.md` | No test checks vocabulary in core.md | Need `test_hld002_vocabulary_in_core_md` |
| SC-002 | All 58 prior tests remain green | Baseline confirmed after spec 010 | No gap |

---

## Implementation Slices

### Slice A — Baseline

**Gate**: `pytest test_flow.py` exits 0 with exactly 58 passed.

### Slice B — SC-001: Vocabulary terms in core.md

**Test name**: `test_hld002_vocabulary_in_core_md`

**Mechanism**: Read `core.md`; assert each of the five vocabulary term names is present:
"Runner", "Task", "Baton", "Handoff", "Decision". This is the minimum guard against
vocabulary drift.

---

## Agent Context

<!-- SPECKIT START -->
Active feature plan: `specs/024-vocabulary/plan.md` (G04 — bundle complete, 59 tests)
<!-- SPECKIT END -->
