# Label / Sessions Roadmap

What's built (HLD-010, shipped): a task has an optional `label`; a named session
(`flow next --session X`) binds to the label of its first labeled task, prefers that
label, falls back rather than idle; `assignee` records the holder; `sessions(name,
bound_label)` stores the binding. Claim is atomic (HLD-013).

This roadmap is the remaining label/session work, in dependency order.

## Slice 1 — HLD-014: orphaned-work recovery (lease + reclaim + fence)  [HIGH, next]

The correctness base (HLD-013) is done; this adds **liveness**: a session can claim a
task then vanish, stranding it `in_progress` forever.

- **Lease.** A claim's `updated_at` is its lease stamp; `note` refreshes it. A task
  `in_progress` past `LEASE_TTL` (a constant) is *orphaned*.
- **Reclaim — lazy, no daemon** (HLD-011 forbids daemons). Inside `next_task` (and an
  explicit `flow sweep`), before selecting: orphaned tasks → `pending`, append
  `reclaimed: session X silent since T`, bump `reclaim_count` (one new column).
- **Escalate-on-repeat.** After K reclaims, escalate instead of re-queue — reuses the
  existing escalation primitive (HLD-006 "repeated failure").
- **Fence — ownership-implying transitions only.** `done` / `escalate` / `split` verify
  `assignee == caller-session` and `state == in_progress`; otherwise reject
  (`you no longer hold task N`). This needs those verbs to carry `--session`.
- **Blackboard stays multi-writer.** `note` / `decide` / `reply` are NOT fenced — they
  get *attribution* (record who wrote), per the baton model (HLD-008). Fencing them
  would break the blackboard.
- **Schema:** + `reclaim_count INTEGER DEFAULT 0` on tasks; lease reuses `updated_at`.
- **HLD-VERIFY:** a silent session's task is reclaimed or (after K) escalated; a stale
  session cannot `done`/`escalate`/`split` a task it no longer holds; `note`/`decide`/
  `reply` remain multi-writer.
- **Tests:** orphan reclaimed; reclaimed task re-claimed by another session; repeated
  reclaim → escalate; fenced verb rejects stale owner; blackboard writes not fenced;
  `note` refreshes the lease (no premature reclaim).

## Slice 2 — session lifecycle / visibility  [MEDIUM]

- `flow sessions` — list sessions + bound labels (observability).
- `flow unbind <session>` — clear `bound_label` so a session can re-specialize.
- Decide binding longevity: persist until unbound (default), vs. expire after long idle.
  Lean: persist + explicit unbind; revisit only if a real need appears.

## Slice 3 — capability routing & must-halt (HLD-010 "Future")  [LOW, on demand]

- **Capability routing** needs no new mechanism — a `label` already lets "cheap model for
  db, strong for arch" fall out by which runner takes which `--session`. Convention, not code.
- **Must-halt:** a tag making a session wait on a specific task instead of parking it —
  one field + a `next` variant. Add only when a concrete need appears.

## Sequencing note

Build Slice 1 (HLD-014) next — it's the protection-completing liveness layer and the
only HIGH-risk item. Slices 2–3 are pull-based: add when observability or capability
routing is actually needed, not speculatively.

## HLD-014 — RunSkeptic revisions (settle before coding)

Two gating decisions:
- **Heartbeat:** lease = silence since last `note`, NOT session liveness. Decide:
  require runners to `note` as a heartbeat, or accept quiet-reclaim as a documented
  tradeoff. (FE:ME)
- **Fence enforcement (CONFLICT):** require `--session` on `done`/`escalate`/`split`
  (safe, breaks single-runner back-compat) vs optional-but-fence-only-when-present
  (compatible, has a bypass hole). (KT:IR/SH:HC)

Fixed constraints:
- Reclaim targets `in_progress` ONLY — `blocked` is parked by design, not orphaned. (PO:CN)
- Reclaim runs atomically under the claim's `BEGIN IMMEDIATE`; TTL generous. (CH:IV)
- Index `(state, updated_at)` for the per-`next` sweep. (CH:SR)
- Safety dominates; narrow exception: reclaim only after clear silence.
