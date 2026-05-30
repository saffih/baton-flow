# Blind-Redo Experiment: HLD-014 spec, independent specifier vs hand baseline

**Goal (Saffi):** redo HLD-014's spec through an independent path, then compare and
learn. **Confound guarded (RunSkeptic):** a fresh-context subagent sees ONLY the HLD +
the SpecKit spec template — never `flow.py`, never the hand-authored spec — so a match
is real signal, not my own steering echoed back.

## What this measures (and what it does NOT)

- **DOES:** the quality of a spec an independent intelligence derives from the current,
  complete HLD-014 anchor, vs the hand-authored `specs/014-hand-authored-baseline/spec.md`.
- **DOES NOT:** validate HLDspec's *deterministic* prework pipeline. That path's
  contamination (the `build_hld_answer_dossier.py` hardcoded-vocabulary /
  out-of-scope-as-feature bug) is separately characterized and is NOT exercised here —
  a reasoning subagent would not reproduce a deterministic keyword-table bug.
- **Caveat on the original forks criterion:** HLD-014 is now a *complete* anchor (the
  heartbeat = quiet-reclaim and fence = optional-when-session-owned decisions are
  written into the HLD prose). So "does it independently surface the open forks" is moot
  — the HLD answers them. The live question is whether the blind spec *captures* those
  stated decisions correctly.

## Pre-registered scoring (written BEFORE seeing the subagent output)

The blind spec **fails** on any of:
1. **Missing FR** — omits a behavior HLD-014 states (lease/TTL; reclaim in_progress-only;
   blocked never reclaimed; reclaim_count; escalate-after-max; fence on
   done/escalate/split; note/decide/reply stay multi-writer; no-session path unfenced).
2. **Re-introduces stripped scope** — names a daemon/sweeper, heartbeat obligation, or
   any HLD-011 out-of-scope machinery (the Brain-to-Flow/Task-Delivery tell).
3. **Over-decomposition** — splits this one ~one-file capability into multiple specs/
   features beyond what the anchor warrants.
4. **Contradicts an HLD invariant** — e.g. fences the blackboard verbs, or breaks the
   HLD-010 "next without a session unchanged" rule.

It **passes** if a reviewer blind to the hand version would accept it as a faithful,
right-sized spec of HLD-014.

Each diff vs the baseline is then classified: **real gap** (a) vs **valid-but-different**
(b) — divergence is not automatically a defect.

## Result (2026-05-31)

A fresh-context subagent, given only `HLD.md` + the spec template (no `flow.py`, no
baseline), authored `spec.md`: **3 user stories, 17 functional requirements**, success
criteria, assumptions, and an Out-of-Scope section.

### Scored against the pre-registered criteria — PASS on all four

1. **Missing FR?** No. Every HLD-014 behavior is covered: lease/`updated_at` refreshed
   by note/decide (FR-001/002), orphan = silence past TTL no heartbeat (FR-003),
   reclaim lazy in `flow next` (FR-004), in_progress-only / blocked-never (FR-005),
   pending + baton reason + reclaim_count (FR-006/007/008), under `BEGIN IMMEDIATE`
   (FR-009), escalate-after-max (FR-010), fence done/escalate/split when session-held
   (FR-011), no-session legacy path unfenced (FR-012), blackboard never fenced (FR-013).
2. **Re-introduces stripped scope?** No — and notably it did the *opposite*: it put
   "no daemon / no background sweeper" and "no heartbeat obligation" in Out-of-Scope,
   explicitly citing HLD-011. (This is the contrast with the deterministic dossier bug,
   which mints the stripped concepts from a keyword table.)
3. **Over-decomposition?** No. One feature, three stories — identical shape to the hand
   baseline.
4. **Contradicts an HLD invariant?** No. Blackboard stays multi-writer; the HLD-010
   no-session path is preserved unchanged.

**Verdict: the blind spec PASSES.** A reviewer blind to the hand version would accept it.

### Diffs vs the hand baseline, classified

- **17 FRs vs 7 (valid-but-different).** The blind spec is finer-grained — one MUST per
  behavior — where the hand one bundled. Same coverage, same single feature; the blind
  version is arguably the more reviewable artifact. Not a gap.
- **It flagged `LEASE_TTL` and `RECLAIM_MAX` as `[NEEDS CLARIFICATION]` (REAL GAP — in
  the HLD, not the spec).** The HLD says "generous TTL" / "after K reclaims" but states
  no numbers. The independent specifier surfaced this as an open question; in my hand
  pass I *silently* picked `LEASE_TTL=3600`, `RECLAIM_MAX=3` in plan.md without flagging
  that the HLD underspecifies them. The blind path was more honest here.
- **It flagged "does reclaim clear `assignee`?" as a judgment call (REAL GAP in the
  HLD).** HLD-014 says the task returns to `pending` and the prior holder can no longer
  act (the fence), but never states `assignee` is cleared. My implementation *does* set
  `assignee=NULL`; I never recorded that the HLD leaves it implicit. The blind specifier
  caught the ambiguity I'd resolved without noting.

### What this teaches

1. **An independent reasoning pass produces a faithful, right-sized HLD-014 spec** — the
   HLD anchor is specific enough to regenerate from. Good news for the HLD's quality.
2. **The blind path beat the hand path on rigor in two places:** it surfaced two genuine
   HLD under-specifications (the two constants; the assignee-clearing) that I had
   silently closed. Lesson for my own spec work: flag what the HLD leaves open instead
   of quietly deciding it — the decision belongs in the HLD or an explicit clarification,
   not buried in plan.md/code.
3. **Reasoning-driven specification did NOT reproduce the dossier contamination.** This
   confirms the contamination is a property of the *deterministic keyword pipeline*
   (`build_hld_answer_dossier.py`), not of "deriving a spec from this HLD." It isolates
   the bug: fix the dossier, not the HLD.
4. **Two HLD-014 follow-ups fall out:** (a) add the concrete `LEASE_TTL`/`RECLAIM_MAX`
   values (or a clarification note) to the HLD; (b) state in HLD-014 that reclaim
   releases the holder (`assignee` cleared). Both are cheap and make the anchor
   self-contained.
