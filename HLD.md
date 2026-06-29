# Baton Flow — High-Level Design

**Status**: Authoritative design. Single source of truth.
**One line**: Context, intent, and decisions that survive every handoff between AI sessions.

---

## HLD-001 - What it is

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

## HLD-002 - Vocabulary

HLD-ID: HLD-002
HLD-DESC: HLD-002 is in-scope reference at low risk, touching none; "load-bearing vocabulary: baton, handoff, runner".
HLD-ROLE: reference
HLD-STATUS: active
HLD-RISK: LOW
HLD-SPECS: TBD
HLD-RESOURCES: core.md

| Term | Meaning |
|------|---------|
| **Runner** | Anything that does work: an AI session (Claude, Devin, Codex…) or the human. Pluggable. |
| **Task** | A unit of work with a lifecycle. |
| **Baton** | The per-task document that carries context across handoffs. The shared blackboard for that task. (Replaces the old "WIP".) |
| **Handoff** | The act of passing: escalate to a human, spawn sub-tasks, or wake a parked task. |
| **Decision** | A recorded choice, durable and inspectable. |

## HLD-003 - Core model

HLD-ID: HLD-003
HLD-DESC: HLD-003 is in-scope governance at high risk, touching data and processing; "SQLite is the single source of truth; markdown is one-way".
HLD-ROLE: governance
HLD-STATUS: active
HLD-RISK: HIGH
HLD-SPECS: constitution
HLD-RESOURCES: flow.py,.flow/,.specify/memory/constitution.md
HLD-VERIFY: SQLite is the only source of truth; markdown is a one-way projection, never an input; the loop depends only on the CLI + text and names no specific AI

**Single source of truth.** A SQLite database holds all state. Markdown files are a
**one-way projection** of the database for human reading — never an input. The
database is truth; markdown is the view.

**The contract is agnostic.** The execution loop is defined in one file (`core.md`)
that depends on **exactly two interfaces**: a **CLI** (the verbs a runner calls) and
**markdown/text** (what it reads and writes). It never names a specific AI. Any runner
that can run a shell command and read/write text can execute it. Claude, Devin, and
Codex differ *only* in how they are handed `core.md` — not in the loop itself. That is
the entire pluggability mechanism.

```
runner (any AI, or human)
   │  runs the loop in core.md
   ▼
CLI verbs  ──►  SQLite (source of truth)  ──►  markdown projection (read-only view)
```

## HLD-004 - The task lifecycle

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
The kept label preserves stickiness without hidden ownership.

## HLD-005 - The wait model (fork-join)

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

## HLD-006 - Escalation triggers (runner → human)

HLD-ID: HLD-006
HLD-DESC: HLD-006 is in-scope processing at medium risk, touching processing; "escalation triggers from runner to human".
HLD-ROLE: processing
HLD-STATUS: active
HLD-RISK: MEDIUM
HLD-SPECS: TBD
HLD-RESOURCES: core.md,flow.py

The strength of the system is that a runner **stops and asks instead of guessing**. A
runner must escalate when:

1. **Ambiguity** — the task admits two valid readings. Ask; don't invent requirements.
2. **Authority** — a call only the human can make: product direction, credentials, spend.
3. **Irreversibility** — an action is hard to undo (delete, deploy, external send, money). Confirm first.
4. **Repeated failure** — ~3 attempts and still failing. Escalate rather than thrash or fake success.

Any trigger → `flow escalate`, task → `blocked`, runner moves on.

## HLD-007 - Human-in-the-loop: answer / reply / feedback transition

HLD-ID: HLD-007
HLD-DESC: HLD-007 is in-scope processing at medium risk, touching processing; "human-in-the-loop: reply currently resolves an open escalation; answer/feedback naming is a tracked alignment gap".
HLD-ROLE: processing
HLD-STATUS: active
HLD-RISK: MEDIUM
HLD-SPECS: constitution
HLD-RESOURCES: flow.py,core.md
HLD-VERIFY: reply currently resolves a task's open escalation — appended to the task's baton, resolves the one open escalation, and wakes the task; answer and feedback are target contract names, not fully implemented CLI verbs yet; feedback remains a deferred steering/new-scope verb; naming alignment is tracked explicitly rather than silently fixed
HLD-RATIONALE: the target contract separates a waiting-task response from steering/new-scope feedback. The current implementation still exposes `reply` for the waiting-task response and has not yet exposed first-class `answer` or `feedback` verbs. That is a tracked transition gap, not a reason to pretend the target names are implemented.

