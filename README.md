# Baton Flow

Context, intent, and decisions that survive every handoff between AI sessions.

Baton Flow keeps work continuous across AI-assisted sessions. You create tasks; a
**runner** (an AI session, or you) picks one up and
writes everything it learns onto a **baton**, a per-task document that travels from
runner to runner so nothing is lost. When a runner can't finish — it needs a human
call, or the work must be split — it **hands off** and moves to the next task. The work
waits; the session never idles.

It exists to kill three specific pains:

1. **Context loss** between AI sessions on multi-step work.
2. **No visibility** into what the AI is doing while it works.
3. **No way to steer** without starting over.

The baton solves all three: it *is* the durable context, it's readable at any moment,
and you steer by replying to it.

The design is the single source of truth: see **[HLD.md](HLD.md)**.

## Scope boundary

There is no exclusion list. Capabilities like a web UI, HTTP API, Unix sockets, daemons,
worker pools, environment staging, or migration tooling are **allowed candidates**, not
product limits (HLD-017) — their absence today is current implementation status, not
intent. One boundary rule governs any expansion (HLD-011): no interface or infrastructure
may bypass or weaken baton/context integrity, durable task state, stable IDs, explicit
references, escalation traceability, session/log links, copy-pasteable context, or human
authority over decisions. Candidates are adopted deliberately via an HLD amendment, never
by accretion.

## Layout

- **[HLD.md](HLD.md)** — the design (single source of truth).
- **[core.md](core.md)** — the agnostic loop a runner executes (CLI + markdown only).
- **flow.py** — the runtime: SQLite source of truth, all CLI verbs, markdown projection.
- **test_flow.py** — lifecycle, fork-join, escalation, and reopen tests.

## Usage

The commands below reflect the **currently implemented** surface. `HLD.md` states the
target design, which is ahead of the runtime in places (concurrent escalations,
`answer`/`feedback`, mandatory named sessions, reports); HLD-017 records that gap.

```bash
flow() { python3 flow.py "$@"; }   # or: chmod +x flow.py && ./flow.py …

flow add "Ship login page"            # -> 1   (pending)
flow split 1 "Build form" "Wire auth" # parent parks; children 2,3 pending
flow next --assignee me               # claim the next runnable task
flow context 2                        # read its baton
flow note 2 "using the shared form component"
flow escalate 2 "OAuth or password?"  # park on a human; runner moves on
flow reply 2 "OAuth"                  # (human) answer -> task wakes
flow done 2 "form built with OAuth"   # rejected if deps unmet
flow list
```

State lives in `.flow/flow.db`; human-readable batons are projected to `.flow/batons/`.

Run the tests with `pytest`.
