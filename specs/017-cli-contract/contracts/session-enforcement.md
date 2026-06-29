# Mandatory Session Enforcement — Design Contract

**Source**: HLD-009, HLD-010, HLD-014, HLD-015
**Status**: Design only — no behavior changes until the implementation PR
**Scope**: Defines the enforcement boundary, verb categorization, migration
path, and test impact for mandatory named sessions

---

## Current state vs target state

| Aspect | Current (root HLD / code) | Target (source HLD) |
|---|---|---|
| Session identity | Preferred; anonymous allowed | Mandatory; no anonymous path |
| Enforcement point | None | CLI entry, reads included |
| `--session` / `--assignee` | `--assignee` is the only tested spelling | `--session` is primary |
| `backup` / `check` | Listed as operator maintenance verbs | Absent from verb table |
| `flow reclaim` | Deferred (lazy lease-TTL only) | Implemented (see-and-act) |
| `flow reply` / `flow answer` | `reply` implemented | `answer` (renamed) |

This document defines the bridge: what the implementation PR must do
to move from current to target, and what it must not break.

---

## Enforcement decisions

### 1. Which commands require a named session?

**Task-state-changing** verbs require a session. Read-only verbs do not.

| Category | Verbs | Session required |
|---|---|---|
| Runner (state-changing) | `add`, `next`, `note`, `done`, `escalate`, `split`, `decide` | Yes — future mandatory |
| Human/ops (state-changing) | `reply`, `reopen` | Yes — future mandatory |
| Read-only | `context`, `list` | **No** — exempt |
| Operator maintenance | `backup`, `check` | **No** — exempt |

**Rationale for read-only / maintenance exemption**: these verbs never change
task state or identity. Requiring a session name for `PRAGMA integrity_check`
or reading a baton adds ceremony with no accountability benefit. The
enforcement boundary is "who changes state," not "who touches the CLI."

**Source HLD divergence (flagged, not adopted here)**: source HLD-009 says
"enforced at the CLI entry… reads included" — a stricter end-state where
every command, including reads, carries a session. This design contract
adopts the user's stated policy ("task-state-changing verbs") as the
implementation target. If the eventual target is reads-included, that is a
separate decision requiring its own rationale for `context`/`list`/`backup`/`check`.

### 2. Is `--assignee` kept as compatibility spelling?

Yes. `--assignee` remains a temporary compatibility alias for `--session`.
The implementation PR should:
- Keep both spellings in argparse
- Document `--session` as primary in cli-verbs.md and core.md
- Not remove `--assignee` until a separate deprecation decision

### 3. What happens to anonymous `flow next`?

Anonymous `flow next` (no `--session`/`--assignee`) **remains allowed** until
the implementation PR intentionally flips enforcement. The current behavior
is explicitly tracked as a gap, not a bug.

Migration path (answers Q7: docs-only → warning → hard error):
1. **Current** (this PR): docs define the contract; behavior unchanged
2. **Implementation PR**: enforcement enabled; anonymous calls raise `FlowError`

The three-phase path (docs → warning → hard error) was considered and
rejected in favor of a two-phase path (docs → hard error). Rationale: the
only callers are automated runners reading `core.md`, not interactive humans
who benefit from deprecation warnings. The contract change in `core.md` is
the notification; a warning phase adds a release cycle of noise with no
human audience to act on it.

### 4. Where is enforcement implemented?

**At the CLI boundary** — a single check in the dispatch path, not scattered
per-verb guards.

```
CLI entry (argparse)
  → dispatch function
    → session presence check  ← enforcement point (single gate)
      → verb handler
```

The implementation PR must NOT:
- Add per-verb `if session is None` checks
- Move enforcement into `_require_owner` (that checks ownership, not presence)
- Scatter enforcement across multiple code paths

The implementation PR SHOULD:
- Add the check after dispatch, before the verb handler
- Exempt read-only and maintenance verbs (`context`, `list`, `backup`, `check`) by verb name
- Raise `FlowError` with a clear message naming `--session`

### 5. Parser shape changes needed

Currently only `next`/`done`/`escalate`/`split` accept `--session`/`--assignee`.
The implementation PR must extend the flag to all state-changing verbs that
don't yet have it: `add`, `note`, `decide`, `reply`, `reopen`.

Read-only verbs (`context`, `list`) and maintenance verbs (`backup`, `check`)
do not need the flag. This is a parser-shape change, not just validation
tightening.

---

## Test impact

### Tests that break by design (6)

These tests assert the anonymous gap is still open. The implementation PR
must flip their assertions from "succeeds" to "raises FlowError":

| Test | Current assertion | After enforcement |
|---|---|---|
| `test_anonymous_claim_recorded_on_baton` | anonymous claim succeeds | must raise |
| `test_unassigned_pool_is_claimable` | anonymous next succeeds | must raise |
| `test_next_without_session_unchanged` | anonymous next returns task | must raise |
| `test_hld010_anonymous_session_path_deferred` | anonymous claim succeeds (gap) | must raise |
| `test_no_session_task_unfenced` | no-session task is unfenced | must raise |
| `test_hld009_session_enforcement_deferred` | enforcement deferred (gap) | must assert enforcement active |

### Tests unaffected (~83)

Read-only verb tests (context, list), maintenance verb tests (backup/check),
named-session tests, routing tests, concurrency tests, HLD invariant tests —
all either already use named sessions or test exempt verbs.

### New tests needed

The implementation PR must add:
- `test_anonymous_next_rejected` — `flow next` without session raises
- `test_anonymous_done_rejected` — `flow done` without session raises
- `test_context_no_session_allowed` — `flow context` without session succeeds
- `test_list_no_session_allowed` — `flow list` without session succeeds
- `test_backup_no_session_allowed` — `flow backup` without session succeeds
- `test_check_no_session_allowed` — `flow check` without session succeeds
- `test_session_flag_accepted_on_state_changing_verbs` — every state-changing verb accepts `--session`

---

## Pre-existing divergences (out of scope for this PR)

These are noted for the implementation PR, not fixed here:

1. **Root HLD.md vs source HLD.md**: root mirror is stale and still describes
   the "preferred/transition" state. Re-materialization is a separate step.
2. **cli-verbs.md / core.md use `--assignee` only**: neither mentions
   `--session` as the primary spelling. Update belongs in the implementation PR.
3. **`flow reply` vs `flow answer`**: source HLD uses `answer`; code uses
   `reply`. Rename is a separate decision tracked in HLD-009.
4. **`flow reclaim` implementation**: source HLD describes it as implemented;
   code defers it. Implementation is a separate HLD-014 decision.

---

## Follow-ups

- [ ] Implementation PR: flip enforcement, update 6 tests, extend parser
- [ ] Re-materialize root HLD.md from source after implementation
- [ ] Decide whether reads-included enforcement (source HLD-009) is the eventual target
- [ ] Update cli-verbs.md `--assignee` → `--session` primary spelling
- [ ] Update core.md session usage examples
- [ ] Decide `reply` → `answer` rename (HLD-009 alignment)
- [ ] Decide `flow reclaim` implementation (HLD-014 alignment)