The target rule that separates the two:

> **`answer`** responds to a question the task is waiting on. **`feedback`** steers — it
> comments on output or injects scope a task wasn't waiting on.

**Target `answer <id> <text>`; current `reply <id> <text>`.** The implemented verb is
`reply`; `answer` is the target name for the same waiting-task response. It is valid only
when the task is blocked on an open escalation.
Appends to the task's baton, resolves that one escalation, wakes the task. An answer is, by
construction, **about this task** (no "is this new scope?" branch). If
an answer happens to *reveal* new scope, the runner spins it off by its own judgment
(HLD-015), never silently merging it. `answer` with no open escalation → rejected:
*"nothing to answer; use feedback."*
Current `reply` is broader than the target `answer`: it also reopens a done task as a late
reply signal, and that compatibility behavior remains implemented until the naming/verb
split is deliberately completed.

**Deferred `feedback <id> <text>`.** Feedback steers. On a **report**, it drives an agent-judged update
(HLD-016: in-place / section / supersede / sweep) — the human says what's wrong or wanted;
the agent decides how big the response is. As **new scope**, it creates a referenced task
(sugar over `add` + a reference): the new task is a regular pending task linked to the
source (a db reference, **not** `parent_id`, so no fork-join dependency and a `done`/report
source is never blocked or mutated). Feedback never reaches in and mutates a `done` task or
a `deprecated` report — it produces *new* work or a *successor*.

## HLD-008 - The baton: the context substrate

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

## HLD-009 - The CLI contract during session/reclaim transition

HLD-ID: HLD-009
HLD-DESC: HLD-009 is in-scope api at high risk, touching cli; "the flow CLI verbs are the runner contract; named sessions are preferred while the legacy anonymous path remains temporarily allowed".
HLD-ROLE: api
HLD-STATUS: active
HLD-RISK: HIGH
HLD-SPECS: constitution
HLD-RESOURCES: flow.py,flow,core.md
HLD-VERIFY: named sessions are preferred and should become mandatory later, but the legacy anonymous path remains temporarily allowed; runners use only the listed implemented verbs with no direct database access; reply is the current human answer verb; feedback, answer naming, and explicit reclaim remain tracked alignment gaps; lazy lease-TTL reclaim is the implemented reclaim path
HLD-RATIONALE: the name a session declares is its bracelet (HLD-010) — accountability, not security. The target state is CLI-entry enforcement for every call, reads included. Transition policy C keeps the legacy anonymous path temporarily allowed so current behavior stays honest while named-session enforcement is implemented deliberately later.

**Named sessions are preferred now and mandatory later.** A compliant invocation names its
session (`--session <name>` or the current `--assignee <name>` compatibility spelling).
The legacy no-session path still exists temporarily and is a known gap, not a completed
contract. The tables below omit session flags per row for brevity.

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
| `flow feedback <id> <text>` | Deferred steering verb (HLD-007): target name for report feedback or referenced-task injection. |

Human/ops-facing (not part of the runner loop):

| Verb | Meaning |
|---|---|
| `flow reply <id> <text>` | Current implemented answer path: resolve a task's one open escalation and wake it. Target naming alignment to `answer` is tracked, not silently fixed. |
| `flow reopen <id>` | Resurrect a `done` task to `pending` (rare; the norm is supersede — HLD-004). Runner- or human-**callable**, but not a routine **loop step** (see the permission-vs-loop note below). |
| `flow reclaim <id>` | Deferred explicit reclaim verb (HLD-014). Current implementation has lazy lease-TTL reclaim inside `flow next`. |
| `flow list` | List tasks with state. Session/liveness visibility is not implemented yet. Read-only. |
| `flow backup <path>` | Write a SQLite-safe database snapshot for operational backup (HLD-013). |
| `flow check` | Run SQLite `PRAGMA integrity_check` and print the result (HLD-013). |

