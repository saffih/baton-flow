# Flow + HLDspec — Assessment & Path Forward

_Date: 2026-05-26. Based on a first real end-to-end run of HLDspec on `flow-hld.md`,
a from-scratch Flow implementation, and two independent agent reviews._

---

## TL;DR

- **HLDspec is a pre-flight analysis + gating engine, not a code generator.** Its
  "HLD → SpecKit → implementation" promise stops at "HLD → analysis artifacts + a
  markdown prompt + a human gate." SpecKit is **never actually invoked**. Reaching
  `ALL_FEATURES_COMPLETE` only required pre-filling a JSON state file — the
  completion is hollow by design.
- **Flow (this build) is a solid prototype, not production-ready.** The data/CLI/HTTP/
  storage substrate works and is tested (45 passing tests). The defining half — the
  AI agent loop (`core.md`) and session spawning — is not built.
- **A canonical Flow likely already exists** at `/home/sio/flow/` (the HLD references
  that path throughout and cites line numbers of a `cli.py` far larger than anything
  here). This HLD reads as reverse-engineered documentation of that existing system.

---

## 1. Do we understand Flow? — Yes

Flow is a web app where an AI agent (Devin) processes tasks through an 8-step loop,
maintaining context in WIP documents. Architecture:

- **TEA pattern**: Model = SQLite (single source of truth); View = markdown projection
  + web UI; Update = event-driven state changes.
- **Database API** is the exclusive data layer (no direct DB access).
- **CLI** is the only AI-to-system channel (`flow <entity> <action> …`).
- **core.md** is a blocking rules file that drives the Devin execution loop.
- **One-way sync**: DB → markdown only.
- Multi-session execution with task reservation, health monitoring, failover.

## 2. Does it work? — The substrate does; the product half doesn't

| Layer | Status | Evidence |
|---|---|---|
| Database API (7 tables, atomic reserve, whitelisting) | ✅ Works, tested | 16 DB tests pass |
| CLI (`add/list/get/update/mark/reserve/release/sync/serve/status/health`) | ✅ Works | 8 CLI tests; manual e2e |
| HTTP API + Web UI | ✅ Works | 12 API tests; live curl + browser HTML |
| Storage API + markdown projection | ✅ Works, tested | 7 storage tests |
| Env staging (FLOW_ENV prod/test/dev) | ✅ Works | config tests |
| **core.md 8-step AI loop (HLD-011/012)** | ❌ Not built | the product's reason to exist |
| **Session spawning + health/failover (HLD-015/024)** | ❌ Register/list only | no spawn, no liveness |
| Connection pooling (HLD-019 v2.9) | ❌ Not built | per-call connect only |
| SSE real-time events (HLD-017) | ❌ Not built | UI polls every 5s |
| FTS search, conflict/decision tables | ❌ Not built | — |

## 3. What's missing / what to fix in Flow

**Correctness bugs found (this build):**
1. `metadata_json` is never JSON-encoded (only `metadata` is) — `database.py:495`.
2. Retry/backoff is in the wrong place — wraps `connect()`, not `execute()`, so lock
   contention isn't actually retried — `database.py:78`.
3. `ThreadingHTTPServer` + a shared `:memory:` connection will raise across threads
   (`check_same_thread`). File-backed prod is mostly safe but has no pool.
4. The CLI `_kv_options` REMAINDER parser turns a bare `--flag` (no value) into `True`,
   which can be written to the DB — latent data corruption — `cli.py:32`.
5. No explicit transaction rollback; `*` CORS + no auth on the HTTP server.

**Top 5 to reach production:**
1. Build the core.md AI loop + session spawning (the actual product).
2. Fix concurrency: per-thread connections or a real pool; move retry to `execute()`.
3. Replace the REMAINDER/`_kv_options` hack with proper per-subcommand argparse.
4. Add auth + rate limiting; stop binding `*` CORS before exposing the server.
5. Add `tasks_fts`, conflict/decision tables, SSE, and the missing CLI verbs
   (`read status`, `get-wip`, `append-wip`, `notify`, `check-budget`, `list --wait`).

## 4. What to fix in HLDspec

**Three blocking bugs hit on first real run — all in seams, proving the chain had
never been run end-to-end:**
1. Skeptic cache files archived but still required by `write_skeptic_cache.py` →
   immediate crash. _(fixed: 7f6a2b0)_
2. Prework wrote the invocation queue before the dependency graph it depends on, so a
   strict `mtime >` staleness check blocked every rerun forever. _(fixed: 7f6a2b0)_
3. `approval_gate.py` always returned STOP and never read its own approval record —
   structurally unable to advance. _(fixed: d77b078)_

**Root cause: the test strategy gives false confidence.** 303 `tests_v2` tests pass in
0.5s — all unit-level, stubbing `.specify/sync/*.json` fixtures per machine. The
"e2e" test (`tests/test_e2e_hld_to_specify.py`) explicitly does **not** invoke real
SpecKit. No test runs `ProjectMachine` through the full chain.

**The handoff is stubbed by design.** `speckit_execution.py` only reads `*_decision`
keys from a state file and advances an index; `hldspec_invoke_speckit_feature.py` just
writes a prompt `.md`; `hldspec_speckit_proxy.sh` forces `DRY_RUN=1`. No `specify` /
`/speckit.*` / subprocess call exists anywhere.

**What should change:**
1. Make the execution machine actually shell out to the `specify` CLI per feature
   (via the existing `CommandRunner`), capturing exit codes + generated spec paths.
2. Derive phase `COMPLETE` from **artifacts SpecKit produced** (spec file exists,
   non-empty), never from a human-written JSON key.
3. Add a real integration test: run `ProjectMachine.run()` from a fixture HLD to
   execution with SpecKit faked by an injectable stub binary; assert specs land on
   disk. This single test would have caught all three bugs.
4. Fix the staleness contract itself (`>=` or content hashes), don't reorder writes
   around a microsecond-fragile `>` — bug 2 will recur otherwise.
5. Add a first-run preflight that verifies required operational files exist before
   crashing mid-pipeline.

## 5. Are we production-ready? — No, on both counts

- **HLDspec**: a capable upstream analysis engine with a non-functional downstream
  handoff. Prototype.
- **Flow (this build)**: a clean, tested substrate missing its AI-orchestration half.
  Prototype.

## 6. Making HLD → SpecKit → implementation actually work

1. **Decide the source of truth for implementation.** If `/home/sio/flow/` already
   exists, the goal is *alignment/migration*, not greenfield. Locate it first.
2. **Wire SpecKit for real** (HLDspec change #1–2 above) so the pipeline produces spec
   files, then run `/speckit.implement` to generate code — or have an agent implement
   from the generated specs.
3. **Gate on real artifacts, not state flags**, end to end. "Complete" must mean files
   exist on disk.
4. **Add one true integration test per tool** before trusting either again.

---

_Flow build status: tasks 1–7 of 8 done (substrate + tests). Task 8 (AI loop +
sessions) pending — that's the product's core and the largest remaining effort._
