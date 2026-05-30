# SpecKit Open-Questions Triage — what actually needs a human

The HLDspec prework run (`.hldspec-first-run`) is `ORCHESTRATION_BLOCKED` on **22
open questions** (8 PMQ + 14 ARQ), all stamped `ESCALATE_TO_HUMAN`,
`human_decision: TBD`. This is the triage the user asked for: how many *genuinely*
need a human, how critical they are, and which dissolve under evidence (HLD.md, the
original/engineering sections, the constitution) or under a RunSkeptic look.

## Verdict

| Bucket | Count | Needs a human? |
|---|---|---|
| Answered verbatim by HLD.md metadata/prose | 21 | **No** — heuristic false-positives |
| Constitution sign-off gate (ARQ-014) | 1 | **Technically — but it's a no-op** (see below) |

(Partition is 21 + 1 = 22. Separately, *inside* PMQ-008 hide two genuine design
forks for HLD-014 — heartbeat + fence — that the queue failed to surface as such;
that's a finding about the detector, not two more items needing action now.)

**0 of the 22, as written, require a product or architecture *decision*.** Every
design fact they ask for is already explicit in the HLD's own structured fields
(`HLD-ROLE`, `HLD-VERIFY`, `HLD-SPECS`, `HLD-RESOURCES`) or in `constitution.md`.

## The four detectors and why each fired

### 1. PMQ-001..004, 006, 007, 008 — "Resolve TBD metadata for HLD-SPECS[/RESOURCES]"  (7 Qs)
**Pure literal-token scan.** The flagged set is *exactly* the seven anchors whose
`HLD-SPECS:` field contains the string `TBD` (001, 002, 006, 007, 011, 012, 014);
the two also tagged "HLD-RESOURCES" (PMQ-006, 008) are exactly the two whose
`HLD-RESOURCES:` is also `TBD` (011, 014). The detector matched a string; it never
asked whether a spec is *needed*.

- The HIGH-risk behavioral anchors all already say `HLD-SPECS: constitution`.
- The seven flagged are `purpose / reference / processing / governance / operations`
  roles — **descriptive or runner-judgment prose with no behavioral spec to bind.**
- Correct resolution (HLD hygiene, not a decision): set their `HLD-SPECS` to `none`
  for descriptive anchors (001 purpose, 002 vocabulary, 011 out-of-scope, 012 tech),
  to `core.md` for the runner-judgment ones (006 escalation triggers, 007 human-loop
  — already documented as "partial — by design" in `anchor_implementation_status.md`),
  and leave 014 as deferred (it isn't built).

### 2. PMQ-005 — "Review explicit question text in Human-in-the-loop"  (1 Q)
**A `?` in prose.** HLD-007 contains the rhetorical heading *"Is the reply about this
task itself?"* — a decision rule, not an open question. The detector saw a question
mark and escalated it. False positive.

### 3. ARQ-001..006 — "Confirm API/interface boundary vs processing responsibility"  (6 Qs)
Fires when an anchor "mixes API/interface and processing terms." But every anchor
carries an explicit **`HLD-ROLE`** that *is* the answer: HLD-003 governance,
HLD-004/008/013 architecture, **HLD-009 api**, HLD-012 operations. And HLD-003 states
the boundary outright — the loop depends on "exactly two interfaces: a CLI and
markdown/text"; HLD-009 *is* "The CLI contract." The boundary is the most explicit
thing in the document. Answered by existing metadata.

### 4. ARQ-007..013 — "Confirm source-of-truth ownership and update timing"  (7 Qs)
The single most-repeated fact in the HLD. HLD-003 `HLD-VERIFY`: *"SQLite is the only
source of truth; markdown is a one-way projection, never an input."* HLD-013: *"the
markdown projection is written after the transaction commits."* Update timing = one
all-or-nothing transaction per CLI operation. Seven questions, one HLD sentence each.

### 5. ARQ-014 — "Approve the constitution update plan"  (1 Q) — the ONE real gate
This is a genuine human checkpoint **by design**: constitution rules (ARCH-001..004)
govern every downstream SpecKit output, so they require explicit sign-off before
`/constitution` and `/specify` run. RunSkeptic lens (KT:IR — governs-everything,
hard to walk back later): keep it human. **But it is a literal no-op.** I checked
`constitution.md`: all four proposed rules are *already ratified in it* — ARCH-001
(§I), ARCH-002 (§III), ARCH-003 (§V), ARCH-004 (§"SpecKit Ownership Boundary"). The
"update plan" proposes adding rules the constitution already contains. Expected
action: `APPROVE_PLAN`, changing nothing.

## RunSkeptic pass — does "answer from HLD" hold up?

For buckets 1–4 the answers are **OBSERVED** evidence: each is a line I can quote from
`HLD.md`. Skepticism doesn't weaken them — it confirms they're non-questions. The one
place the skeptic bites *for* keeping a human is ARQ-014 (governs all later outputs →
cheap insurance to glance). The one place it bites *against* the queue is PMQ-008:

**The real finding (PO:SI — the detector measures the wrong thing).** PMQ-008 flags
HLD-014's `TBD` metadata as the open question. But HLD-014's *actual* open questions —
the **heartbeat model** and **fence-enforcement** decisions recorded in
`label-sessions-roadmap.md` — are genuine human design calls, and the queue never
surfaced them. The detector flagged the trivial (a `TBD` string) and **missed the
substantive** (the two design forks). It over-escalates noise and under-escalates the
one thing that truly needs Saffi.

## The actual challenge (what this is really telling us)

HLDspec's question detection is **heuristic and reads structure, not meaning.** It
escalates on a literal `TBD`, a `?`, or co-occurring keywords, while its own policy
(`speckit_clarify_answer_policy.md`) defaults API-contract and source-of-truth classes
to *"ESCALATE unless explicit in the architect pack."* The architect pack was never
populated, so **everything escalated even though the HLD body is explicit** — the
resolver looked for the answer in the wrong artifact and never consulted the HLD's own
`HLD-ROLE` / `HLD-VERIFY` / `HLD-SPECS` / `HLD-RESOURCES` fields, which exist precisely
to answer these.

Two fixes make the pipeline flow:
1. **Evidence-first resolver.** Before escalating an ARQ/PMQ, read the anchor's
   structured fields and `HLD-VERIFY`; auto-answer when present (which is ~21/22 here).
   Treat `HLD-SPECS: TBD` on a descriptive/governance anchor as `none`, not a question.
2. **Surface substance, suppress noise.** A `TBD` token is not an open question; an
   unresolved *design fork* (HLD-014 heartbeat/fence) is. Invert what gets escalated.

## Bottom line for the cycle

Unblocking this run is **not** a product/architecture workshop. It's: auto-resolve 21
heuristic flags from the HLD (mechanical), `APPROVE_PLAN` on the constitution (a no-op
click), and — only if we actually scope HLD-014 — make the heartbeat + fence calls.
The blockage is a **tooling over-escalation problem, not a design-debt problem.**

### This changes the (a)/(b) fork — but only one input

Last turn I weighed (a) finish the existing whole-HLD run vs (b) abandon it and run a
clean HLD-014-scoped cycle, and leaned (b). This triage **kills the cost argument for
(a)** — unblocking is trivial, not a workshop. But the *other* reason still stands and
is now the deciding one: **the existing run is scoped at the entire HLD, so even once
cheaply unblocked it generates spec/plan/tasks for HLD-010 and HLD-013 — work already
built and tested.** So the recommendation is still (b), but for **scope, not cost**: a
fresh run scoped at HLD-014 (where SpecKit produces spec→plan→tasks *before* code) is
the dogfood that earns its keep. Keep this triage and the existing sync artifacts as a
reference; don't unblock the whole-HLD pile just to re-spec done work.

### Fix shipped (HLDspec, 2026-05-30)

The fix went in where each answer actually lives — not as a second keyword scanner
(that would reproduce the bug one layer down):

- **Prompt (`HLDSPEC_AGENT_COMMAND.md`)** — new section *"Resolve open questions from
  the HLD before escalating."* The judge must, per open question, read the cited
  anchor, apply RunSkeptic, record HLD-derived answers through the existing
  `apply_hldspec_queue_answers.py` recorder, and escalate **only** genuine forks. This
  is reading, so it generalizes to any HLD (the prose-reading cases:
  source-of-truth/update-timing, and the HLD-014 design forks).
- **Detector (`build_hld_usecase_api_map.py`)** — stopped minting three classes of
  non-question, all decidable from a *structured field* (HLD-independent): the
  rhetorical-`?` scan is removed; the `TBD`-metadata question fires only on a
  `spec_candidate AND HIGH-risk` anchor; the API/processing split is suppressed when
  `HLD-ROLE` is a single clean role.

Verified on the Flow HLD: `open_questions` 8 → **0**, every `contract_risk` → `normal`
(ARQ-001–006 gone), the 7 source-of-truth flags kept for prompt-time resolution. Full
HLDspec suite: 150 passed. Net: the queue a human ever sees collapses from 22 to the
genuine forks (and the constitution no-op).
