# Data Model: What It Is (HLD-001)

**Branch**: `016-what-it-is` | **Date**: 2026-06-03

HLD-001 is a documentation spec — no new database schema or persistent data. This
file captures the **canonical vocabulary model**: the four entities that README.md and
core.md must define consistently.

## Canonical Entities

### Task
The unit of work. Has a lifecycle: `pending → in_progress → blocked → done`.
- Created by a human.
- Claimed by a runner via `flow next`.
- Carries a baton.

### Baton
The per-task durable context document. Travels with the task from runner to runner.
- Append-only: notes, decisions, and replies accumulate; nothing is erased.
- Read via `flow context <id>`.
- Lives in the database; markdown projection is read-only.

### Runner
Any agent that executes the runner loop (`core.md`). May be an AI session or a human.
- AI-agnostic: the loop names no specific AI system.
- Interacts with the task exclusively through the published `flow` CLI verbs.
- Does not access the database directly.

### Human
Creates tasks, replies to blocked tasks, and reviews output.
- Steers via `flow reply <id>` (on-topic reply unblocks; off-topic reply becomes a new task).
- Can reopen done tasks.

## Vocabulary Rules for Documentation

- Use "runner" (not "agent", "AI", "Claude", etc.) in all documentation.
- Use "baton" (not "context file", "scratchpad", "log").
- Use "task" (not "ticket", "issue", "work item").
- Use "human" or "you" for the non-runner actor.
