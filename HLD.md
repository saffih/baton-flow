# Baton Flow — High-Level Design

**Status**: Authoritative design. Single source of truth.
**One line**: Context, intent, and decisions that survive every handoff between AI sessions.

---

## 1. What it is

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

## 2. Vocabulary

| Term | Meaning |
|------|---------|
| **Runner** | Anything that does work: an AI session (Claude, Devin, Codex…) or the human. Pluggable. |
| **Task** | A unit of work with a lifecycle. |
| **Baton** | The per-task document that carries context across handoffs. The shared blackboard for that task. (Replaces the old "WIP".) |
| **Handoff** | The act of passing: escalate to a human, spawn sub-tasks, or wake a parked task. |
| **Decision** | A recorded choice, durable and inspectable. |

## 3. Core model

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

## 4. The task lifecycle

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

## 5. The wait model (fork–join)

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

## 6. Escalation triggers (runner → human)

The strength of the system is that a runner **stops and asks instead of guessing**. A
runner must escalate when:

1. **Ambiguity** — the task admits two valid readings. Ask; don't invent requirements.
2. **Authority** — a call only the human can make: product direction, credentials, spend.
3. **Irreversibility** — an action is hard to undo (delete, deploy, external send, money). Confirm first.
4. **Repeated failure** — ~3 attempts and still failing. Escalate rather than thrash or fake success.

Any trigger → `flow escalate`, task → `blocked`, runner moves on.

## 7. Human-in-the-loop (human → runner)

When the human answers a blocked task, one binary question decides what happens:

> **Is the reply about this task itself?**
>
> - **Yes** → append it to the baton; task `blocked → pending` (re-enters the loop).
> - **No** → it becomes a **new task**; the original stays blocked.

This keeps steering lossless and never silently merges unrelated scope into a task.

## 8. The baton (per-task document)

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

## 9. The CLI contract

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

## 10. Extensibility (deferred, not built)

The model stays this small because all future complexity hangs off one field and one
filter, never the loop:

- **Routing by type/capability** — give a task an optional `type` tag; teach `flow next`
  to filter on it. That alone enables "cheap model for DB tasks, strong model for
  architecture," or capability-scoped sessions. The loop, states, and wake rule are
  untouched.
- **Multiple sessions** — every session calls `flow next`; the queue hands out runnable
  tasks. Work-stealing falls out for free. No contract change.
- **Must-halt tasks** — a tag that makes the session wait on a specific task instead of
  parking it. Another field; add when needed.

> **Current implementation note:** the runtime assumes a **single runner**. `flow next`
> claims a task without a concurrency guard, so two runners could claim the same task.
> Claim-safety for multiple sessions is deferred until routing lands.

## 11. Out of scope (deliberately stripped)

The prior design accreted operational machinery that is **not** part of this system:
Unix-socket task delivery, connection pools, health-monitoring daemons, automatic
failover, the web UI / HTTP API, environment staging, and migration tooling. They are
excluded on purpose to keep the contract small and the implementation a few files.
Re-introduce only with a documented reason.

## 12. Technology

- **Language**: Python 3.10+
- **State**: SQLite (WAL mode), single source of truth.
- **Projection**: Markdown, one-way out.
- **Loop**: `core.md`, agnostic, over the CLI + text interfaces.
- **Runner (now)**: Claude. **Later (pluggable)**: Devin, Codex.
