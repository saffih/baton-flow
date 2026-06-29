# core.md — the runner loop

This is the loop a **runner** executes. It is **agnostic**: it speaks only to the
`flow` CLI and to text. It never assumes which AI is running it —
any runner executes this same file; runners differ only in how they are launched and handed
this loop. Do not access the database directly. Use only the verbs below.

## Loop

Repeat forever:

1. **Claim work** — `flow next --session <me>`. If it prints `none`, wait and retry.
   The session must never idle on a blocked task: claim the next runnable one instead.
2. **Read the baton** — `flow context <id>`. This is the task's full declared context,
   including any human `reply`. Always read it before acting.
3. **Work the task.** Append findings as you go: `flow note <id> "<progress>" --session <me>`.
   Record real choices: `flow decide <id> "<decision>" --session <me>`.
4. **Hand off when you must** — instead of guessing:
   - **Ambiguity** — two valid readings → `flow escalate <id> "<question>" --session <me>`.
   - **Authority** — a call only the human can make (direction, credentials, spend) →
     `flow escalate <id> "<question>" --session <me>`.
   - **Irreversibility** — delete / deploy / external send / money → `flow escalate`
     to confirm first.
   - **Repeated failure** — ~3 tries, still failing → `flow escalate <id> "<question>" --session <me>`, don't thrash.
   - **Too big to do now** — `flow split <id> "<child A>" "<child B>" … --session <me>`.
     The parent parks until the children finish. Children inherit the parent's
     `label`; `--session` here verifies your ownership of the parent only.
   After any handoff the task is `blocked`; go back to step 1.
5. **Finish** — `flow done <id> "<outcome>" --session <me>`. (Rejected if the task still
   has unmet dependencies; resolve or hand off first.)

## On a woken task (a reply arrived, or children finished)

When `flow next` hands you a previously-parked task, re-read the baton and decide:

A reply is already on the baton and the escalation has been resolved. A reply **about this
task** means continue this task; a reply about anything else becomes a **new related
task** that you create explicitly with `flow add` (HLD-007).

- The reply is **about this task** → continue and finish it.
- The reply is **new scope** → `flow add "<new task>" --session <me>`, then finish, continue, or re-park this one explicitly.
- The work is now **moot** → `flow done <id> "<why it's already resolved>" --session <me>`.

Waking is a decision, not an obligation.

## Rules

- Use **only** these verbs; never touch the database.
- Always pass the same `--session <me>` you claimed with on state-changing CLI verbs:
  `add`, `next`, `note`, `done`, `escalate`, `split`, `decide`, `reply`, and `reopen`.
  `--assignee <me>` remains a temporary compatibility alias. If you went silent and your
  task was reclaimed by another session, ownership-implying verbs are refused — you no
  longer hold it (HLD-014). Re-claim with `flow next` instead.
- Use `flow add "<task>" --label <label> --session <me>` to group tasks by subject (component, feature, topic).
  A session that claims a labeled task binds to that label and prefers it on future
  pickups (HLD-010).
- Never guess past a handoff trigger — escalate.
- Communicate every meaningful step on the baton; it is the only context the next
  runner inherits.