**Permission vs loop membership.** `core.md` defines the *routine loop* — claim → work →
hand off → done. A verb being absent from that loop (the "human/ops" set: `reply`,
`reopen`, `list`, `backup`, `check`, plus deferred `answer`/`feedback`/`reclaim`) means it
is *not a routine runner step*. This slice does not grant runner permission for
`reply`/`reopen`/`list`; `backup` and `check` are operator maintenance verbs only. Any
future runner-callability change needs its own HLD decision. (`test_human_ops_verbs_absent_from_runner_loop`
therefore checks absence from `core.md`.)

Runners use **only** these task/steering verbs — no direct database access, ever. The
**report verb surface (HLD-016)** is a deliberate, separate extension to this contract that
is *not yet enumerated*; until it is, this set is the task/steering plus maintenance layer and
`test_cli_exposes_only_contract_verbs` covers exactly that layer.

## HLD-010 - Work routing (preferred named sessions, soft label affinity)

HLD-ID: HLD-010
HLD-DESC: HLD-010 is in-scope architecture at high risk, touching processing; "work routing by preferred named sessions and soft label affinity during the anonymous-path transition".
HLD-ROLE: architecture
HLD-STATUS: active
HLD-RISK: HIGH
HLD-SPECS: constitution
HLD-RESOURCES: flow.py,test_flow.py
HLD-VERIFY: named claims are preferred and missing-session claims remain a temporary legacy path, explicitly tracked as a gap; a session prefers its bound label, binds to the label of the first labeled task it claims, and falls back to any runnable task only when none of its label remain; a session sees none only when no runnable work exists; the declared name is durable — lazy reclaim takes the task, not the identity
HLD-RATIONALE: the name is the bracelet — declaring a true name is the whole enrollment, there is no separate registration step. The target state rejects missing names, but transition policy C keeps the v1 anonymous path temporarily allowed until enforcement is implemented and tested.

A named session says `flow next --session <name>` or current compatibility spelling
`--assignee <name>`: *"I am `<name>`; give me my next."* Named sessions are the preferred
path and the future mandatory path. Missing-session claims still work temporarily through
the legacy anonymous path and must stay visible as a known gap until removed deliberately.

- **Label** — a task's optional subject (component/feature/topic); reuses the existing
  column. Also the natural scope a **report** is about (HLD-016).
- **Soft affinity** — a session starts unbound, takes the oldest runnable task of any
  subject, binds to it if labeled; bound, it prefers its label but falls back rather than
  idle. "none" only when no runnable work exists. NULL-labeled children (split of an
  unlabeled parent) enter the general pool and don't trigger binding.
- **Durable identity** — a silent session's *task* is reclaimed (HLD-014); its session row
  persists (keeps the bound label). It returns, names itself, gets fresh work.

## HLD-011 - Out of scope

HLD-ID: HLD-011
HLD-ROLE: governance
HLD-STATUS: active
HLD-RISK: LOW
HLD-SPECS: TBD
HLD-RESOURCES: TBD
HLD-DESC: HLD-011 is out-of-scope governance at low risk, touching none; "still stripped: web UI / HTTP API, connection pools, health-monitoring daemons, automatic failover, environment staging, migration tooling — reports and lazy reclaim are back in scope; explicit reclaim remains deferred".

The strip's boundary still holds for the operational machinery — **out of scope:** the web
UI / HTTP API, connection pools, **health-monitoring daemons**, automatic failover,
environment staging, and migration tooling. Re-introduce only with a documented reason.

Two things this revision **moves back in scope**, with the reason stated:
- **Reports (HLD-016)** — the strip dropped them along with the cruft; they are the system's
  *output* (HLD-001) and return as a primary concept, CLI + markdown only (no web UI).
- **Lazy recovery (HLD-014)** — `flow next` performs lease-TTL reclaim as an automatic
  floor. Explicit `flow reclaim` remains deferred. This is **not** a health-monitoring
  daemon: there is no background process. Liveness is observed on demand and reclaim is
  lazy inside `flow next`; the stripped "daemon" was a continuous monitor, so the boundary
  is intact.

