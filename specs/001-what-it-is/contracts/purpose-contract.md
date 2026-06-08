# Purpose Contract: What it is

## Contract

Any product-facing artifact, implementation task, or future behavior derived from spec `001` MUST preserve these statements:

1. Baton Flow exists to produce trustworthy report outputs across AI-assisted sessions.
2. Reports are durable deliverables that accumulate value as work proceeds.
3. Tasks, runners, and baton context are mechanisms that make good reports possible.
4. Baton context is the means, not the final product purpose.
5. Visibility and steering must help the human guide work without restarting.

## Forbidden Drift

- Do not describe Baton Flow as primarily a task queue.
- Do not describe Baton Flow as primarily a baton/context store.
- Do not make the report a secondary byproduct of task processing.
- Do not introduce CLI, persistence, lifecycle, recovery, or routing rules in this spec.

## Verification

- Review `spec.md`, `plan.md`, and `tasks.md` for the five contract statements.
- Reject implementation tasks that change product-facing surfaces without preserving the report-first purpose model.
