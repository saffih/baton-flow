# Feature Specification: Vocabulary (HLD-002)

**Feature Branch**: `024-vocabulary`

**Created**: 2026-06-03

**Status**: Draft

**Input**: HLD-002 — Vocabulary (reference spec; load-bearing terms used throughout the system)

## User Scenarios & Testing

### User Story 1 — Vocabulary is defined and used consistently (Priority: P1)

The five load-bearing vocabulary terms (Runner, Task, Baton, Handoff, Decision) are defined
in HLD-002 and used in `core.md`. Any future reader of the system can look up a term's
meaning and find it consistent with how it is used in the runner loop.

**Why this priority**: Vocabulary drift is a silent failure mode — a term that means one
thing in the HLD and another in the runner loop causes miscommunication across handoffs.

**Independent Test**: Verify that each of the five terms appears in `core.md` where the
runner loop governs day-to-day operation.

**Acceptance Scenarios**:

1. **Given** `core.md` is the runner's operating document, **When** each vocabulary term is searched, **Then** it is present at least once.
2. **Given** HLD-002 defines 5 terms, **When** the spec is reviewed, **Then** all 5 are covered with consistent meaning.

---

### Edge Cases

- No new terms are introduced by this spec — vocabulary is already in use.
- Deviations between HLD-002 definitions and core.md usage would indicate documentation drift (out of scope to fix here; flag only).

## Requirements

### Functional Requirements

- **FR-001**: The five vocabulary terms (Runner, Task, Baton, Handoff, Decision) MUST be defined in the spec and traceable to HLD-002.
- **FR-002**: Each term MUST appear in `core.md`, the authoritative runner loop document (HLD-RESOURCES: core.md).
- **FR-003**: The spec is reference-only; no new behavior is introduced.

## Success Criteria

### Measurable Outcomes

- **SC-001**: All five HLD-002 vocabulary terms (Runner, Task, Baton, Handoff, Decision) appear in `core.md` — need `test_hld002_vocabulary_in_core_md`.
- **SC-002**: All 58 prior tests remain green (after spec 010 adds one test).

## Assumptions

- HLD-002 is a reference spec (HLD-ROLE: reference, HLD-RISK: LOW, no HLD-VERIFY field).
- No new behavior is added; this spec documents vocabulary already in use.
- Baseline at time of this spec's implementation will be 58 tests (57 G03 baseline + 1 from spec 010).
- The single new test confirms vocabulary terms are present in `core.md` to prevent documentation drift.
