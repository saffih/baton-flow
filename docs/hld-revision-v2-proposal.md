# HLD Revision v2 — Proposal (not yet authoritative)

**Status:** PROPOSED. The reviewable draft of the next HLD. `HLD.md` stays the single
source of truth until this is approved and promoted section-by-section through the build
loop. Nothing here is implemented; current code reflects HLD v1.

**The reframing that reorders this whole document:** the system's purpose is to produce
**outputs** — *reports* — across AI sessions. Context-continuity (the baton) is the
*means*, not the end. v1 is baton-centric; v2 is **output-first**. So this draft leads
with purpose, the governing principle, and the output layer; the task/session engine
follows as the machinery beneath them.

**Terminology (v2):** the overloaded v1 `reply` is split and renamed —
- **`answer`** — answer a task's open escalation (the narrowed v1 `reply`).
- **`feedback`** — steer: comment on a report, or inject new scope. "v1 `reply`" below means the retired verb.

**Two patterns rhyme through every layer** (this is how the design stays coherent):
- **Append is the interim** — baton entries, report drafts both accrete for a while.
- **Supersede, don't resurrect** — a new referencing task over reopening a done one; a new report over mutating a stale one.
Both governed by one principle: **enforce invariants, delegate judgment** (HLD-015).

---

## Summary of changes

| Section | Change |
|---|---|
| **HLD-001** | Purpose reframed: reliable **outputs across sessions**; context-continuity is the means, not the end. |
| **HLD-015 (new)** | The autonomy contract: enforce invariants (`dependency·identity·ownership·lifecycle·existence`), delegate judgment. |
| **HLD-016 (new)** | The **output layer**: every task has a mandatory **outcome** (its bound account, any size — long ones just render as separate markdown, still outcomes); a **report** is a *distinct, transcendent* deliverable (bigger than a task, produced deliberately) with its own lifecycle. |
| **HLD-004** | `blocked` ⇒ **unassigned** (label kept). `reopen` allowed for runners but the norm is *supersede* (new referencing task), not resurrect. |
| **HLD-005** | Parking clears assignee; **one open escalation** at a time; partial answer → agent re-escalates the remainder. |
| **HLD-007** | v1 `reply` split into **`answer`** (resolve an escalation) and **`feedback`** (steer / inject). |
| **HLD-008** | The baton is repositioned as the **context substrate** (the means), not the headline. |
| **HLD-009** | Every CLI call carries a **recognized session** (enforced at entry, reads included). New verbs: `answer`, `feedback`, `reclaim`. |
| **HLD-010** | Sessions **mandatory**; the name is the bracelet; anonymous path removed. |
| **HLD-013** | Each claim records `claimed by <session>` on the baton, in-transaction. |
| **HLD-014** | Fence drops only the caller-anonymous bypass; `reclaim_count` is a **permanent** flaky-mark; **see-and-act** recovery (liveness visible + explicit `reclaim`), not a blind 1h wait. |

Small doc fixes and the full promotion/blast-radius plan are at the end.

---

# PART I — Purpose, principle, output

## HLD-001 — What it is *(revised: output-first)*

HLD-ID: HLD-001
HLD-DESC: HLD-001 is in-scope purpose at medium risk, touching none; "what Baton Flow is — producing reliable outputs across AI sessions".
HLD-ROLE: purpose
HLD-STATUS: active
HLD-RISK: MEDIUM
HLD-SPECS: TBD
HLD-RESOURCES: README.md,core.md

Baton Flow exists to **produce trustworthy outputs across AI-assisted sessions** — durable
deliverables (**reports**) that accumulate value as work proceeds, reliably and under human
steering. You create tasks; a runner (an AI session, or you) claims one, works it, and the
work's result becomes part of an output. Context survives every handoff so the output comes
out good; the human sees and steers it at any moment.

It kills three pains — but they are the floor, not the point:
1. **Context loss** between sessions on multi-step work.
2. **No visibility** into what the AI is doing.
3. **No way to steer** without starting over.

The **report** is the point: the deliverable the system is *for*. The **baton** solves the
three pains as the durable, readable, steerable context that makes good reports possible —
it is the means, not the end.

## HLD-015 — The autonomy contract: enforce invariants, delegate judgment *(new)*

