# Baton Flow — High-Level Design

**Status**: Authoritative design. Single source of truth.
**One line**: Context, intent, and decisions that survive every handoff between AI sessions.

---

## HLD-001 - What it is

HLD-ID: HLD-001
HLD-DESC: HLD-001 is in-scope purpose at medium risk, touching none; "what Baton Flow is — keeping AI work continuous across sessions".
HLD-ROLE: purpose
HLD-STATUS: active
HLD-RISK: MEDIUM
HLD-SPECS: TBD
HLD-RESOURCES: README.md,core.md

Baton Flow keeps work continuous across AI-assisted sessions. You create tasks; a
runner (an AI session, or you) picks one up, works it, and writes everything it
learns onto a **baton** — a per-task document that travels from runner to runner so
nothing is ever lost. When a runner can't finish — it needs a human call, or the work
must be broken into pieces — it **hands off** and moves on. The work waits, the
session never idles.

It exists to kill three specific pains:

1. **Context loss** between AI sessions on multi-step work.
2. **No visibility** into what the AI is doing while it works.
3. **No way to steer** without starting over.

The baton solves all three: it *is* the durable context, it's readable at any moment,
and you steer by replying to it.

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
HLD-VERIFY: only four states exist; a task cannot be done with unfinished children; done is reopenable; blocked wakes to pending only when all dependencies resolve

Four states. `done` is a resting state, not a grave — it can be reopened.

```
pending ──► in_progress ──► done
   ▲             │            │
   │             ▼            │ reopen (by human, or a late reply)
   │          blocked         │
   └─────────────┴────────────┘
        wake (dependency resolved)
```

- `pending` — runnable: no unmet dependencies.
- `in_progress` — a runner is working it.
- `blocked` — parked, waiting on a dependency (a human answer and/or child tasks).
- `done` — finished, but reopenable.

**The one rule that governs everything:** *a task is runnable only when it has no
unmet dependencies.* A task cannot be `done` while it has unfinished children.

## HLD-005 - The wait model (fork-join)

HLD-ID: HLD-005
HLD-DESC: HLD-005 is in-scope architecture at high risk, touching processing; "the unified fork-join wait model (escalate == split)".
HLD-ROLE: architecture
HLD-STATUS: active
HLD-RISK: HIGH
HLD-SPECS: constitution
HLD-RESOURCES: flow.py,test_flow.py
HLD-VERIFY: escalate and split both park the task as blocked and free the runner; a task is runnable only when it has no unmet dependencies

Escalation and sub-tasking are **the same primitive**: a task becomes `blocked`
because it's waiting on something, and the runner immediately moves to the next
runnable task. The session never idles — it is the scarce resource and must keep
working. A parked task may wait **minutes, days, or forever**; that costs nothing.

A dependency is satisfied by an event:

- **escalate** → the task waits on **a human answer**.
- **split** → the task waits on **its child tasks finishing**.

When every dependency resolves, the task wakes back to `pending`. Waking hands the
runner a *decision*, not an obligation: the work may now be moot (mark `done`), or need
more work, or be reopened. This is fork–join over a dependency graph — the same shape
as `async/await` joins or a build-system DAG.

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

## HLD-007 - Human-in-the-loop (human → runner)

HLD-ID: HLD-007
HLD-DESC: HLD-007 is in-scope processing at medium risk, touching processing; "human-in-the-loop replies route back to the runner".
HLD-ROLE: processing
HLD-STATUS: active
HLD-RISK: MEDIUM
HLD-SPECS: constitution
HLD-RESOURCES: flow.py,core.md
HLD-VERIFY: a human reply about the task itself appends to the baton and unblocks; a reply about anything else becomes a new task and leaves the original blocked

When the human answers a blocked task, one binary question decides what happens:

> **Is the reply about this task itself?**
>
> - **Yes** → append it to the baton; task `blocked → pending` (re-enters the loop).
> - **No** → it becomes a **new task**; the original stays blocked.

This keeps steering lossless and never silently merges unrelated scope into a task.

## HLD-008 - The baton (per-task document)

