# Research: The CLI Contract (HLD-009)

**Purpose**: SC coverage gap analysis before task generation

---

## Existing test coverage — SC mapping

| SC | Requirement | Existing coverage | Gap |
|---|---|---|---|
| SC-001 | Every runner verb has ≥1 isolation test | 47 tests exercise verbs behaviorally; no single grouped isolation test | Need `test_runner_verb_contracts` |
| SC-002 | `reply`/`reopen`/`list` absent from runner-permitted verb set | `test_cli_exposes_only_contract_verbs` guards the 11-verb set; no test checks core.md specifically | Need `test_human_ops_verbs_absent_from_runner_loop` |
| SC-003 | HLD-009 VERIFY invariant cited by ID in ≥1 test | `test_cli_exposes_only_contract_verbs` references HLD-009 in a comment; VERIFY text not cited | Need `test_hld009_verify_invariant` |
| SC-004 | No AI names in verb/arg/output | `test_loop_contract_names_no_specific_ai` covers core.md + flow.py | No gap — COVERED |
| SC-005 | All 47 prior tests green | Baseline — confirmed green | No gap |

---

## core.md verb analysis

`core.md` uses the 8 runner verbs inline in the loop steps:
`flow next`, `flow context`, `flow note`, `flow decide`, `flow done`,
`flow escalate`, `flow split`, `flow add`.

Human/ops verbs `reply`, `reopen`, `list` do NOT appear as `flow <verb>` commands.
The word "reply" appears once as a noun ("any human `reply`") — not as a CLI verb.

**Decision**: SC-002 test can assert `"flow reply"`, `"flow reopen"`, `"flow list"`
are absent from core.md as string literals. This is testable and correct.

---

## Decisions

| Decision | Choice | Rationale |
|---|---|---|
| New test file? | No — add to test_flow.py | All existing tests are in test_flow.py; new file would break the single-file pattern |
| Data model changes? | None | Characterization only; no schema changes |
| flow.py changes? | None | All 11 verbs already implemented correctly |
| core.md changes? | None expected | Already correct; tests verify the existing state |
