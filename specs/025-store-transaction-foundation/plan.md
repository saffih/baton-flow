# Implementation Plan: Store & Transaction Foundation

**Branch**: `025-store-transaction-foundation` | **Date**: 2026-07-05 | **Spec**: `specs/025-store-transaction-foundation/spec.md`

**Input**: Feature specification from `/specs/025-store-transaction-foundation/spec.md`

## Summary

One durable state store is the single source of truth for all system state; markdown
projections are derived, re-derivable views that are never part of a transaction; every
CLI operation executes as one all-or-nothing transaction (write lock taken up front for
the claim path) so a crash at any point leaves no partial state.

This is a **brownfield foundation feature**: the runtime (`flow.py`) already implements
the store, the per-operation transaction wrapper, the atomic claim, and post-commit
projection rendering. The plan therefore (a) ratifies that design against FR-001–FR-010
with explicit contracts and a data model, and (b) closes the verification gaps — crash
injection (SC-001), busy-timeout clean failure (edge case 3), and projection element
completeness (FR-004) — rather than rebuilding what exists. No new modules, no new
dependencies.

## Technical Context

**Language/Version**: Python 3.10+ (per HLD; stdlib only. Local plan-time runner was
Python 3.9.6 — execution environment evidence only, not the project target)

**Primary Dependencies**: None beyond the standard library (`sqlite3`, `argparse`,
`contextlib`, `pathlib`, `datetime`)

**Storage**: One durable state store (FR-001). The chosen implementation is SQLite via
stdlib `sqlite3` — see Inherited Tensions T1 for how this coexists with the
engine-agnostic contract. Store file: `.flow/flow.db`. Projections: `.flow/batons/<id>.md`.

**Testing**: pytest over `test_flow.py` (existing convention; 66 tests today, including
HLD-013 connection-hardening and concurrent-claim tests)

**Target Platform**: Local POSIX (macOS/Linux) single machine; multiple concurrent CLI
processes against one store file

**Project Type**: Single-file CLI tool (`flow.py` + `flow` wrapper) with a text contract
(`core.md`)

**Performance Goals**: Correctness under concurrency, not throughput. A competing writer
waits up to the configured busy timeout (currently 5000 ms) instead of failing
immediately; beyond it, it fails cleanly with no partial write.

**Constraints**: Crash atomicity for every CLI operation (FR-007); WAL journaling,
busy_timeout, synchronous=NORMAL on every connection (FR-009); projections written only
after commit (FR-010); no write path through projections (FR-005); loop depends only on
CLI + markdown/text (FR-006).

**Scale/Scope**: Single repository store; a handful of concurrent runner sessions.
Feature scope is exactly FR-001–FR-010 (traced to HLD-003 and HLD-013).

## Inherited Tensions

Three tensions are inherited from the HLD/spec and are handled explicitly here. They also
shape the decisions in `research.md`.

**T1 — Named pragmas vs engine-agnostic contract.** FR-009 mandates WAL journaling,
busy_timeout, and synchronous=NORMAL — SQLite-specific pragmas — while the spec's
Assumptions (spec.md ~line 97) state the storage engine is an implementation choice.
Resolution adopted by this plan: SQLite is the **chosen implementation** of the store for
this feature, and FR-009 is read as binding **on that implementation**. The **contract**
stays engine-agnostic by stating the properties those pragmas deliver: single-writer
atomic commit, concurrent readers during a write, contention handled by bounded waiting
rather than immediate failure, and a stated durability class (see T3). A replacement
engine must provide equivalent properties; the pragma names themselves are not part of
the contract. See `research.md` § Decision 1 and `contracts/store-transaction.md`
§ Durability & concurrency properties.

**T2 — Canonical read path.** The canonical read path is the CLI against the database;
the markdown projection is a derived handoff/integration surface, **never a write path**
(HLD-008). All reads that decisions depend on are architected against the CLI/store
(`flow context`, `flow list`); projections are derived-only, non-authoritative, and may
be stale or absent without any loss of state (spec edge case 2). This framing governs
the projection contract (`contracts/projection.md`) and the data model's Projection
entity: a projection is a rendering of store state, never an input to it.