## HLD-012 - Technology

HLD-ID: HLD-012
HLD-DESC: HLD-012 is in-scope operations at low risk, touching none; "technology choices: Python, SQLite, files".
HLD-ROLE: operations
HLD-STATUS: active
HLD-RISK: LOW
HLD-SPECS: TBD
HLD-RESOURCES: flow.py

- **Language**: Python 3.10+
- **State**: SQLite (WAL mode), single source of truth.
- **Projection**: Markdown, one-way out.
- **Loop**: `core.md`, agnostic, over the CLI + text interfaces.
- **Runner (now)**: Claude. **Later (pluggable)**: Devin, Codex.

## HLD-013 - Concurrency and durability

HLD-ID: HLD-013
HLD-DESC: HLD-013 is in-scope architecture at high risk, touching concurrency and data; "concurrency and durability — atomic claim, WAL".
HLD-ROLE: architecture
HLD-STATUS: active
HLD-RISK: HIGH
HLD-SPECS: constitution
HLD-RESOURCES: flow.py,test_flow.py
HLD-VERIFY: concurrent flow next calls claim each task at most once (the claim takes the write lock before it reads the queue); each claim records claimed by session on the baton within the same transaction; every CLI operation is one all-or-nothing transaction (a crash leaves no partial state); the connection runs WAL + busy_timeout + synchronous=NORMAL

Named sessions make concurrency real, so the base layer must be strong before routing
rides on it.

- **Atomic claim.** `flow next` takes the write lock *before* it reads the queue
  (`BEGIN IMMEDIATE`), selects the runnable task, records `claimed by <session>` on the
  baton, and claims it in the same transaction. Two runners can never both hold one task:
  the second sees it already `in_progress` and moves on.
- **One transaction per operation.** Each command commits all of its effects or none. A
  crash mid-operation cannot leave split state (e.g. a child marked `done` while its parent
  stays `blocked` forever).
- **Durable settings.** WAL journaling, a `busy_timeout` so a concurrent writer waits
  instead of failing with "database is locked," and `synchronous=NORMAL`.
- **Operational backup.** Use `flow backup <path>` for live snapshots. It uses SQLite's
  backup API and verifies the snapshot with `PRAGMA integrity_check`. Do not copy only
  `.flow/flow.db` while WAL is active; committed data may still be in `.flow/flow.db-wal`
  with coordination state in `.flow/flow.db-shm`. If doing a file-level copy instead,
  quiesce/checkpoint the database and include the `-wal` and `-shm` companions.
- **Integrity check.** Use `flow check` to run `PRAGMA integrity_check` explicitly before
  larger behavior changes, after backup, or after moving a database.

The markdown projection is written *after* the transaction commits; it is a re-derivable
view, never part of a transaction.

## HLD-014 - Recovery: lease, lazy reclaim, fence, flaky-mark

HLD-ID: HLD-014
HLD-DESC: HLD-014 is in-scope architecture at high risk, touching concurrency, data and processing; "recovery: lease, lazy reclaim, ownership fence, permanent flaky-mark; explicit reclaim deferred".
HLD-ROLE: architecture
HLD-STATUS: active
HLD-RISK: HIGH
HLD-SPECS: constitution
HLD-RESOURCES: flow.py,test_flow.py
HLD-VERIFY: lazy lease-TTL reclaim is implemented inside flow next and explicit flow reclaim is deferred; lazy reclaim returns a silent in_progress task to pending, clears assignee, records the reason, and saturates reclaim_count at RECLAIM_MAX as a permanent flaky-mark — at or past the ceiling every further orphaning escalates immediately; ownership-implying transitions by a named session that is not the current owner are rejected, while legacy anonymous/unowned paths remain temporarily operable; note/decide stay multi-writer; feedback as a creation/steering verb is deferred; lazy reclaim runs under the claim's BEGIN IMMEDIATE
HLD-RATIONALE: named-session fencing is the target state, but transition policy C keeps the legacy anonymous path temporarily allowed (HLD-009/HLD-010). Current recovery has the lazy lease-TTL backstop inside `flow next`; explicit `flow reclaim` remains deferred so operators do not infer a see-and-act verb that the implementation does not expose yet.

