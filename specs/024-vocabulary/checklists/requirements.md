# Specification Quality Checklist: Vocabulary (HLD-002)

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-06-03
**Feature**: [Link to spec.md](../spec.md)

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
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

- Reference spec (HLD-ROLE: reference, HLD-RISK: LOW, no HLD-VERIFY field).
- One new test: test_hld002_vocabulary_in_core_md — checks vocabulary drift.
- No source/schema changes needed.

## Brownfield Verification

- [x] All vocabulary terms listed in spec match usage in core.md (HLD-RESOURCES)
  - Runner: "This is the loop a **runner** executes" ✓
  - Task: "Work the task", "claim the next runnable one" ✓
  - Baton: "Read the baton" ✓
  - Handoff: "After any handoff the task is `blocked`" ✓
  - Decision: "`flow decide <id> "<decision>"`", "Waking is a decision" ✓
- [x] No HLD-002 vocabulary terms are absent from core.md
