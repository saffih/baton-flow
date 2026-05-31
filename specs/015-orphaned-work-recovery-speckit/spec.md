# Feature Specification: Orphaned-Work Recovery (Lease, Reclaim, Fence)

**Feature Branch**: `015-orphaned-work-recovery-speckit`

**Created**: 2026-05-31

**Status**: Draft

**Input**: User description: "Build Orphaned-work recovery (lease, reclaim, fence) for the Baton Flow task runtime — HLD anchor HLD-014. A named session can claim a task then vanish, stranding it in_progress forever. Recovery is a liveness concern: a lease, lazy reclaim inside `flow next`, escalate after repeated reclaim, and an ownership fence on the verbs that imply completion."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Stranded work is recovered automatically (Priority: P1)

A worker takes a piece of work and then disappears — its process crashes, its
connection drops, or it is simply abandoned — without finishing it, asking for help,
or breaking it into pieces. That work must not stay "in progress" forever. After the
worker has been silent for longer than a generous grace period, the next worker who
asks for work finds that abandoned item returned to the available pool, with a note
explaining it was recovered from a silent worker.

**Why this priority**: This is the entire purpose of the feature. Without it, one
vanished worker permanently strands a task and no one is alerted — work is silently
lost. It stands alone as a complete, demonstrable capability and delivers the core
value on its own.

**Independent Test**: Have a named worker take an item, let its grace period lapse with
no further activity, then have any worker ask for the next item. Confirm the item is
available again, carries a recovery note naming the silent worker and when it went
silent, and that its recovery count went up by one.

**Acceptance Scenarios**:

1. **Given** an in-progress item whose holding worker has been silent beyond the grace
   period, **When** any worker asks for the next item, **Then** the item is returned to
   the available pool, a note recording "recovered from worker X, silent since T" is
   added to its record, and its recovery count is incremented — all before any item is
   handed out.
2. **Given** an in-progress item whose holder has been active within the grace period,
   **When** a worker asks for the next item, **Then** the item is NOT recovered and stays
   with its current holder.
3. **Given** a parked item that is waiting on a human answer or on child items, **When**
   it has been idle past the grace period, **Then** it is NOT recovered — only actively-
   held work is subject to recovery; deliberately parked work is left alone.
4. **Given** an in-progress item whose holder records progress within the grace period,
   **When** a worker later asks for the next item, **Then** the recorded progress counts
   as a sign of life and the item is NOT recovered.

### User Story 2 - A returning, displaced worker cannot corrupt moved-on work (Priority: P2)

A worker's item was recovered and may now be held by someone else. The original worker
comes back — unaware it lost the item — and tries to complete it, escalate it, or break
it into sub-items. Because it no longer holds that item, each of those actions is
refused with a clear explanation, so a returning ghost cannot overwrite or restructure
work that has already moved on.

**Why this priority**: Recovery (Story 1) creates the possibility that two workers each
believe they own one item. Without this guard, the stale worker could mark work
"done" or restructure it while another worker is actively redoing it — corrupting the
outcome. It protects the integrity of recovery, but recovery delivers value before it
exists, so it is P2.

**Independent Test**: Have worker A take an item, recover it to worker B, then have A
attempt to complete, escalate, and split it. Confirm each attempt is refused with a
clear "you no longer hold this item" message and the item is unchanged. Separately,
confirm an item taken without a named worker (the established simple path) still accepts
those same actions unchanged.

**Acceptance Scenarios**:

1. **Given** an item now held by worker B, **When** worker A tries to complete it,
   **Then** the attempt is refused with a message stating A no longer holds the item, and
   the item's state is unchanged.
2. **Given** an item held by a named worker, **When** a different worker tries to escalate
   or split it, **Then** each attempt is refused with the same clear message.
3. **Given** an item held by worker A, **When** worker A itself completes, escalates, or
   splits it, **Then** the action succeeds.
4. **Given** an item that was taken without any named worker (the existing simple path),
   **When** it is completed, escalated, or split, **Then** the action is accepted exactly
   as before this feature — the guard applies only to work held by a named worker.
5. **Given** any item, **When** any participant adds a note, records a decision, or posts
   a reply to it, **Then** the action is always accepted and attributed — these shared
   running-record actions are never guarded.

### User Story 3 - Chronically-abandoned work is raised to a human (Priority: P3)

An item keeps being taken and abandoned, cycling through recovery after recovery —
perhaps it is poison work that crashes whoever takes it. Rather than recirculate it
forever, after it has been recovered a set number of times the system stops requeuing
it and instead raises it for a human to look at, reusing the same "needs a human"
path used elsewhere for repeated failure.

**Why this priority**: This prevents endless thrashing on a pathological item. It only
matters once recovery exists and only fires after repeated recoveries, so it is the
lowest-priority of the three while still independently testable.

**Acceptance Scenarios**:

1. **Given** an item whose recovery count is below the limit, **When** it is found
   abandoned again, **Then** it is returned to the available pool as in Story 1.
2. **Given** an item that has reached the recovery limit, **When** it is found abandoned
   again, **Then** instead of recirculating it is parked for human attention via the
   existing escalation path.

### Edge Cases

- An item silent for less than the grace period is never recovered, even with no activity
  since it was taken.
- A parked (waiting) item is never recovered regardless of how long it has been idle.
- Two workers asking for work at the same moment must never both recover-and-take the
  same abandoned item; it is handed to at most one.
- Only progress and decisions by the holder count as signs of life; a human reply or a
  read of the item does not.
