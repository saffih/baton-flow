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

1. **Two independent contamination sources (my first diagnosis was only half right).**
   The `Brain-to-Flow`/`Task Delivery`/`Reply Handling`/`CLI Protocol` strings —
   operational machinery HLD-011 says was "deliberately stripped" — come from BOTH:

   a. **Stale, non-hermetic workspace.** A re-run regenerated *some* artifacts but left
      *others* stale, because `project_continue.sh` step 4 only rebuilds when
      `spec_build_plan_review.md` is absent — a changed source HLD reused the old plan.
      **FIXED** (HLDspec `6fc57e8`): a source-fingerprint gate now refuses a stale or
      unverifiable built workspace (exit 3) and `HLDSPEC_FRESH=1` does a guarded clean
      rebuild. Verified: the contaminated workspace is refused; a fresh rebuild drops
      these from 23 files to 9.

   b. **Generated fresh by `build_hld_answer_dossier.py` (separate, still open).** The
      residual 9 are NOT stale — the dossier builder hardcodes `CONTRACT_NAME_RULES`
      mapping `core.md`→"Brain-to-Flow CLI Contract" (our HLD cites core.md everywhere)
      and `socket`→"Task Delivery Handshake Contract", which matches HLD-011's
      *out-of-scope* line "Unix-socket task delivery… excluded on purpose" — i.e. it
      **reads the exclusion list as a feature request**. This is project-specific
      vocabulary + keyword-matching-meaning baked into a general tool (the same disease
      as the resolve-before-escalate fix). Deferred on purpose: it is the blind-redo
      experiment's own pre-registered failure signal — fix it *after*, with the
      experiment as evidence.
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
