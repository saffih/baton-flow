# HLDspec Architecture Questions — Answer Dossier (ARQ-001..010, QG-014)

Resolved from the HLD itself where the HLD already answers; escalated only where a
genuine human/product decision remains. Each answer cites its governing HLD section.

## Governing answer for ARQ-001..009 (source-of-truth ownership + update timing)

All nine are the same templated question fired per section because the map "detected
state/source-of-truth/data terms." The HLD answers it **uniformly and definitively**:

- **Source of truth / ownership** — **SQLite is the single source of truth; all state lives
  in the DB. Markdown is a one-way projection for human reading, never an input.** (HLD-003
  VERIFY, verbatim.) The DB is mutated **only** through the `flow` CLI verbs — "no direct
  database access, ever" (HLD-009). Every actor is a recognized named session (HLD-009/010).
- **Update timing** — **every CLI operation is one all-or-nothing transaction** (`BEGIN
  IMMEDIATE`); the markdown projection is written **after** commit and is re-derivable, never
  part of a transaction. (HLD-013.)

Per section (each conforms to the above; no per-section divergence):

| ARQ | Section | SoT owner | Notes |
|---|---|---|---|
| 001 | Core model (HLD-003) | SQLite DB | This *is* the SoT rule; markdown one-way. |
| 002 | Task lifecycle (HLD-004) | `tasks` table (state col) | transitions transactional via verbs; dependency-guarded. |
| 003 | answer/feedback (HLD-007) | escalations + baton_entries | `answer` resolves the one open escalation + wakes in one tx; `feedback` creates a referenced task; source untouched. |
| 004 | Baton (HLD-008) | `baton_entries` | declared context only; markdown batons one-way. |
| 005 | CLI contract (HLD-009) | DB via verbs only | verbs are the only mutators; every call names a session. |
| 006 | Technology (HLD-012) | SQLite (WAL) | Python + SQLite SoT + markdown one-way. |
| 007 | Concurrency/durability (HLD-013) | DB | atomic claim (lock before read), 1 tx/op, WAL+busy_timeout+synchronous=NORMAL, projection post-commit. This *is* the answer. |
| 008 | Autonomy contract (HLD-015) | **N/A — no data object** | a governance principle over guard behavior; the heuristic mis-flagged "invariant/state" wording. No SoT/timing to confirm. |
| 009 | Output layer (HLD-016) | SQLite (reports + outcomes) | reports DB-owned + markdown-projected like the baton; outcome bound to its task; report transcendent w/ own lifecycle (active→deprecated{superseded\|obsolete}), deprecated=immutable, references deprecation-aware; supersession = new report + mark old deprecated, transactionally. |

**Disposition ARQ-001..009: RESOLVED from the HLD. No human decision required** — these are
heuristic over-escalations the HLD pre-answers (the known HLDspec resolve-before-escalate
pattern).

## ARQ-010 — Constitution update plan — GENUINE HUMAN GATE

The plan's four architecture rules are sound, standard, and consistent with the HLD:
ARCH-001 (HLD is architecture SoT), ARCH-002 (API-contract / processing separation),
ARCH-003 (common foundation before dependents), ARCH-004 (SpecKit ownership boundary).

**Recommendation: APPROVE_PLAN.** One thing to verify before approving: that the full
constitution still carries the engineering "every product fully tested" axiom (wired by the
toolbox→constitution augmenter, separate from these architecture rules). If it's absent,
the right answer is MODIFY_PLAN to include it. The architecture rules themselves are good.

**Disposition: HUMAN APPROVAL — recommended APPROVE_PLAN (verify the testing axiom present).**

## QG-014 — Answer Dossier (prework ACTION)

Finding: "HLD Answer Dossier is present but has action findings; the judge should review the
action findings before approval." This dossier + the RunSkeptic below **is** that review.
The only residual action is ARQ-010 (constitution approval), which is correctly a gate, not
a defect. **Disposition: reviewed; no blocker.**