- An item taken without a named worker is never guarded and behaves exactly as before.

## Requirements *(mandatory)*

### Functional Requirements

**Sign-of-life (lease)**

- **FR-001**: The system MUST treat the time of an item's last change as its sign-of-life
  marker.
- **FR-002**: The system MUST refresh that marker whenever the holder records progress or
  a decision on the item.
- **FR-003**: The system MUST consider an actively-held item *abandoned* when its marker
  is older than a single, generous grace period, with no requirement that workers send
  periodic check-ins — silence alone, not a missing check-in, defines abandonment.

**Recovery**

- **FR-004**: The system MUST detect and recover abandoned items only at the moment a
  worker asks for the next item, before any item is selected — there is no always-on
  background process performing recovery.
- **FR-005**: The system MUST recover only actively-held items; deliberately parked items
  (waiting on a human or on child items) MUST never be recovered.
- **FR-006**: On recovery, the system MUST return the item to the available pool and
  detach it from the vanished worker so it can be taken by anyone.
- **FR-007**: On recovery, the system MUST add a note to the item recording that it was
  recovered, which worker had held it, and since when.
- **FR-008**: On recovery, the system MUST increase the item's recovery count by one.
- **FR-009**: Concurrent requests for the next item MUST never recover-and-hand-out the
  same abandoned item more than once.

**Escalation on repeat**

- **FR-010**: When an item has been recovered a configured number of times, the system
  MUST raise it for human attention instead of returning it to the pool again, reusing
  the existing "needs a human" path.

**Ownership guard (fence)**

- **FR-011**: For an item held by a named worker, the system MUST refuse a complete,
  escalate, or split request that does not come from the holding worker, and MUST state
  plainly that the requester no longer holds the item.
- **FR-012**: The system MUST NOT apply the ownership guard to items taken without a named
  worker; those continue to behave exactly as before this feature, and asking for the
  next item without naming a worker is unchanged.
- **FR-013**: The system MUST NOT guard the shared running-record actions (adding a note,
  recording a decision, posting a reply); these remain open to all participants and are
  attributed to whoever performs them.

**Configurable thresholds**

- **FR-014**: The grace period before an item is considered abandoned MUST be a single
  configurable value, defaulting to one hour.
- **FR-015**: The number of recoveries before an item is raised to a human MUST be a
  configurable value, defaulting to three.

### Key Entities *(include if feature involves data)*

- **Work item**: the unit being recovered. Relevant facts: whether it is actively held vs
  parked (only actively-held is recoverable), its sign-of-life marker, which named worker
  holds it (if any), and how many times it has been recovered.
- **Sign-of-life marker**: the time of the item's last change, interpreted as a freshness
  window; an actively-held item older than the grace period is abandoned.
- **Recovery count**: a per-item tally, raised on each recovery and compared against the
  limit to decide recirculate-vs-raise-to-human.
- **Named worker**: the identity that holds an item. Whether an item is held by a named
  worker vs taken anonymously determines whether the ownership guard applies.
- **Item record (running record)**: the shared, append-only record carried with each item;
  recovery adds a note to it, and it stays open to notes, decisions, and replies from all.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: No actively-held item stays held past the grace period of silence once any
  worker asks for the next item — it is either returned to the pool or, at the limit,
  raised to a human. (0 permanently-stranded items.)
- **SC-002**: Under simultaneous requests for work, an abandoned item is recovered and
  handed to at most one worker — never duplicated or double-held.
- **SC-003**: An item is never recovered before it has been silent past the grace period,
  and a parked item is never recovered — 0% false recoveries of fresh or parked items.
- **SC-004**: 100% of complete/escalate/split attempts on a named-worker-held item by a
  non-holder are refused; 100% of those same actions on anonymously-taken items are
  accepted unchanged.
- **SC-005**: Shared running-record actions (note, decision, reply) succeed for any
  participant on any item, 100% of the time, with the author attributed.
- **SC-006**: Every recovery leaves an audit trail — the item's record names the prior
  holder and when it went silent, and the recovery count reflects the number of
  recoveries.

## Assumptions

- **Liveness, not correctness**: this feature ensures work does not get stuck. It relies
  on — but does not redefine — the existing guarantee that taking an item is atomic and
  that each operation is all-or-nothing; recovery simply runs within that existing atomic
  "ask for next item" step so it cannot race a simultaneous take.
- **Builds on named workers**: the ownership guard and the notion of "the worker that
  holds an item" depend on the already-established ability to name a worker when asking
  for work.
- **Detaching the holder on recovery**: when an item returns to the pool it is no longer
  attributed to the vanished worker; the source design states it returns to the pool and
  that the prior holder can no longer act on it, and this spec treats the holder as
  detached on recovery.
- **Defaults**: grace period defaults to one hour and the recovery limit to three; both
  are described in the source design as deliberately generous / small and are exposed as
  configuration.

## Out of Scope

- **No background process / no daemon**: recovery happens only when a worker asks for the
  next item. There is no health-monitoring daemon, polling loop, or background sweeper —
  consistent with the design's deliberately excluded operational machinery.
- **No check-in obligation**: workers are not required to send periodic pings or
  heartbeats; silence alone defines abandonment.
- **Redefining atomicity/durability**: the atomic-take and all-or-nothing-operation
  guarantees are owned elsewhere and are not redefined here.
- **Guarding the shared running record**: notes, decisions, and replies are deliberately
  never guarded; restricting them would break the shared running-record model.
- **Recovering parked work**: items waiting on a human or on child items are out of scope
  for recovery by design.
