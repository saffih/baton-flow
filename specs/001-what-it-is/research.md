# Research: What it is

## Decision: Treat HLD-001 as a product-purpose foundation

**Rationale**: HLD-001 states that Baton Flow exists to produce trustworthy outputs across AI-assisted sessions and that the report is the point. This makes the first spec a governance/purpose slice that later specs must not contradict.

**Alternatives considered**:

- Define runtime behavior now. Rejected because HLD-001 does not own CLI, lifecycle, persistence, or recovery mechanics.
- Merge vocabulary into this spec. Rejected because HLD-002 is planned as a separate later feature.

## Decision: Define a purpose contract instead of code contracts

**Rationale**: G01 has no API dependency and HLD-001 is a purpose section. A lightweight product-purpose contract is enough to protect the invariant that reports are the deliverable and baton context is the means.

**Alternatives considered**:

- Create CLI or database contracts. Rejected because those belong to later HLD sections and would widen scope.

## Decision: Use reviewable checks as the verification path

**Rationale**: This phase is pre-implementation and must not touch product code. The right verification is artifact consistency: spec, plan, contract, and tasks must preserve HLD-001 and avoid unrelated behavior.

**Alternatives considered**:

- Run product tests now. Rejected because no implementation is authorized and this bundle only creates pre-implementation artifacts.
