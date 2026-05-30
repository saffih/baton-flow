# SpecKit Pipeline Run Review (pre-invocation, 2026-05-30)

Review of the HLDspec→SpecKit prework run on the Flow HLD *after* the
resolve-before-escalate fix, stopped at the legitimate `SPECKIT_PREWORK_APPROVAL_GATE`
before any paid SpecKit invocation. This is the "what went well / what didn't" the
user asked for, on the pipeline so far (no implementation yet — that is gated here).

## What went well

- **The fix works end-to-end.** The run that was `ORCHESTRATION_BLOCKED` on 22 fake
  questions now flows. The regenerated escalation queue is **8, not 22** — the 8
  TBD-metadata and 6 API/processing questions are gone (detector fix), confirming the
  deterministic half on the real workspace, not just a temp dir.
- **The prompt protocol closed the rest.** Acting as judge, the 7 remaining
  source-of-truth questions (ARQ-001..007) were resolved from the HLD with per-anchor
  citations and recorded through `apply_hldspec_queue_answers.py` — the same path a
  human answer takes. Queue went **8 → 1**. The only open item is ARQ-008, the
  constitution gate (a legitimate human sign-off, already a near no-op).
- **Plan gate is green:** plan quality PASS, KEEP_PLAN, 0 conflicts, 0 flagged specs.
- **The 11 planned specs map cleanly** to the current HLD anchors (001, 009, 004, 005,
  006, 007, 008, 010, 013, 014, 002).

## What did not go well

1. **Stale, non-hermetic workspace (the biggest issue).** A re-run regenerated *some*
   artifacts (use-case map, escalation queue) but left *others* stale (spec build plan,
   constitution update plan, answer dossier). Those carry concepts from the
   **pre-simplification** HLD — `Brain-to-Flow CLI Contract`, `Task Delivery Handshake
   Contract`, `Reply Handling Contract`, `CLI Protocol Contract` — exactly the
   operational machinery HLD-011 says was "deliberately stripped." The prework a human
   would approve is a **mix of old and new**. A re-run must fully regenerate downstream
   artifacts or version them; partial regeneration silently contaminates the gate.
2. **Descriptive sections planned as features.** The first feature is HLD-001 (purpose)
   and the plan includes HLD-002 (vocabulary). Purpose/reference prose is not a
   buildable feature; the decomposition should route these to constitution/context, not
   to `spec.md`. (Related: the use-case map *does* classify them context-only, but the
   spec build plan still lists them as specs — another old/new disagreement.)
3. **Scope re-specs built work.** HLD-010 and HLD-013 are already implemented and
   tested (34 green tests). The 11-spec whole-HLD run would generate spec→plan→tasks
   for them again — wasted motion and a drift risk against the working code.

## Recommendation

Do **not** approve the whole-HLD prework as-is — it is contaminated with stripped
pre-simplification concepts and re-specs built work. Instead: **wipe the run workspace
and do a clean, narrow run scoped at HLD-014** (orphaned-work recovery — the one
unbuilt anchor), where SpecKit produces spec→plan→tasks→implementation for genuinely
new work and the dogfood actually earns its keep. Settle HLD-014's two open forks
(heartbeat model, fence enforcement) first — those are the *real* human decisions the
queue should have surfaced (see `label-sessions-roadmap.md`).

## HLDspec follow-on (separate from Flow)

The stale-artifact finding is an HLDspec bug, not a Flow bug: the run state machine
should detect a changed source HLD and force full downstream regeneration (or refuse to
present a mixed workspace). Logged here; fix in HLDspec when addressed.

## What we did instead, and HLD-014 outcome (2026-05-30)

Decision ("your call"): rather than approve the contaminated whole-HLD prework, we
scoped to HLD-014 and built it.

**Important scope honesty — what was and wasn't "SpecKit":** the artifacts under
`specs/014-orphaned-work-recovery/` (`spec.md`, `plan.md`, `tasks.md`) were
**hand-authored in SpecKit's template format**, and the implementation was done by the
same TDD method that shipped HLD-010/013. We did **not** run the `specify` CLI, and the
HLDspec→SpecKit bundle handoff remains **unexercised** — it is still blocked behind the
workspace-hermeticity bug above and the whole-HLD scope problem. So the SpecKit *format*
was dogfooded; the SpecKit *generation pipeline* was not. Exercising it for real needs
the hermeticity fix first.

**HLD-014 shipped:** HLD promoted planned→active (HIGH) with a testable HLD-VERIFY;
lease (`updated_at`, generous TTL, no heartbeat), lazy reclaim inside `flow next` (under
the claim's `BEGIN IMMEDIATE`), escalate-after-`RECLAIM_MAX`, and an ownership fence on
`done`/`escalate`/`split` (optional `--session`/`--assignee`, fenced when session-owned).
Migration adds `reclaim_count` (and back-fills `label`) on old DBs. 45 tests green
(10 new HLD-014 + a CLI-alias guard); `core.md` updated so compliant runners pass their
identity through.

**What went well:** TDD against the HLD-VERIFY; the regression ratchet went red the
moment HLD-014 became HIGH-risk and forced its tests.
**What didn't (caught in review):** (1) the fence verbs initially accepted only
`--session` while `core.md` prescribed `--assignee` — a compliant runner would have hit
`error: unrecognized arguments` (exit 2); fixed with the dual alias + a CLI test.
(2) `_reclaim_orphans` left stale `.md` projections for tasks it touched but didn't
claim; fixed by projecting each reclaimed id after the tx.
