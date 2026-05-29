# Baton Flow Constitution

The anchored `HLD.md` (sections `HLD-001`..`HLD-012`) is the governing architecture.
Every principle below traces to an HLD anchor or to a hard-won lesson from two prior
attempts that failed when a data-model change cascaded through working code. These rules
exist to make that failure mode impossible.

## Core Principles

### I. HLD Is the Architecture Source of Truth (ARCH-001)

Specs, plans, and code MUST NOT contradict the facts in `HLD.md`. The HLD governs; SpecKit
consumes it. Architecture changes happen in the HLD **first** (edit the section, re-validate
`hld_map.parse_hld_file` clean), then flow forward into specs and code — never the reverse.
A spec that needs to violate an HLD invariant is a signal to amend the HLD deliberately, not
to diverge silently.

### II. SQLite Is the Single Source of Truth; Markdown Is One-Way (HLD-003, HLD-008)

A SQLite database holds all state. Markdown files are a **read-only projection** for humans
and are NEVER an input. The baton lives in the database and is read via the CLI
(`flow context`), never parsed back from markdown. Any feature that treats a markdown file
as authoritative input is rejected. This is the invariant whose violation destroyed prior
attempts.

### III. The Runner Contract Is AI-Agnostic (HLD-003, HLD-009) — and Contracts Are Separated From Processing (ARCH-002)

The execution loop (`core.md`) depends on exactly two interfaces: the `flow` CLI verbs and
text/markdown. It MUST NOT name a specific AI. Runners use **only** the published CLI verbs
— no direct database access, ever. The CLI contract (HLD-009) is a stable seam: it changes
independently of processing behavior, and processing changes MUST NOT require contract
changes. Human/ops verbs (`reply`, `reopen`) are not part of the runner loop.

### IV. Test-First and Regression-Ratchet (NON-NEGOTIABLE)

This is the rule that breaks the restart loop:

- TDD: a failing test is written and confirmed red before the implementation.
- **Every slice reruns the tests of all previously completed slices.** A green new slice
  that reds a prior slice is a failed slice.
- The data model and the CLI/markdown contract are locked behind **characterization tests**
  before they are extended. A change to the schema or a CLI verb MUST be accompanied by:
  persistence round-trip and rollback tests, contract tests, and negative-invariant tests
  (assert the forbidden state cannot occur).
- No HLD invariant (the `HLD-VERIFY` lines on HIGH-risk sections) is considered implemented
  without a test that would fail if it were violated.

### V. Common Foundation Before Dependents (ARCH-003) and Simplicity (HLD-010, HLD-011)

Shared/foundation capabilities are specified and built **before** dependent, user-facing
behavior — bottom-up, no duplicate foundations. Build order:
`001 → 009 → 004 → 005 → 006 → 007 → 008 → 010 → 002`. Simplicity is enforced: the scope
deliberately stripped in HLD-011 (sockets, connection pools, health daemons, failover,
web UI / HTTP API, environment staging, migration tooling) stays stripped. New complexity
must cite a documented reason and an HLD anchor.

## Lifecycle and Wait Invariants (HLD-004, HLD-005, HLD-007)

These are enforced as hard rules, each backed by a negative-invariant test:

- Exactly four states: `pending`, `in_progress`, `blocked`, `done`. No others.
- A task is runnable **only** when it has no unmet dependencies.
- A task CANNOT become `done` while it has unfinished children.
- `done` is reopenable (by a human or a late reply); it is a resting state, not a grave.
- `escalate` (wait on a human) and `split` (wait on children) are the **same primitive**:
  the task goes `blocked` and the runner moves on. When every dependency resolves, the task
  wakes to `pending`.
- Binary reply rule: a human reply about the task itself appends to the baton and unblocks;
  a reply about anything else becomes a new task and leaves the original blocked.

## Development Workflow and SpecKit Ownership Boundary (ARCH-004)

- HLDspec prepares SpecKit inputs (the read-only first-run cycle produces the spec build
  plan, dependency graph, and this constitution's inputs). **SpecKit** owns `spec.md`,
  `plan.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`, `tasks.md`, and
  implementation artifacts. Do not hand-fabricate those; generate them through the tool.
- Quality gates that MUST pass before advancing a slice:
  1. `hld_map.parse_hld_file(HLD.md).validation_errors == []`.
  2. `review_spec_build_plan.py --strict` exits 0 (no flagged specs, no conflicts).
  3. The slice's own tests pass AND all prior slices' tests still pass (Principle IV).
- The reproducible HLDspec workspace lives at `.hldspec-run/` (gitignored); regenerate with
  `first_run_readonly.sh "$PWD/HLD.md" "$PWD/.hldspec-run" --force`.

## Governance

This constitution supersedes other practices for Baton Flow. Because the HLD is the source
of truth (Principle I), any amendment that changes an architectural rule MUST update the
relevant `HLD.md` section in the same change and re-pass the gates above. Version bumps
follow semantic versioning: MAJOR for removing/redefining a principle, MINOR for adding a
principle or section, PATCH for clarifications. Complexity must be justified against the
stripped-scope list (Principle V). Runtime runner behavior is governed by `core.md`.

**Version**: 1.0.0 | **Ratified**: 2026-05-29 | **Last Amended**: 2026-05-29