**T3 — Atomicity vs durability under synchronous=NORMAL.** FR-007 requires that a crash
at any point leaves **no partial state**. Under WAL with synchronous=NORMAL, a recently
**committed** transaction can be lost on OS crash or power failure (the WAL may not yet
be synced), but atomicity is preserved: the store rolls back to a consistent
pre-transaction state — never a partial mix. FR-007 is therefore an **atomicity**
guarantee, and this plan states the durability class explicitly: process crash → no
committed work lost; power loss → at most the most recent committed transaction(s) may
be lost, with the store still consistent. This is the intended reading of FR-007 + FR-009
together, recorded in `research.md` § Decision 3 and in the contract's durability class.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

The applied constitution (`.specify/memory/constitution.md`, PROPOSAL status — honored
here as the gating input) is derived from the same HLD sections this feature traces to.
Gates relevant to this feature:

| Gate | Requirement | Status |
|---|---|---|
| CONTRACT-SINGLE-STORE | Single durable store sole source of truth; projections derived, deletable, re-derivable | PASS — FR-001/FR-002; design keeps one store, `project()` re-derives from DB |
| CONTRACT-ONE-TX-PER-VERB | Every CLI operation is one all-or-nothing transaction | PASS — FR-007; single `_tx` wrapper (BEGIN IMMEDIATE … COMMIT/ROLLBACK) per verb |
| CONTRACT-ATOMIC-CLAIM | `flow next` takes write lock before reading queue; claim + claimed-by in same transaction | PASS — FR-008; claim runs entirely inside one BEGIN IMMEDIATE |
| Core principle 2 (CLI-only writes) | Every mutation through named CLI verbs; no direct DB access | PASS — FR-005/FR-006; projections expose no write mechanism |
| DATA-BATON-OWNERSHIP | Baton DB-owned; canonical read path is the CLI; markdown derived | PASS — T2 framing above |
| DATA-PROJECTION-ROLES | Projections carry three roles and preserve stable IDs, references, context state, reply context, report/log links | PASS with verification gap — FR-003/FR-004; completeness check is a planned test (see quickstart / research Decision 6) |

No gate violations. Complexity Tracking is empty.

**Post-design re-check (after Phase 1)**: the design artifacts introduce no new write
paths, no second store, no projection-side mutation, and no transaction that spans
multiple operations. Contracts in `contracts/` restate — not weaken — the constitution
gates. Re-check: PASS.

## Project Structure

### Documentation (this feature)

```text
specs/025-store-transaction-foundation/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   ├── store-transaction.md
│   └── projection.md
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
flow.py          # Single-file runtime: connect() pragmas, _tx() wrapper, verbs, project()
flow             # CLI entry wrapper
core.md          # Runner loop contract (CLI + text only — FR-006)
test_flow.py     # pytest suite; foundation tests live here
.flow/
├── flow.db      # The durable store (single source of truth)
└── batons/      # Derived markdown projections, <id>.md (read-only surface)
```

**Structure Decision**: Keep the existing single-file layout. This feature is the
foundation layer of `flow.py` (connection settings, transaction wrapper, claim path,
projection rendering) plus its tests in `test_flow.py`. Introducing `src/` packaging for
a 580-line single-file tool would be structure without need.

## Phase 0 → Phase 1 outputs

- `research.md` — decisions resolving T1/T2/T3 and the verification approach (crash
  injection, busy-timeout behavior, projection completeness). No NEEDS CLARIFICATION
  markers remain (the spec declares none; the three tensions are resolved or explicitly
  carried as stated readings above).
- `data-model.md` — store entities (tasks, baton_entries, escalations, sessions), the
  Projection and Transaction concepts, state transitions, validation rules.
- `contracts/store-transaction.md` — per-operation transaction contract, claim protocol,
  durability & concurrency properties (engine-agnostic statement + chosen-implementation
  bindings).
- `contracts/projection.md` — projection roles, required preserved elements (FR-004),
  regeneration rules, never-a-write-path.
- `quickstart.md` — how to exercise and verify the foundation guarantees locally.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No violations — table intentionally empty.
