# core.md — the runner loop

This is the loop a **runner** executes. It is **agnostic**: it speaks only to the
`flow` CLI and to text. It never assumes which AI is running it —
any runner executes this same file; runners differ only in how they are launched and handed
this loop. Do not access the database directly. Use only the verbs below.

## Loop

Repeat forever:

1. **Claim work** — `flow next --session <me>`. Name your session; the name is how the
   system knows you (it binds your label affinity and fences your handoffs). If it prints
   `none`, wait and retry. The session must never idle on a blocked task: claim the next
   runnable one instead.
2. **Read the baton** — `flow context <id>`. This is the task's full declared context,
   including any human answers already given. Always read it before acting. The markdown
   files the system writes are a derived, read-only view of the same baton — never write
   them; write through the verbs.
3. **Work the task.** Append findings as you go: `flow note <id> "<progress>"`.
   Record real choices: `flow decide <id> "<decision>"`.
4. **Hand off when you must** — instead of guessing:
   - **Ambiguity** — two valid readings → `flow escalate <id> "<question>"`.
   - **Authority** — a call only the human can make (direction, credentials, spend) →
     `flow escalate`.
   - **Irreversibility** — delete / deploy / external send / money → `flow escalate`
     to confirm first.
   - **Repeated failure** — ~3 tries, still failing → `flow escalate`, don't thrash.
   - **Too big to do now** — `flow split <id> "<child A>" "<child B>" … --session <me>`.
     The parent parks until the children finish. Children inherit the parent's
     `label`; `--session` here verifies your ownership of the parent only.
   Distinct concerns are distinct escalations: a task may hold several open at once —
   escalate each question separately rather than bundling unrelated needs into one.
   After any handoff the task is `blocked` and unassigned (its label is kept); go back
   to step 1.
5. **Finish** — `flow done <id> "<outcome>" --session <me>`. The outcome is mandatory:
   the task's own account of what it did, how, and why. Any size — a long outcome is
   still an outcome. (Rejected if the task still has unmet dependencies — an open
   escalation or an unfinished child; resolve or hand off first.)

## On a woken task (answers arrived, or children finished)

A parked task wakes only when **every** dependency is resolved — all its open escalations
answered, all its children finished. It comes back unassigned, so you claim it through
`flow next` like any other task. Re-read the baton and decide:

The human's replies are already on the baton and their escalations are resolved. A reply
**about this task** means continue this task; a reply about anything else becomes a
**new related task** that you create explicitly with `flow add`.

- The reply is **about this task** → continue and finish it.
- The reply is **new scope** → `flow add "<new task>"`, then finish, continue, or re-park this one explicitly.
- An answer resolved only **part** of what you asked → re-escalate the remainder as its
  own escalation; completeness is your judgment.
- The work is now **moot** → `flow done <id> "<why it's already resolved>"`.

Waking is a decision, not an obligation.

## Rules

- Use **only** these verbs; never touch the database, and never write the markdown
  projections — they are derived output.
- Always pass the same `--session <me>` you claimed with on `escalate`, `split`, and
  `done`. If you went silent and your task was reclaimed by another session, these verbs
  are refused — you no longer hold it (HLD-014). Re-claim with `flow next` instead.
- Use `flow add --label <label>` to group tasks by subject (component, feature, topic).
  A session that claims a labeled task binds to that label and prefers it on future
  pickups (HLD-010).
- To revisit **done** work, the norm is a new task that references it (supersede via
  `flow add`), not resurrecting the old one — in-place reopening is the rare human/ops
  path.
- Never guess past a handoff trigger — escalate.
- Communicate every meaningful step on the baton; it is the only context the next
  runner inherits, and the deliverable comes out only as good as the context you leave.
