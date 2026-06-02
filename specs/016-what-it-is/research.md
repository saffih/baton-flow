# Research: What It Is (HLD-001)

**Branch**: `016-what-it-is` | **Date**: 2026-06-03

No external research required — this is a documentation spec. Findings from reading
current `README.md` and `core.md` against the spec's FRs:

## Current-State Gap Analysis

| FR | Requirement | Current State | Delta |
|----|-------------|---------------|-------|
| FR-001 | Baton defined in plain language | ✅ README.md defines "baton" | None |
| FR-002 | Three pains named explicitly | ⚠ Not enumerated; phrased as benefit, not pain list | Add pain list |
| FR-003 | Two actor types identified | ✅ "you" (human) and "runner" present | None |
| FR-004 | All CLI verbs enumerated with descriptions | ✅ Usage block in README; core.md lists all verbs | None |
| FR-005 | Binary reply rule stated explicitly | ⚠ core.md covers the cases but doesn't state the routing rule in one sentence | Strengthen |
| FR-006 | escalate/split described as same primitive | ✅ core.md: both park as blocked, runner moves on | None |
| FR-007 | Stripped-scope boundaries stated | ⚠ Not mentioned in README or core.md | Add section |
| FR-008 | No specific AI named | ❌ README.md: "a runner (an AI session — **Claude now, Devin/Codex later** — or you)" | Fix: remove named AIs |

## Critical Finding

**README.md names specific AI systems** (`Claude`, `Devin`, `Codex`). This violates
HLD-003/HLD-009 (Principle III) and the existing `test_ai_agnostic_core` test in
`test_flow.py`. The test checks `core.md` only — README.md is currently unguarded.

## Decisions

- **FR-008 fix**: Replace the named-AI clause in README.md with "an AI session, or you".
  Scope: README.md only (core.md is already compliant).
- **FR-002 fix**: Add an explicit "three pains" paragraph to README.md, matching HLD-001
  prose verbatim to stay faithful to the source.
- **FR-005 fix**: Add a one-sentence binary reply rule to the "On a woken task" section
  in core.md: the decision criteria are there, but the rule as a named invariant is absent.
- **FR-007 fix**: Add a brief "What it is not" section to README.md citing HLD-011's
  stripped-scope list.
- **Test guard**: The `test_ai_agnostic_core` test guards `core.md`. Extend it (or add
  a peer test) to also assert README.md contains no named AI systems, so this can't regress.
