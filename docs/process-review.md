# Baton Flow — Process Review (2026-05-29)

How attempt #3 is being built, what the end-to-end process actually is, where it
worked, and how to improve it. Written so the hard-won method survives handoff.

## The process, end to end

1. **Lean HLD** (`HLD.md`) — the design distilled from a 313 KB Devin-specific doc to
   ~190 lines, AI-agnostic, single source of truth.
2. **Anchor** the HLD to HLDspec format (`## HLD-NNN` + `HLD-*` metadata). 12 sections;
   5 HIGH-risk sections carry `HLD-VERIFY` invariant lines (the scar tissue from attempts
   #1/#2 where a data-model change cascaded through working code).
3. **HLDspec Journey 2 read-only cycle** (`first_run_readonly.sh`): format report →
   HLD map → Spec Build Plan → Plan Quality Gate → RunSkeptic review. Output: a
   skeptic-clean plan (9 candidate specs, 0 flagged, 0 conflicts) + a proposed
   constitution + a bottom-up dependency order.
4. **SpecKit** (`specify init --here --integration claude`) — scaffolds `.specify/` +
   the `/speckit-*` commands. Constitution ratified at `.specify/memory/constitution.md`
   v1.0.0, binding the HLD invariants as enforceable principles (Test-First +
   Regression-Ratchet is NON-NEGOTIABLE).
5. **Build = harden the existing runtime under a regression net**, not regenerate. The
   ~350-line `flow.py` already implemented the HLD with 18 passing tests; the work is to
   bring every `HLD-VERIFY` invariant under a failing-if-violated test, then extend behind
   stable seams (the data model + the CLI contract).

## Gates (must stay green to advance a slice)

| Gate | Command | Status |
|---|---|---|
| HLD valid | `hld_map.parse_hld_file(HLD.md).validation_errors == []` | ✓ `[]` |
| Plan clean | `review_spec_build_plan.py --strict` | ✓ exit 0 |
| Tests | `pytest test_flow.py` | ✓ 24 passed |

## The regression net (HLD-VERIFY → test)

The deliverable three prior attempts never built. Each HIGH-risk invariant now maps to a
test or is recorded as structural:

| Invariant (HLD) | Coverage |
|---|---|
| HLD-004 only four states | `test_only_four_states` + DB `CHECK` constraint + `test_state_column_rejects_unknown_state` |
| HLD-004 no `done` with unfinished children | `test_parent_cannot_be_done_with_open_children` |
| HLD-004 `done` is reopenable | `test_reopen_done_task` |
| HLD-004 wake only when all deps resolve | `test_parent_wakes_when_all_children_done`, `test_reply_wakes_task` |
| HLD-005 escalate parks + frees runner | `test_escalate_blocks`, `test_next_skips_blocked` |
| HLD-005 split parks + frees runner | `test_split_blocks_parent_and_creates_children`, `test_next_skips_split_blocked_parent` |
| HLD-004 no illegal `done → blocked` | `test_cannot_escalate_done_task`, `test_cannot_split_done_task` |
| HLD-003/008 SQLite is truth; markdown one-way | structural (no code path reads markdown as input); `test_projection_writes_markdown` covers the one-way write |
| HLD-003/009 agnostic contract; no direct DB | structural (loop lives in `core.md`, depends only on CLI + text; runners have no DB handle) |

### Real bugs the net caught (red → green, this session)

- **G1** `split(task, [])` parked the parent `blocked` with no children — nothing could
  ever wake it. Now rejected.
- **G3** `escalate`/`split` on a `done` task drove it to `blocked` — a transition not in
  the lifecycle. Now rejected.
- **G2** "only four states" was a documented tuple, unenforced. Now a storage-level
  `CHECK` constraint.

## What worked

- Anchoring as a pure heading+metadata pass (prose verbatim) — HLD stayed lean and the
  whole HLDspec/SpecKit pipeline lit up (0 → 12 anchors, empty → full spec plan).
- Encoding the scar-tissue invariants into the constitution **before** touching code.
- TDD on the invariants surfaced three live defects in code that "already worked."

## How to improve

1. **My own recurring failure mode (the most important fix).** Three times in one session
   I concluded "X doesn't exist" from a single negative probe — the anchor seeder, the
   raw→anchored conversion process, and the `specify` CLI — and was wrong each time
   (it was in git history, in `first_run_readonly.sh`, and on disk at `~/.local/bin`
   off the non-interactive PATH). This is the same "lose key parts" failure the project
   fights. **Rule: before concluding a capability is absent, check across PATH + installer
   manifests (`uv tool list`, `pipx`, `pip`), git history (incl. deleted/archived files),
   and docs — not one probe.**
2. **Don't force greenfield decomposition onto a working brownfield core.** HLDspec/SpecKit
   proposed 9 specs; the evidence (three small bugs in one 350-line module) says the
   foundation is **one** unit. Apply SpecKit's *discipline* (spec→plan→tasks→tests→gates)
   at the granularity the system warrants. The real artifact is the invariant→test net,
   not nine ceremonial `spec.md` files.
3. **Reconcile HLDspec's two entry points.** `agent_session --mode create` reports
   "0 anchors" and hands a generic prompt; `first_run_readonly.sh` runs the actual
   readiness-detection + marking + slice/build flow. A user entering via `agent_session`
   never sees the marking plan. (Logged in HLDspec backlog.)
4. **HLDspec marking is a keyword-heuristic draft, not final.** Its `apply` step
   double-numbers titles and defaults roles to `architecture/MEDIUM`. Good as a never-skip
   scaffold; the agent must still do the judgment pass. (Two polish items logged.)
5. **Brownfield reconciliation belongs in `/speckit-plan`**, which must name `flow.py` +
   `test_flow.py` as the existing implementation and cite characterization-first, so
   `/speckit-tasks` emits "test / close-gap" tasks rather than "build from scratch."

## Milestone reached / what remains

**Reached:** the foundation runtime is test-guarded against every `HLD-VERIFY` invariant,
three real bugs are fixed, the regression ratchet is in place, and all three gates are
green. This is the defensible end of the foundation slice.

**Remains:** wire `/speckit-plan` against the existing code for any genuinely new behavior;
commit the milestone (HLD anchor, constitution, hardened runtime) on a feature branch.

## Update — the lesson is now a process (not just a doc)

The "structural" hand-waves above were closed into real tests, and one of them caught a
live inconsistency: `core.md`, the *agnostic* loop, named "Claude, Devin, Codex" — fixed
to "any runner". Baton Flow is now **28 tests green**, every HIGH-risk anchor covered.

Most importantly, improvement #2 (the invariant→test discipline) was institutionalized in
HLDspec so it stops being something a human must remember:

- **`hldspec/scripts/hld_verify_coverage.py`** — a deterministic gate. It parses the
  anchored HLD, and requires every HIGH-risk anchor (each carries an `HLD-VERIFY`
  invariant) to be **cited by id** (e.g. `# HLD-004`) in the test corpus. `--strict`
  exits non-zero if any is uncovered; `--waive` records explicit exceptions. This converts
  HLDspec's own prose rule ("no anchor implemented without test evidence") — which had the
  exact "stated, not enforced" disease that caused our bugs — into a mechanism.
- The convention is wired into HLDspec's slice-test policy, unit-tested
  (`tests_v2/test_hld_verify_coverage.py`), and the full HLDspec suite (731) stays green.
- The slice loop now has **three gates**: `hld_map` clean → `review_spec_build_plan
  --strict` → `hld_verify_coverage --strict` → tests (this + all prior slices) green.