HLD-ID: HLD-015
HLD-DESC: HLD-015 is in-scope governance at high risk, touching processing; "the contract enforces invariants and delegates judgment to the agent".
HLD-ROLE: governance
HLD-STATUS: active
HLD-RISK: HIGH
HLD-SPECS: constitution
HLD-RESOURCES: flow.py,core.md,test_flow.py
HLD-VERIFY: every raise FlowError in flow.py is tagged with the one invariant it protects, drawn from the closed set dependency, identity, ownership, lifecycle, existence; a raise that cannot be honestly tagged from that set is flagged for review as candidate overreach; the agent-discretion behaviors (done/escalate/split from any non-blocked state, answer-then-runner-decides, feedback-magnitude-is-judged, waking-as-a-decision) are intentional, not defects
HLD-RATIONALE: an unwritten principle the whole system leans on is itself a stated-not-enforced gap; the tagging guard makes the enforcement boundary auditable without overclaiming — it is a review-forcing tripwire (it surfaces guards that protect no invariant), not a mechanical proof that no overreach exists

*(Numbered 015 to avoid renumbering referenced sections; conceptually it sits beside the
core model, HLD-003.)*

The engine constrains only what **must** be true — the closed invariant set:

- **dependency** — a task can't be `done` with unmet dependencies (open escalation or unfinished children); a split must have ≥1 child (no stranded parent).
- **identity** — every action is taken by a named session; "no one" can't hold or move work (HLD-009/010).
- **ownership** — a task held by a named session can't be transitioned by another (HLD-014).
- **lifecycle** — the state machine is well-formed: four task states, legal transitions only (`done` can't be escalated/split; `reopen` only from `done`), one open escalation at a time, and **a `deprecated`/`obsolete` report is immutable** (HLD-016).
- **existence** — operations target a real task/report.

**Everything above that floor is the agent's call:** when to label, how big a response a
piece of feedback deserves (update / section / supersede / sweep — HLD-016), whether a
woken task is still worth doing, when to split, whether to mark stale work done. The
mechanism never pre-decides a judgment the runner should make.

**The audit test — honest about what it is.** Every `raise FlowError` in `flow.py` carries
a tag — `# INVARIANT: dependency|identity|ownership|lifecycle|existence` — naming the one
invariant it protects; a guard that can't be honestly tagged from that closed set is
**flagged for review as candidate overreach**. This is a *tripwire that forces
justification*, not a proof that no overreach exists — claiming the latter would itself be
the stated-not-enforced trap inverted. A judgment-shaped guard ("must have written N
notes") fits none of the five and trips the wire. *(The four-state set is additionally
enforced declaratively by the SQLite `CHECK(state IN …)` constraint — a `lifecycle`
invariant guarded in the schema rather than via `raise FlowError`, so it sits outside the
tagging scope by nature, not by omission.)*

## HLD-016 — The output layer: outcome and report *(new)*

HLD-ID: HLD-016
HLD-DESC: HLD-016 is in-scope architecture at high risk, touching data and processing; "the output layer — every task has an outcome (bound, any size); a report is a distinct transcendent deliverable".
HLD-ROLE: architecture
HLD-STATUS: active
HLD-RISK: HIGH
HLD-SPECS: constitution
HLD-RESOURCES: flow.py,test_flow.py
HLD-VERIFY: every task states a mandatory outcome at done — the task's bound account (what/how/why), any size, where a long outcome only changes UX (rendered as separate markdown) and is still an outcome, never a report; a report is a distinct transcendent deliverable scoped to a subject bigger than one task, produced deliberately by a report-purposed task; tasks and reports are many-to-many and a report is updated under agent judgment (in-place, add-section, supersede, or sweep); a report's lifecycle (active to deprecated, with fate superseded or obsolete) is independent of any task's lifecycle; a deprecated or obsolete report is immutable and a reference to it resolves to its live successor; every report update is attributed
HLD-RATIONALE: outcome vs report is a distinction of KIND (the task's bound account vs a transcendent subject deliverable), not size — calling a long outcome a report was a category error; the report is the system's valuable output (HLD-001), distinct from both the baton (context) and the outcome (per-task account); it is bigger than a task because value accrues across many tasks on a subject; updates span a spectrum because forcing supersession for a typo is as wrong as appending forever — the agent judges magnitude (HLD-015); deprecated-immutable + deprecation-aware references keep outputs from silently going stale

The output stack has three levels — context feeds results feed deliverables:

| Level | Scope | Nature | Update mode |
|---|---|---|---|
| **Baton** | per task | context — the journey (HLD-008) | append-log |
| **Outcome** | per task (bound) | result — the task's account (what/how/why), **mandatory**; short → inline UX, long → separate-markdown UX (**still an outcome**) | stated at `done` |
| **Report** | per **subject** (bigger than a task), **transcendent** | the **deliverable** — produced deliberately, drawing on the subject's outcomes (not a big outcome) | agent-judged spectrum |

- **Every task has an outcome** — its own account of *what it did, how, and why*. `done`
  requires it. The outcome is **bound to its task** (the task's record; it dies with the task).
- **Outcome size is a UX detail, not a kind change.** A **short** outcome renders inline; a
  **long** one renders as its own **separate markdown** (different UX) — but it is *still an
  outcome*, bound to its task. A long outcome is **not** a report. (The separate-markdown view
  is the projection of HLD-003, not a web UI — HLD-011 stays.)
- **A report is a distinct kind** — the transcendent, subject-scoped **deliverable**,
  produced *deliberately* by a task whose **purpose** is to generate/synthesize one. Such a
  task has **both** its outcome (its account of generating) *and* the report (the deliverable).
  A report *draws on* the outcomes of the subject's tasks but is **not** any single outcome
  that got big. It transcends every task: its own lifecycle, fed and updated across the subject.
- **Tasks ↔ reports are many-to-many.** Commonly one task → one report; a report can be fed
  by many tasks (subject-scoped); one task can sweep-update many reports (maintenance).
- **Feedback on a report → the agent judges the magnitude** (HLD-015): **tiny** → update in
  place; **medium** → research and add a **section**; **large** → a new task + new report
  that **supersedes**; **broad** → one task that sweeps many reports. Reports are *not*
  ownership-fenced like tasks — they are collaborative deliverables maintained under agent
  judgment; the human steers via `feedback`.
- **Report lifecycle:** `active` → (interim appends are fine) → declared **`deprecated`**,
  with fate **`superseded`** (regenerated; points to its successor) or **`obsolete`**
  (no successor; retained for audit, not deleted).
- **Two enforced invariants** (HLD-015 `lifecycle`): a `deprecated`/`obsolete` report is
  **immutable** (appends/feedback redirect to the successor); a report's lifecycle is
  **independent** of any task's (a report outlives its tasks; it is superseded without
  reopening a task — no retroactive cascade).
- **References are deprecation-aware** and **updates are attributed** — a reference resolves
  to the live successor, never silently stale; every contribution records who and when.

Reports are DB-owned and markdown-projected, exactly like the baton (HLD-003) — the output
is truth in SQLite, readable as a one-way markdown view.

*(The concrete report verb surface — create/update/section/supersede/abandon — and ref
storage are **a deferred, separate extension to HLD-009's verb contract**, pinned at build
time. Until then HLD-009 enumerates the task/steering layer only; reports are created via a
long `done` outcome and steered via `feedback`, and the remaining ops are named here but not
yet given CLI verbs. The operations and invariants above are the contract; the surface is
not.)*

---

# PART II — The engine (revised)

## HLD-004 — The task lifecycle *(revised)*

HLD-ID: HLD-004
HLD-DESC: HLD-004 is in-scope architecture at high risk, touching processing and data; "the four-state task lifecycle".
HLD-ROLE: architecture
HLD-STATUS: active
HLD-RISK: HIGH
HLD-SPECS: constitution
HLD-RESOURCES: flow.py,test_flow.py
HLD-VERIFY: only four states exist; a task cannot be done with unfinished children; done is reopenable via reopen() but the norm is to supersede with a new referencing task, not resurrect; a task parked as blocked is unassigned, keeping its label for affinity; blocked wakes to pending only when all dependencies resolve; the done/escalate/split guard is on dependencies, not on prior state — agents may operate from any non-blocked state
HLD-RATIONALE: done/escalate/split do not require in_progress (HLD-015 delegation); parking clears the assignee so a woken task re-enters the claim flow rather than granting its former holder a silent resume — ownership is re-established only through flow next, while the kept label softly routes the same session back; reopen exists but supersede-via-new-task is the idiom (mirrors report supersession, HLD-016) — resurrecting a done task is the rare path

Four states. `done` is a resting state, not a grave.

```
pending ──► in_progress ──► done
   ▲             │            │
   │             ▼            │ reopen (rare; the norm is supersede via a new referencing task)
   │          blocked         │
   └─────────────┴────────────┘
        wake (dependency resolved)
```

- `pending` — runnable: no unmet dependencies.
- `in_progress` — a named session is working it.
- `blocked` — parked on a dependency (a human answer and/or child tasks). **Unassigned** —
  the former holder no longer owns it — but it keeps its `label` so affinity (HLD-010) tends
  to route the same session back.
- `done` — finished, reopenable. The **idiomatic** way to revisit done work is a *new task
  referencing it* (supersede), exactly like report supersession (HLD-016); `reopen` (any
  runner or human may call it) is the rare in-place resurrection.

**The one rule:** *a task is runnable only when it has no unmet dependencies.* A task cannot
be `done` while it has unfinished children.

**Agent autonomy (HLD-015).** The diagram is the *typical* flow. Agents may
`done`/`escalate`/`split` from any non-`blocked` state; the only hard gate is the dependency
guard. The `in_progress` step is normal but not mandatory.

**Why parking unassigns.** Clearing the assignee on block means a woken task is re-claimed
through `flow next` like any other — no silent shortcut back into a task never re-claimed.
The kept label preserves stickiness without hidden ownership. (Replaces v1's
assignee-survives-blocked.)

## HLD-005 — The wait model (fork-join) *(revised)*

HLD-ID: HLD-005
HLD-DESC: HLD-005 is in-scope architecture at high risk, touching processing; "the unified fork-join wait model (escalate == split)".
HLD-ROLE: architecture
HLD-STATUS: active
HLD-RISK: HIGH
HLD-SPECS: constitution
HLD-RESOURCES: flow.py,test_flow.py
HLD-VERIFY: escalate and split both park the task as blocked, clear its assignee (label kept), and free the runner; the guard is that the task must not be done; a task holds at most one open escalation at a time (escalate is rejected when one is already open); a task is runnable only when it has no unmet dependencies
HLD-RATIONALE: one open escalation is a structural invariant (lifecycle), not a judgment constraint — a task has a single wait-channel and the agent packages its needs into one coherent handoff (HLD-015); when a human's answer only partly resolves the question, the agent re-escalates the remainder on pickup, so completeness stays the agent's judgment and the system never tracks "partial"

Escalation and sub-tasking are **the same primitive**: a task becomes `blocked`, its
assignee is cleared, and the runner moves to the next runnable task. The session never
idles. A parked task may wait minutes, days, or forever; that costs nothing.

- **escalate** → waits on **a human answer**. One open escalation at a time; a second is
  rejected. The agent is free to ask anything — packaged into one coherent question.
- **split** → waits on **its child tasks finishing**.

When all dependencies resolve the task wakes to `pending` (unassigned). Waking hands the
runner a *decision*, not an obligation. **Partial answers:** if a human's `answer` resolves
only part, the agent re-escalates the remainder on pickup; the loop continues under its
judgment.

## HLD-007 — Human-in-the-loop: answer and feedback *(revised)*

HLD-ID: HLD-007
HLD-DESC: HLD-007 is in-scope processing at medium risk, touching processing; "human-in-the-loop: answer resolves an open escalation, feedback steers".
HLD-ROLE: processing
HLD-STATUS: active
HLD-RISK: MEDIUM
HLD-SPECS: constitution
HLD-RESOURCES: flow.py,core.md
HLD-VERIFY: answer resolves a task's open escalation — appended to the task's baton, resolves the one open escalation, and wakes the task; answer is rejected when there is no open escalation; feedback steers — on a report it drives an agent-judged update (in-place, section, supersede, or sweep), and as new scope it creates a referenced task; feedback never forces a state change a guard would forbid; an answer is always about the task it wakes
HLD-RATIONALE: the v1 reply verb was overloaded across six states and carried a runner-side "is this new scope?" branch; the discriminator "was the task waiting for this?" splits it — yes is an answer (a fork-join join, in-band, always about this task), no is feedback (steering output or injecting scope). The human picks the channel, so answer never guesses; the magnitude of a feedback response is the agent's judgment (HLD-015), not hardcoded into a verb

The rule that separates the two:

> **`answer`** responds to a question the task is waiting on. **`feedback`** steers — it
> comments on output or injects scope a task wasn't waiting on.

**`answer <id> <text>`** — valid only when the task is blocked on an open escalation.
Appends to the task's baton, resolves that one escalation, wakes the task. An answer is, by
construction, **about this task** (no "is this new scope?" branch — that was v1 `reply`). If
an answer happens to *reveal* new scope, the runner spins it off by its own judgment
(HLD-015), never silently merging it. `answer` with no open escalation → rejected:
*"nothing to answer; use feedback."*

**`feedback <id> <text>`** — steers. On a **report**, it drives an agent-judged update
(HLD-016: in-place / section / supersede / sweep) — the human says what's wrong or wanted;
the agent decides how big the response is. As **new scope**, it creates a referenced task
(sugar over `add` + a reference): the new task is a regular pending task linked to the
source (a db reference, **not** `parent_id`, so no fork-join dependency and a `done`/report
source is never blocked or mutated). Feedback never reaches in and mutates a `done` task or
a `deprecated` report — it produces *new* work or a *successor*.

## HLD-008 — The baton: the context substrate *(revised: repositioned)*

HLD-ID: HLD-008
HLD-DESC: HLD-008 is in-scope architecture at high risk, touching data and processing; "the baton is the DB-owned per-task context substrate (the means, not the output)".
HLD-ROLE: architecture
HLD-STATUS: active
HLD-RISK: HIGH
HLD-SPECS: constitution
HLD-RESOURCES: flow.py,.flow/batons/
HLD-VERIFY: the baton lives in the database and is read via the CLI; markdown batons are a one-way projection; the baton carries a task's declared context (the means by which a handoff is lossless) and is distinct from the report, which is the output (HLD-016); declared context is the only context the contract touches
HLD-RATIONALE: the baton is plumbing, not the product — it is the append-log of one task's journey that makes a handoff lossless so the report (the output) comes out good; conflating baton (context) with report (output) is the v1 framing this revision corrects

The baton is the **context substrate** — a per-task **blackboard** the runner, its
sub-tasks, and the human all read and write. It makes a handoff lossless: the next runner
reads the baton and keeps going. It is **not** the deliverable — the report is (HLD-016).
The baton is *how a task went*; the report is *what was produced*.

- **Declared context** lives on the baton: durable, inspectable, shared — an append-log.
- A runner MUST read a task's baton (`flow context <id>`) before working it and append
  progress as it goes (`flow note`). Batons are read from the database via the CLI.

## HLD-009 — The CLI contract *(revised)*

HLD-ID: HLD-009
HLD-DESC: HLD-009 is in-scope api at high risk, touching cli; "the flow CLI verbs are the runner contract; every call is a named session".
HLD-ROLE: api
HLD-STATUS: active
HLD-RISK: HIGH
HLD-SPECS: constitution
HLD-RESOURCES: flow.py,flow,core.md
HLD-VERIFY: every CLI call carries a recognized session, enforced at the CLI entry — a missing session is an error, there is no anonymous path, reads included; runners use only the listed verbs with no direct database access; answer, reopen, list, and reclaim are human/ops-facing; feedback steers and add/feedback create work
HLD-RATIONALE: the name a session declares is its bracelet (HLD-010) — accountability, not security; enforcing it once at the CLI entry (not per-verb) makes "no anonymous path" true for every command including reads, because a task and a report must always have a trackable actor behind every touch

**Every invocation names its session** (`--session <name>`), enforced **at the CLI entry** —
a call with no recognized session is an error, reads included. The CLI is for named
sessions and nobody else. The tables below omit `--session` per row for brevity; it is
required on **all** of them.

Runner-facing (the loop):

| Verb | Meaning |
|---|---|
| `flow add <text> [--label <label>]` | Create a task. `--label` groups it for affinity (HLD-010). |
| `flow next` | Claim the next runnable task for this session (or "none"). |
| `flow context <id>` | Read the task's baton (declared context) and inbound references. |
| `flow note <id> <text>` | Append progress/finding to the baton. |
| `flow decide <id> <decision>` | Record a decision. |
| `flow done <id> <outcome>` | Complete with a **mandatory** outcome (the task's account; a long one renders as separate markdown but is still an outcome, not a report — HLD-016). |
| `flow escalate <id> <question>` | Park the task on a human (one open escalation at a time). |
| `flow split <id> "child A" "child B" …` | Spawn children; park the parent. |
| `flow feedback <id> <text>` | Steer (HLD-007): drive an agent-judged report update, or inject a referenced task. |

Human/ops-facing (not part of the runner loop, but still carry a recognized session):

| Verb | Meaning |
|---|---|
| `flow answer <id> <text>` | Answer a task's one open escalation; resolve + wake. Rejected if none open. |
| `flow reopen <id>` | Resurrect a `done` task to `pending` (rare; the norm is supersede — HLD-004). Runner- or human-**callable**, but not a routine **loop step** (see the permission-vs-loop note below). |
| `flow reclaim <id>` | Immediately reclaim a non-responsive session's task (HLD-014) — the "act" in see-and-act, no waiting out the lease. |
| `flow list` | List tasks/sessions with state and liveness. Read-only. |

**Permission vs loop membership.** `core.md` defines the *routine loop* — claim → work →
hand off → done. A verb being absent from that loop (the "human/ops" set: `answer`,
`reopen`, `reclaim`, `list`) means it is *not a routine step*, **not** that a runner may not
call it. A runner may `reopen` or `reclaim` when its judgment calls for it (HLD-015); these
simply aren't part of the steady-state cycle. (`test_human_ops_verbs_absent_from_runner_loop`
therefore checks *loop membership* — absence from `core.md` — not callability.)

Runners use **only** these task/steering verbs — no direct database access, ever. The
**report verb surface (HLD-016)** is a deliberate, separate extension to this contract that
is *not yet enumerated*; until it is, this set is the task/steering layer and
`test_cli_exposes_only_contract_verbs` covers exactly that layer.

## HLD-010 — Work routing (mandatory named sessions, soft label affinity) *(revised)*

HLD-ID: HLD-010
HLD-DESC: HLD-010 is in-scope architecture at high risk, touching processing; "work routing by mandatory named sessions and soft label affinity".
HLD-ROLE: architecture
HLD-STATUS: active
HLD-RISK: HIGH
HLD-SPECS: constitution
HLD-RESOURCES: flow.py,test_flow.py
HLD-VERIFY: every claim names a session and a missing name is an error (no anonymous path); a session prefers its bound label, binds to the label of the first labeled task it claims, and falls back to any runnable task only when none of its label remain; a session sees none only when no runnable work exists; the declared name is durable — reclaim takes the task, not the identity
HLD-RATIONALE: the name is the bracelet — declaring a true name is the whole enrollment, there is no separate registration step; first contact creates the session row implicitly and the system trusts the name on sight (it cannot and need not verify truthfulness); removing the v1 anonymous path closes the unfenced legacy hole at its root

A session is **mandatory** and names itself: `flow next --session <name>` means *"I am
`<name>`; give me my next."* The name **is** the bracelet — declaring it is the enrollment;
no separate registration verb, first contact creates the session row implicitly, the system
trusts the name on sight and rejects only its absence. (Removes v1's "no `--session` behaves
as before" path — now an error.)

- **Label** — a task's optional subject (component/feature/topic); reuses the existing
  column. Also the natural scope a **report** is about (HLD-016).
- **Soft affinity** — a session starts unbound, takes the oldest runnable task of any
  subject, binds to it if labeled; bound, it prefers its label but falls back rather than
  idle. "none" only when no runnable work exists. NULL-labeled children (split of an
  unlabeled parent) enter the general pool and don't trigger binding.
- **Durable identity** — a silent session's *task* is reclaimed (HLD-014); its session row
  persists (keeps the bound label). It returns, names itself, gets fresh work.

## HLD-013 — Concurrency and durability *(revised — one addition)*

HLD-VERIFY: concurrent flow next calls claim each task at most once (the claim takes the write lock before it reads the queue); each claim records claimed by session on the baton within the same transaction; every CLI operation is one all-or-nothing transaction (a crash leaves no partial state); the connection runs WAL + busy_timeout + synchronous=NORMAL

Unchanged from v1 except: **each claim appends a `claimed by <session>` entry to the baton
inside the claim transaction**, so the baton alone records who held the task and when —
accountability is the point of the named-session model (HLD-010). The markdown projection
is written after commit; it is re-derivable, never part of a transaction.

## HLD-014 — Recovery: lease, see-and-act reclaim, fence, flaky-mark *(revised)*

HLD-ID: HLD-014
HLD-DESC: HLD-014 is in-scope architecture at high risk, touching concurrency, data and processing; "recovery: lease, see-and-act reclaim, ownership fence, permanent flaky-mark".
HLD-ROLE: architecture
HLD-STATUS: active
HLD-RISK: HIGH
HLD-SPECS: constitution
HLD-RESOURCES: flow.py,test_flow.py
HLD-VERIFY: a non-responsive session's task is reclaimable two ways — an explicit flow reclaim acts immediately on an observed non-response, and a lazy lease-TTL backstop reclaims silent tasks automatically; reclaim returns the task to pending (in_progress only, never blocked), clears assignee, records the reason, and saturates reclaim_count at RECLAIM_MAX as a permanent flaky-mark — at or past the ceiling every further orphaning escalates immediately; ownership-implying transitions by a session that is not the current owner are rejected, while an unowned task stays operable by any named session; note/decide stay multi-writer and feedback (like add) is an unfenced creation verb; reclaim runs under the claim's BEGIN IMMEDIATE
HLD-RATIONALE: every caller is now a named session (HLD-010), so the fence drops only the v1 caller-anonymous bypass; it still distinguishes a task held by another named session (rejected — no theft) from an unowned task (allowed — cleanup, HLD-015). v1's only fast recovery was the anonymous bypass, removed here — so recovery becomes see-and-act: liveness is visible (flow list shows staleness) and flow reclaim acts at once, with the lease as the automatic floor; permanent flaky-mark because a since-fixed task costs one bounded human glance while a reset risks repeating wasted silent-reclaim cycles — a clean slate is a fresh task

A session can claim a task and go non-responsive — hung, or vanished. Recovery is a
**liveness** concern, separate from the correctness HLD-013 guarantees. **See and act:**
don't wait blindly.

- **See.** `flow list` surfaces each session's staleness (last-seen, current task), so a
  non-responsive session is *visible*.
- **Act now.** `flow reclaim <id>` immediately returns an observed-non-responsive session's
  task — no waiting out the lease. (This restores v1's emergency override, but **named and
  logged** instead of anonymous.)
- **Automatic floor.** A task `in_progress` past `LEASE_TTL` (default 1 hour) is reclaimed
  lazily inside `flow next` — the backstop for a session nobody noticed. `note`/`decide`
  refresh the lease stamp; silence alone defines a silent task.
- **Reclaim** returns the task to `pending`, **clears assignee**, records
  `reclaimed: session X …`, and bumps `reclaim_count`. Only `in_progress` is reclaimed;
  `blocked` is parked by design. Runs under the claim's `BEGIN IMMEDIATE`.
- **Permanent flaky-mark.** `reclaim_count` saturates at `RECLAIM_MAX` (default 3); at/past
  the ceiling, any further orphaning **escalates immediately** instead of requeuing. The
  mark never resets — an `answer` resolves each escalation but a fresh start is a **new task**
  (count 0), not a reset.
- **Fence.** `done`/`escalate`/`split` are rejected when the task is held by a *different*
  named session. An unowned task stays operable by any named session (the cleanup pattern,
  HLD-015). The only v1 removal is the caller-anonymous bypass — there is no anonymous
  caller anymore.
- **Blackboard multi-writer.** `note`/`decide` are never fenced (attributed, per HLD-008).
  `feedback` is a creation/steering verb (like `add`) — identity-gated, not an ownership
  transition — so it too is unfenced.

## HLD-011 — Out of scope *(revised: keep the boundary coherent)*

HLD-ID: HLD-011
HLD-ROLE: governance
HLD-STATUS: active
HLD-RISK: LOW
HLD-SPECS: TBD
HLD-RESOURCES: TBD
HLD-DESC: HLD-011 is out-of-scope governance at low risk, touching none; "still stripped: web UI / HTTP API, connection pools, health-monitoring daemons, automatic failover, environment staging, migration tooling — reports and lazy reclaim are back in scope".

The strip's boundary still holds for the operational machinery — **out of scope:** the web
UI / HTTP API, connection pools, **health-monitoring daemons**, automatic failover,
environment staging, and migration tooling. Re-introduce only with a documented reason.

Two things this revision **moves back in scope**, with the reason stated:
- **Reports (HLD-016)** — the strip dropped them along with the cruft; they are the system's
  *output* (HLD-001) and return as a primary concept, CLI + markdown only (no web UI).
- **See-and-act recovery (HLD-014)** — `flow list` liveness + an explicit `flow reclaim`.
  This is **not** a health-monitoring daemon: there is no background process. Liveness is
  *observed on demand* (in `list`) and reclaim is *lazy* (inside `flow next`) or *explicit*
  (the verb). The stripped "daemon" was a continuous monitor; this is on-demand, so the
  boundary is intact.

---

## Small doc fixes (no behavior change)

- **HLD-002:** add the load-bearing terms `report` (output) and `outcome` (per-task result),
  and the new baton entry kind `claimed`. Clarify baton = context, report = output.
- **HLD-004 diagram:** prose already says `in_progress` is optional; leave as "typical."
- **HLD-010:** NULL-labeled children enter the general pool (now stated in-section).
- `note` vs `decide` is a presentational distinction only (no logic branches on the kind).
- **Woken tasks** are claimed before newer work (FIFO by id) — resuming started work first
  is intended; note it.

---

## Promotion / implementation plan (when approved)

Per section, through the build loop — not hand-edited into existence.

1. **Promote HLD text** section-by-section into `HLD.md`. For each changed/new HIGH-risk
   section, update its mirroring test docstring in the same step (keeps the drift guards
   green). **HLD-015 and HLD-016 are new HIGH-risk** — each needs its literal ID (`HLD-015`,
   `HLD-016`) **and** its full VERIFY verbatim in a test docstring, or
   `test_every_high_risk_invariant_has_a_test` and `test_high_risk_verify_texts_present_in_tests`
   go red.
2. **Code (`flow.py`):**
   - Enforce `--session` at the CLI entry for **every** command (B2 — not just `next`).
   - `next_task`: write the `claimed by <session>` baton entry (kind/text pinned here).
   - `_require_owner`: delete only the `if session is None: return` bypass.
   - `escalate`/`split`: clear `assignee` on parking; `escalate` rejects a second open escalation.
   - **`_reclaim_orphans` escalate-on-ceiling branch must also clear `assignee`** (the inline-SQL spot the prior plan missed).
   - rename `reply` → `answer` (reject when no open escalation; remove the done→reopen branch).
   - add `feedback` (steer reports + create referenced task) and the report entity (DB-owned, projected; ref storage = a `task_refs`/`report_refs` table — no migration vs a column that needs `_migrate`).
   - add `reclaim` (explicit immediate reclaim) and liveness/staleness in `list`.
   - tag every `raise FlowError` with `# INVARIANT: dependency|identity|ownership|lifecycle|existence`.
3. **`core.md`:** rename `reply`→`answer` everywhere (incl. line ~15 "any human reply");
   teach `feedback` as a runner verb; rewrite "On a woken task" — `answer` is answer-only
   (always about this task), new scope is `feedback`/the runner's own follow-up.
4. **Tests — the full blast radius:**
   - *Bypass cohort* (now error: fence verbs with no session; `next_task(assignee=None)`): `test_next_skips_blocked`, `test_cli_roundtrip`, `test_runner_verb_contracts`(+`_split`), `test_hld004/005/007_verify_invariant`, `test_escalation_question_on_baton`, `test_next_without_session_unchanged`, `test_concurrent_next_claims_each_task_once`, and `test_no_session_task_unfenced` (premise removed).
   - *Reply→answer + done-reopen removal*: `test_reply_wakes_task`, `test_reply_recorded_on_baton` (rename), `test_hld007_late_reply_reopens_done_task`, `test_late_reply_on_done_child_parent_stays_done` (path deleted), plus retire `test_binary_reply_rule_in_core_md`, `test_hld007_binary_reply_branches`.
   - *Stale taxonomy*: `test_human_ops_verbs_absent_from_runner_loop`, `test_hld009_verify_invariant` → `{answer,reopen,list,reclaim}` human/ops, `feedback` a runner verb.
   - *Verb set*: `test_cli_exposes_only_contract_verbs` → `{add,next,context,note,decide,done,escalate,split,feedback,answer,reopen,reclaim,list}`.
   - New characterization: bracelet-required claim; blocked-unassigns; answer-rejects-no-escalation; feedback (report update spectrum + referenced task); one-escalation; reclaim see-and-act; permanent flaky-mark; report lifecycle + deprecated-immutable + deprecation-aware reference; HLD-015 annotation guard.
   - *Changed HIGH-risk VERIFY → update the mirror-test docstring verbatim, or `test_high_risk_verify_texts_present_in_tests` goes red:* `test_connection_hardening` (HLD-013), `test_hld008_verify_invariant` (HLD-008), `test_hld010_verify_invariant` (HLD-010), `test_orphaned_task_reclaimed` (HLD-014) — each carries old VERIFY text that the v2 rewrite changed.
5. **HLD.md sweep:** every stray `reply` outside the revised sections (HLD-002/008 vocab,
   HLD-014 multi-writer list) → `answer`/`feedback`.
6. **Specs:** regenerate affected specs (001, 004, 005, 007, 008, 009, 010, 013, 014, new
   015 & 016) via SpecKit; in-flight 024 is unaffected.
7. **Promotion-time verification:** diff each section against current `HLD.md` before it
   lands (these were drafted partly from an earlier read); re-run the 63-test baseline after
   each promoted section.
