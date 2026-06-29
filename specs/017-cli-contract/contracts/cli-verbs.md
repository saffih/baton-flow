# CLI Verb Contract — HLD-009

**Source**: HLD-009 / HLD-013 (amended to add maintenance verbs)
**HLD-VERIFY**: runners use only the listed implemented verbs with no direct
database access; reply/list/reopen and persistence maintenance verbs are
human/ops-facing and not part of the runner loop

---

## Runner Verbs (8)

These are the only verbs a runner may call. No exceptions.
State-changing runner verbs require `--session <id>` at the CLI boundary.
`--assignee <id>` remains a temporary compatibility alias. `flow context` is
read-only and remains exempt.

| Verb | Arguments | Effect |
|---|---|---|
| `flow add` | `<text> --session <id>` | Create a new pending task |
| `flow next` | `--session <id>` | Claim the next runnable task; returns "none" if none exist |
| `flow context` | `<id>` | Read the task's baton |
| `flow note` | `<id> <text> --session <id>` | Append progress/finding to the baton |
| `flow done` | `<id> <outcome> --session <id>` | Complete with stated outcome; rejected if unfinished children |
| `flow escalate` | `<id> <question> --session <id>` | Park task blocked on a human |
| `flow split` | `<id> "child A" "child B" … --session <id>` | Spawn children; park parent |
| `flow decide` | `<id> <decision> --session <id>` | Record a decision on the baton |

---

## Human/Ops Verbs (3)

Not part of the runner loop. Runners MUST NOT call these.
State-changing human/ops verbs still require `--session <id>` for accountability.

| Verb | Arguments | Effect |
|---|---|---|
| `flow reply` | `<id> <text> --session <id>` | Answer a blocked task; appends to baton; wakes task to pending |
| `flow reopen` | `<id> --session <id>` | Move a done task back to pending |
| `flow list` | _(none)_ | List all tasks with current state. Read-only; never changes state |

---

## Operator Maintenance Verbs (2)

Operator-facing persistence maintenance. Not part of the runner loop; never
transitions task state.

| Verb | Arguments | Effect |
|---|---|---|
| `flow backup` | `<path>` | Write a SQLite-safe backup snapshot. Read-only against task state |
| `flow check` | _(none)_ | Run SQLite `PRAGMA integrity_check`. Read-only |

---

## Invariants

- Total verb count: 13 (8 runner + 5 human/ops/maintenance)
- No direct database access by any runner
- State-changing CLI verbs require `--session`; `--assignee` is a compatibility alias
- `context`, `list`, `backup`, and `check` remain exempt from session enforcement
- `flow add` is dual-use: primary human creation verb AND runner off-topic reply branch
- `flow list` is read-only: it never transitions state
- `flow backup` and `flow check` never transition task state
