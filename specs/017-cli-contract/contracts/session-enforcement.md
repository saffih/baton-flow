# Mandatory Session Enforcement — Implemented Contract

**Source**: HLD-009, HLD-010, HLD-014, HLD-015
**Status**: Implemented at the CLI boundary
**Scope**: Defines which CLI verbs require named sessions, which verbs remain exempt, and
how `--session` / `--assignee` compatibility works.

---

## Active policy

State-changing CLI verbs require a named session before dispatch. Read-only and
maintenance verbs do not.

| Category | Verbs | Session required |
|---|---|---|
| Runner state-changing | `add`, `next`, `note`, `done`, `escalate`, `split`, `decide` | Yes |
| Human/ops state-changing | `reply`, `reopen` | Yes |
| Read-only | `context`, `list` | No |
| Operator maintenance | `backup`, `check` | No |

The required session flag is `--session <name>`. `--assignee <name>` remains a temporary
compatibility alias. Supplying both flags with different values is rejected.

## Boundary

Enforcement lives at the CLI boundary after argument parsing and before verb handler
execution. It is not an ownership check and must not be scattered across individual verb
handlers.

Internal Python API calls remain outside this CLI authorization boundary. Those
compatibility paths do not grant runner CLI permission; they are library/test surfaces.

## Exemptions

`context`, `list`, `backup`, and `check` are exempt because they do not transition task
state. `backup` and `check` are operator maintenance verbs; they must stay available
without session ceremony for persistence safety.

The previous broader "CLI-entry enforcement for every call, reads included" wording is not
the active implementation contract. Adopting reads-included/all-calls enforcement would
require a future HLD decision with explicit rationale for `context`, `list`, `backup`, and
`check`.

## Still Deferred

- `flow reclaim` remains deferred; lazy lease-TTL reclaim inside `flow next` is the
  implemented recovery path.
- `flow reply` remains the implemented answer path; `reply` -> `answer` naming alignment is
  still a separate decision.
- Removing the `--assignee` compatibility alias is not part of this contract.
