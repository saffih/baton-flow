# Implementation Plan: What it is

**Branch**: `001-what-it-is` | **Date**: 2026-06-08 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-what-it-is/spec.md`

## Summary

Define and preserve Baton Flow's product-purpose contract: the system exists to produce trustworthy report outputs across AI-assisted sessions, while tasks, runners, and baton context are the mechanisms that make those reports reliable, visible, and steerable.

## Technical Context

**Language/Version**: Not specified for this governance slice; implementation language is intentionally deferred to later code-changing specs.

**Primary Dependencies**: None for this specification phase.

**Storage**: Not applicable for this purpose slice; storage source-of-truth details belong to later architecture/data specs.

**Testing**: Future implementation must include tests or checks that prove product-facing surfaces preserve the HLD-001 purpose model.

**Target Platform**: Existing Baton Flow product surfaces; exact surfaces are deferred until implementation approval.

**Project Type**: Governance/product-purpose slice for a CLI-oriented AI-assisted work system.

**Performance Goals**: Not applicable; this slice defines product purpose, not runtime throughput.

**Constraints**: Must not contradict HLD-001, must not demote reports below baton mechanics, and must not define CLI, data, lifecycle, or recovery details owned by later specs.

**Scale/Scope**: One planned spec, `001`, sourced only from HLD-001.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **ARCH-001 HLD Architecture Source of Truth**: PASS. The plan traces to HLD-001 and treats HLD-001 as authoritative.
- **ARCH-002 API Contract and Processing Separation**: PASS. This plan defines no API or processing contract and explicitly defers those boundaries.
- **ARCH-003 Common Foundation Before Dependents**: PASS. G01 is first in the approved bottom-up order and has no dependencies.
- **ARCH-004 SpecKit Ownership Boundary**: PASS. Artifacts are SpecKit-phase artifacts only; implementation remains blocked.
- **ENG-001 Capability Stewardship**: PASS. Tasks will require future maintainers to preserve product-purpose wording and tests/checks where implementation touches product surfaces.
- **ENG-005/006/007 Testing Rules**: PASS for planning. Future implementation tasks require test/check coverage before product-surface changes.
- **ENG-008/009 Environment Safety**: PASS. No production or user-owned data mutation is planned.

## Project Structure

### Documentation (this feature)

```text
specs/001-what-it-is/
├── spec.md
├── checklists/
│   └── requirements.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── purpose-contract.md
└── tasks.md
```

### Source Code (repository root)

```text
README.md
docs/
specs/001-what-it-is/
```

**Structure Decision**: This feature is a governance/product-purpose slice. It plans future changes to product-facing documentation and purpose-preservation checks only after implementation approval. It does not plan changes to `flow.py`, `test_flow.py`, persistence, CLI contracts, or runtime behavior.

## Complexity Tracking

No constitution violations require justification.

## Phase 0: Research

Research is captured in [research.md](research.md). All unknowns are resolved from HLD-001 and allowed G01 evidence; no external research is required.

## Phase 1: Design and Contracts

- Data model: [data-model.md](data-model.md) records purpose-level entities only.
- Contract: [contracts/purpose-contract.md](contracts/purpose-contract.md) defines the product-purpose invariant that later artifacts must preserve.
- Quickstart: [quickstart.md](quickstart.md) defines review checks for this non-code slice.

## Post-Design Constitution Check

- PASS: The design remains bounded to HLD-001.
- PASS: Contract and data ownership stay separable from later CLI, persistence, processing, and recovery specs.
- PASS: Implementation remains blocked pending explicit approval.
