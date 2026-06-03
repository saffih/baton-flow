# CLI Verb Contract — HLD-009

**Source**: HLD-009 (amended 2026-06-03 to add `flow list`)
**HLD-VERIFY**: runners use only the listed verbs; no direct database access;
reply, reopen, and list are human/ops-facing and not part of the runner loop

---

## Runner Verbs (8)

These are the only verbs a runner may call. No exceptions.

| Verb | Arguments | Effect |
|---|---|---|
| `flow add` | `<text>` | Create a new pending task |
| `flow next` | `[--assignee <id>]` | Claim the next runnable task; returns "none" if none exist |
| `flow context` | `<id>` | Read the task's baton |
| `flow note` | `<id> <text>` | Append progress/finding to the baton |
| `flow done` | `<id> <outcome> [--assignee <id>]` | Complete with stated outcome; rejected if unfinished children |
| `flow escalate` | `<id> <question> [--assignee <id>]` | Park task blocked on a human |
| `flow split` | `<id> "child A" "child B" … [--assignee <id>]` | Spawn children; park parent |
| `flow decide` | `<id> <decision> [--assignee <id>]` | Record a decision on the baton |

---

## Human/Ops Verbs (3)

Not part of the runner loop. Runners MUST NOT call these.

| Verb | Arguments | Effect |
|---|---|---|
| `flow reply` | `<id> <text>` | Answer a blocked task; appends to baton; wakes task to pending |
| `flow reopen` | `<id>` | Move a done task back to pending |
| `flow list` | _(none)_ | List all tasks with current state. Read-only; never changes state |

---

## Invariants

- Total verb count: 11 (8 runner + 3 human/ops)
- No direct database access by any runner
- `flow add` is dual-use: primary human creation verb AND runner off-topic reply branch
- `flow list` is read-only: it never transitions state