A session can claim a task and go non-responsive — hung, or vanished. Recovery is a
**liveness** concern, separate from the correctness HLD-013 guarantees.

- **See, deferred.** Target session/liveness visibility would surface each session's
  staleness (last-seen, current task). Current `flow list` is task-only.
- **Act now, deferred.** Target `flow reclaim <id>` would immediately return an
  observed-non-responsive session's task. It is not implemented in this transition slice.
- **Automatic floor.** A task `in_progress` past `LEASE_TTL` (default 1 hour) is reclaimed
  lazily inside `flow next` — the backstop for a session nobody noticed. `note`/`decide`
  refresh the lease stamp; silence alone defines a silent task.
- **Reclaim** returns the task to `pending`, **clears assignee**, records
  `reclaimed: session X …`, and bumps `reclaim_count`. Only `in_progress` is reclaimed;
  `blocked` is parked by design. Runs under the claim's `BEGIN IMMEDIATE`.
- **Permanent flaky-mark.** `reclaim_count` saturates at `RECLAIM_MAX` (default 3); at/past
  the ceiling, any further orphaning **escalates immediately** instead of requeuing. The
  mark never resets — a current `reply` / target `answer` resolves each escalation but a
  fresh start is a **new task** (count 0), not a reset.
- **Fence.** `done`/`escalate`/`split` are rejected when the task is held by a *different*
  named session. Unowned and legacy anonymous paths remain temporarily operable; this is a
  known transition gap, not the final named-session contract.
- **Blackboard multi-writer.** `note`/`decide` are never fenced (attributed, per HLD-008).
  Target `feedback` is a deferred creation/steering verb (like `add`) — identity-gated,
  not an ownership transition — so it remains a future unfenced verb.

## HLD-015 - The autonomy contract: enforce invariants, delegate judgment

HLD-ID: HLD-015
HLD-DESC: HLD-015 is in-scope governance at high risk, touching processing; "the contract enforces invariants and delegates judgment to the agent".
HLD-ROLE: governance
HLD-STATUS: active
HLD-RISK: HIGH
HLD-SPECS: constitution
HLD-RESOURCES: flow.py,core.md,test_flow.py
HLD-VERIFY: every raise FlowError in flow.py is tagged with the one invariant it protects, drawn from the closed set dependency, identity, ownership, lifecycle, existence; a raise that cannot be honestly tagged from that set is flagged for review as candidate overreach; the target agent-discretion behaviors (done/escalate/split from any non-blocked state, answer-then-runner-decides, feedback-magnitude-is-judged, waking-as-a-decision) are intentional, not defects, while answer/feedback naming remains a tracked transition gap
HLD-RATIONALE: an unwritten principle the whole system leans on is itself a stated-not-enforced gap; the tagging guard makes the enforcement boundary auditable without overclaiming — it is a review-forcing tripwire (it surfaces guards that protect no invariant), not a mechanical proof that no overreach exists

The engine constrains only what **must** be true — the closed invariant set:

- **dependency** — a task can't be `done` with unmet dependencies (open escalation or unfinished children); a split must have ≥1 child (no stranded parent).
- **identity** — named sessions are the preferred and future mandatory path; the current
  anonymous compatibility path is a tracked gap rather than the final contract
  (HLD-009/010).
- **ownership** — a task held by a named session can't be transitioned by another (HLD-014).
- **lifecycle** — the state machine is well-formed: four task states, legal transitions only (`done` can't be escalated/split; `reopen` only from `done`), one open escalation at a time, and **a `deprecated`/`obsolete` report is immutable** (HLD-016).
- **existence** — operations target a real task/report.

**Everything above that floor is the agent's call:** when to label, how big a response a
target piece of feedback deserves (update / section / supersede / sweep — HLD-016), whether a
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

## HLD-016 - The output layer: outcome and report

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
storage are **a deferred, separate extension to HLD-009's verb contract**, pinned separately.
Until then HLD-009 enumerates the task/steering layer only; reports are represented through
long `done` outcomes, while feedback-driven report steering remains deferred with the rest
of the report verb surface. The operations and invariants above are the contract; the
surface is not.)*
