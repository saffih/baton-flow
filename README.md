# Baton Flow

Context, intent, and decisions that survive every handoff between AI sessions.

Baton Flow keeps work continuous across AI-assisted sessions. You create tasks; a
**runner** (an AI session — Claude now, Devin/Codex later — or you) picks one up and
writes everything it learns onto a **baton**, a per-task document that travels from
runner to runner so nothing is lost. When a runner can't finish — it needs a human
call, or the work must be split — it **hands off** and moves to the next task. The work
waits; the session never idles.

The design is the single source of truth: see **[HLD.md](HLD.md)**.

## Status

Design phase. No implementation yet — `HLD.md` defines the model, the agnostic
CLI + markdown contract, the task lifecycle, and the human-in-the-loop escalation rules.
