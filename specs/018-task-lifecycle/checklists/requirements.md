# Specification Quality Checklist: The Task Lifecycle (HLD-004)

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-06-03
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified (blocked→done rejected, reopen on non-done rejected, no fifth state)
- [x] Scope is clearly bounded (four-state lifecycle, waking semantics, reopen; excludes routing/sessions)
- [x] Dependencies and assumptions identified (brownfield flow.py, HLD-010/014 treated as built)

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows (full lifecycle, blocked-done guard, reopen, auto-wake)
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Brownfield Verification

- [x] Four states confirmed in flow.py: `STATES = ("pending", "in_progress", "blocked", "done")` with DB CHECK constraint (line 44)
- [x] `done` rejected with unfinished children: `_is_blocked()` checks open escalations + non-done children; `done()` raises FlowError if blocked (lines 161–171, 365–368)
- [x] `done` is reopenable: `reopen()` asserts state==done then sets state=pending (lines 403–408)
- [x] Auto-wake: `_maybe_wake()` called in `done()` and `reply()` transitions; wakes blocked task to pending when `_is_blocked()` is False (lines 224–229)
- [x] No undocumented states found in referenced files