HLD-ID: HLD-008
HLD-DESC: HLD-008 is in-scope architecture at high risk, touching data and processing; "the baton is the DB-owned per-task document".
HLD-ROLE: architecture
HLD-STATUS: active
HLD-RISK: HIGH
HLD-SPECS: constitution
HLD-RESOURCES: flow.py,.flow/batons/
HLD-VERIFY: the baton lives in the database and is read via the CLI; markdown batons are a one-way projection; declared context is the only context the contract touches

The baton is a **blackboard**: a shared surface that multiple knowledge sources —
the runner, its sub-tasks, and the human — all read and write. It is the artifact that
makes a handoff lossless; the next runner reads the baton and keeps running.

- **Declared context** lives on the baton: durable, inspectable, shared. This is the
  only context the contract touches.
- **Actual context** (a session's internal working memory) is private and out of scope.
  *Future optimization:* route a task to whichever session already has its actual
  context warm. Not built; noted.

A runner MUST read a task's baton (`flow context <id>`) before working it, and append
progress as it goes (`flow note`). Batons are read from the database via CLI, never
from markdown files directly.

## HLD-009 - The CLI contract

HLD-ID: HLD-009
HLD-DESC: HLD-009 is in-scope api at high risk, touching cli; "the flow CLI verbs are the runner contract".
HLD-ROLE: api
HLD-STATUS: active
HLD-RISK: HIGH
HLD-SPECS: constitution
HLD-RESOURCES: flow.py,flow,core.md
HLD-VERIFY: runners use only the listed verbs; no direct database access; reply and reopen are human/ops-facing and not part of the runner loop

The entire runner-facing API is small. This is the agnostic surface.

| Verb | Meaning |
|------|---------|
| `flow add <text>` | Create a task (used by the human, and by a runner for the "No" reply branch in §7). |
| `flow next` | Get the next runnable task assigned to me (or "none"). |
| `flow context <id>` | Read the task's baton (declared context). |
| `flow note <id> <text>` | Append progress/finding to the baton. |
| `flow done <id> <outcome>` | Complete with a stated outcome. |
| `flow escalate <id> <question>` | Park the task waiting on a human. |
| `flow split <id> "child A" "child B" …` | Spawn children; park the parent until they finish. |
| `flow decide <id> <decision>` | Record a decision. |

Runners use **only** these. No direct database access, ever.

Two verbs are **human/ops-facing**, not part of the runner loop:

| Verb | Meaning |
|------|---------|
| `flow reply <id> <text>` | Answer a blocked task (§7). Records the reply on the baton and wakes the task; the runner decides on pickup whether it's about the task or new scope. |
| `flow reopen <id>` | Move a `done` task back to `pending`. |

## HLD-010 - Work routing (soft affinity by label and named sessions)

HLD-ID: HLD-010
HLD-DESC: HLD-010 is in-scope architecture at high risk, touching processing; "work routing by soft label affinity and named sessions".
HLD-ROLE: architecture
HLD-STATUS: active
HLD-RISK: HIGH
HLD-SPECS: constitution
HLD-RESOURCES: flow.py,test_flow.py
HLD-VERIFY: `flow next` without a session returns the oldest runnable task exactly as before; a session prefers its bound label, binds to the label of the first labeled task it claims, and falls back to any runnable task only when none of its label remain; a runner sees "none" only when no runnable work exists at all

Routing keeps a session's context warm by feeding it work on one **subject** rather than
thrashing it across unrelated subjects every pickup. It hangs off one existing field
(the task's `label`) and one filter on `flow next` — the loop, the four states, and the
wake rule are untouched.

- **Label.** A task carries an optional `label` (its subject — a component, directory, or
  topic). This reuses the existing task column; no new task field is added.
- **Named sessions.** A runner identifies itself: `flow next --session <name>`. A small
  `sessions` table records each session's **bound label**; `assignee` records which
  session currently holds a task.
- **Soft affinity.** A session starts unbound and takes the oldest runnable task of any
  subject; if that task is labeled, the session **binds** to it. Once bound it prefers its
  label, but if none of its label is runnable it **falls back** to any runnable task
  (binding unchanged) rather than idle — the session is the scarce resource and must keep
  working. A runner gets "none" only when the queue holds no runnable work at all.
- **Backward compatible.** `flow next` with no `--session` behaves exactly as today.

> **Future (not built):** routing by capability and *must-halt* tasks (wait on a specific
> task instead of parking) are further fields on the same shape; add when needed.

## HLD-011 - Out of scope (deliberately stripped)

HLD-ID: HLD-011
HLD-ROLE: governance
HLD-STATUS: active
HLD-RISK: LOW
HLD-SPECS: TBD
HLD-RESOURCES: TBD
HLD-DESC: HLD-011 is out-of-scope governance at low risk, touching none; "unix-socket task delivery, connection pools, health daemons, failover, web UI / HTTP API, environment staging, migration tooling — deliberately stripped".

The prior design accreted operational machinery that is **not** part of this system:
Unix-socket task delivery, connection pools, health-monitoring daemons, automatic
failover, the web UI / HTTP API, environment staging, and migration tooling. They are
excluded on purpose to keep the contract small and the implementation a few files.
Re-introduce only with a documented reason.

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
HLD-VERIFY: concurrent `flow next` calls claim each task at most once (the claim takes the write lock before it reads the queue); every CLI operation is one all-or-nothing transaction (a crash leaves no partial state); the connection runs WAL + busy_timeout + synchronous=NORMAL

Named sessions make concurrency real, so the base layer must be strong before routing
rides on it.

- **Atomic claim.** `flow next` takes the write lock *before* it reads the queue
  (`BEGIN IMMEDIATE`), selects the runnable task, and claims it in the same transaction.
  Two runners can never both hold one task: the second sees it already `in_progress` and
  moves on.
- **One transaction per operation.** Each command commits all of its effects or none. A
  crash mid-operation cannot leave split state (e.g. a child marked `done` while its parent
  stays `blocked` forever).
- **Durable settings.** WAL journaling, a `busy_timeout` so a concurrent writer waits
  instead of failing with "database is locked," and `synchronous=NORMAL`.

The markdown projection is written *after* the transaction commits; it is a re-derivable
view, never part of a transaction.

## HLD-014 - Orphaned-work recovery (lease, reclaim, fence)

HLD-ID: HLD-014
HLD-DESC: HLD-014 is in-scope architecture at high risk, touching concurrency, data and processing; "orphaned-work recovery: lease, reclaim, fence".
HLD-ROLE: architecture
HLD-STATUS: active
HLD-RISK: HIGH
HLD-SPECS: constitution
HLD-RESOURCES: flow.py,test_flow.py
HLD-VERIFY: a task whose session has been silent past the lease TTL is reclaimed to pending — in_progress only, never blocked — recording the reason and incrementing reclaim_count; after a reclaim threshold it is escalated instead of requeued; done/escalate/split by a session that no longer holds a session-owned task are rejected; note/decide/reply stay multi-writer; reclaim runs under the claim's BEGIN IMMEDIATE

A session can claim a task and then vanish, leaving it stuck `in_progress` forever.
Recovery is a **liveness** concern, separate from the correctness HLD-013 guarantees.

- **Lease.** A claim's `updated_at` is its lease stamp; any progress (`note`, `decide`)
  refreshes it. A task `in_progress` past `LEASE_TTL` (a generous default of **1 hour**)
  is *orphaned*. There is no heartbeat obligation — silence alone, not a missing ping,
  defines an orphan.
- **Reclaim — lazy, no daemon.** Inside `flow next` (before selecting), an orphaned task
  returns to `pending`, **clears its `assignee`** (the vanished session no longer holds
  it), appends `reclaimed: session X silent since T`, and bumps a new `reclaim_count`.
  Only `in_progress` is reclaimed; `blocked` is parked by design. Reclaim happens under
  the same `BEGIN IMMEDIATE` as the claim, so it cannot race.
- **Escalate-on-repeat.** After `RECLAIM_MAX` reclaims (default **3**), the task escalates
  instead of requeuing — reusing the escalation primitive (HLD-006 repeated failure).
- **Fence — ownership-implying transitions only.** When a task is held by a named session,
  `done` / `escalate` / `split` must carry that session or are rejected (`you no longer
  hold task N`). Tasks claimed with no session (the legacy path, HLD-010) stay unfenced, so
  `flow next` without a session behaves exactly as today.
- **Blackboard stays multi-writer.** `note` / `decide` / `reply` are never fenced; they get
  attribution, per the baton model (HLD-008). Fencing them would break the blackboard.
