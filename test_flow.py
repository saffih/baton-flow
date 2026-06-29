"""Tests for the Baton Flow runtime: lifecycle, fork-join, escalation, reopen."""

import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

import flow


def _age(conn, task_id, seconds):
    """Backdate a task's lease stamp so it looks silent (HLD-014 test helper)."""
    old = (datetime.now(timezone.utc) - timedelta(seconds=seconds)).isoformat(timespec="seconds")
    conn.execute("UPDATE tasks SET updated_at=? WHERE id=?", (old, task_id))


@pytest.fixture
def conn(tmp_path):
    c = flow.connect(tmp_path / ".flow" / "flow.db")
    yield c
    c.close()


def state(conn, task_id):
    return flow._task(conn, task_id)["state"]


# --- basic lifecycle -------------------------------------------------------


def test_add_creates_pending(conn):
    tid = flow.add(conn, "do a thing")
    assert state(conn, tid) == "pending"


def test_next_claims_in_progress(conn):
    tid = flow.add(conn, "task")
    t = flow.next_task(conn, assignee="alice")
    assert t["id"] == tid
    assert state(conn, tid) == "in_progress"
    assert t["assignee"] == "alice"


def test_next_returns_none_when_empty(conn):
    assert flow.next_task(conn, assignee="alice") is None


def test_next_skips_blocked(conn):
    a = flow.add(conn, "a")
    flow.next_task(conn, assignee="me")
    flow.escalate(conn, a, "stuck?")
    assert flow.next_task(conn, assignee="me") is None


def test_done_marks_done_with_outcome(conn):
    tid = flow.add(conn, "task")
    flow.done(conn, tid, "shipped")
    t = flow._task(conn, tid)
    assert t["state"] == "done"
    assert t["outcome"] == "shipped"


def test_unassigned_pool_is_claimable(conn):
    tid = flow.add(conn, "task")  # no assignee
    t = flow.next_task(conn, assignee="bob")
    assert t["id"] == tid and t["assignee"] == "bob"


# --- escalation ------------------------------------------------------------


def test_escalate_blocks(conn):
    tid = flow.add(conn, "task")
    flow.escalate(conn, tid, "which db?")
    assert state(conn, tid) == "blocked"


def test_reply_wakes_task(conn):
    tid = flow.add(conn, "task")
    flow.escalate(conn, tid, "which db?")
    flow.reply(conn, tid, "use sqlite")
    assert state(conn, tid) == "pending"


def test_done_rejected_while_escalated(conn):
    tid = flow.add(conn, "task")
    flow.escalate(conn, tid, "blocked on you")
    with pytest.raises(flow.FlowError):
        flow.done(conn, tid, "nope")


def test_reply_recorded_on_baton(conn):
    tid = flow.add(conn, "task")
    flow.escalate(conn, tid, "q?")
    flow.reply(conn, tid, "the answer")
    _, entries = flow.context(conn, tid)
    kinds = {e["kind"]: e["text"] for e in entries}
    assert kinds["reply"] == "the answer"


# --- fork / join -----------------------------------------------------------


def test_split_blocks_parent_and_creates_children(conn):
    parent = flow.add(conn, "big task")
    kids = flow.split(conn, parent, ["sub a", "sub b"])
    assert state(conn, parent) == "blocked"
    assert len(kids) == 2
    assert all(state(conn, k) == "pending" for k in kids)


def test_parent_wakes_when_all_children_done(conn):
    parent = flow.add(conn, "big")
    a, b = flow.split(conn, parent, ["a", "b"])
    flow.done(conn, a, "a done")
    assert state(conn, parent) == "blocked"  # b still open
    flow.done(conn, b, "b done")
    assert state(conn, parent) == "pending"  # joined


def test_parent_cannot_be_done_with_open_children(conn):
    parent = flow.add(conn, "big")
    flow.split(conn, parent, ["a"])
    with pytest.raises(flow.FlowError):
        flow.done(conn, parent, "premature")


def test_children_inherit_label(conn):  # HLD-010
    parent = flow.add(conn, "big", label="db")
    a, = flow.split(conn, parent, ["a"])
    assert flow._task(conn, a)["label"] == "db"


# --- reopen ----------------------------------------------------------------


def test_reopen_done_task(conn):
    tid = flow.add(conn, "task")
    flow.done(conn, tid, "done")
    flow.reopen(conn, tid)
    assert state(conn, tid) == "pending"


def test_reopen_rejects_non_done(conn):
    tid = flow.add(conn, "task")
    with pytest.raises(flow.FlowError):
        flow.reopen(conn, tid)


# --- projection ------------------------------------------------------------


def test_projection_writes_markdown(conn, tmp_path):
    tid = flow.add(conn, "projected task")
    md = tmp_path / ".flow" / "batons" / f"{tid}.md"
    assert md.exists()
    assert "projected task" in md.read_text()


# --- invariant guards (HLD-VERIFY negative tests) --------------------------


def test_only_four_states():
    # HLD-004: exactly four states exist.
    assert flow.STATES == ("pending", "in_progress", "blocked", "done")


def test_state_column_rejects_unknown_state(conn):
    # HLD-004: the store itself must refuse a state outside the four.
    tid = flow.add(conn, "task")
    with pytest.raises(Exception):
        conn.execute("UPDATE tasks SET state='zombie' WHERE id=?", (tid,))
        conn.commit()


def test_split_empty_children_rejected(conn):
    # G1: splitting with no children would strand the parent blocked forever.
    tid = flow.add(conn, "task")
    with pytest.raises(flow.FlowError):
        flow.split(conn, tid, [])
    assert state(conn, tid) != "blocked"


def test_cannot_escalate_done_task(conn):
    # G3 / HLD-004: done -> blocked is not a legal transition.
    tid = flow.add(conn, "task")
    flow.done(conn, tid, "shipped")
    with pytest.raises(flow.FlowError):
        flow.escalate(conn, tid, "too late?")
    assert state(conn, tid) == "done"


def test_cannot_split_done_task(conn):
    # G3 / HLD-004: done -> blocked is not a legal transition.
    tid = flow.add(conn, "task")
    flow.done(conn, tid, "shipped")
    with pytest.raises(flow.FlowError):
        flow.split(conn, tid, ["a"])
    assert state(conn, tid) == "done"


def test_next_skips_split_blocked_parent(conn):
    # HLD-005: a split-blocked parent is not runnable until its children join.
    parent = flow.add(conn, "big")
    flow.split(conn, parent, ["a", "b"])
    claimed = flow.next_task(conn, assignee="me")
    assert claimed is None or claimed["id"] != parent


# --- baton stage 0/1: escalate/split HLD divergences -----------------------


def test_double_escalation_rejected(conn):
    # HLD-005: one open escalation at a time; a second must be rejected.
    tid = flow.add(conn, "task")
    flow.escalate(conn, tid, "first question")
    with pytest.raises(flow.FlowError):
        flow.escalate(conn, tid, "second question")


def test_escalate_clears_assignee(conn):
    # HLD-004/005: a task parked as blocked is unassigned.
    tid = flow.add(conn, "task")
    flow.next_task(conn, assignee="alice")
    flow.escalate(conn, tid, "blocked on review")
    assert flow._task(conn, tid)["assignee"] is None


def test_escalate_keeps_label(conn):
    # HLD-005: clear assignee but keep label — regression guard.
    tid = flow.add(conn, "task", label="backend")
    flow.next_task(conn, assignee="alice")
    flow.escalate(conn, tid, "blocked")
    assert flow._task(conn, tid)["label"] == "backend"


def test_split_clears_parent_assignee(conn):
    # HLD-004/005: split parks parent as blocked; assignee must be cleared.
    tid = flow.add(conn, "task")
    flow.next_task(conn, assignee="alice")
    flow.split(conn, tid, ["sub a", "sub b"])
    assert flow._task(conn, tid)["assignee"] is None


def test_split_children_have_no_assignee(conn):
    # Regression guard: split children start with no assignee.
    tid = flow.add(conn, "task")
    flow.next_task(conn, assignee="alice")
    kids = flow.split(conn, tid, ["sub a", "sub b"])
    for kid in kids:
        assert flow._task(conn, kid)["assignee"] is None


def test_split_keeps_parent_label(conn):
    # HLD-005: split clears assignee but keeps label — regression guard.
    tid = flow.add(conn, "task", label="backend")
    flow.next_task(conn, assignee="alice")
    flow.split(conn, tid, ["sub a"])
    assert flow._task(conn, tid)["label"] == "backend"


# --- CLI smoke -------------------------------------------------------------


def test_cli_roundtrip(tmp_path, capsys):
    db = str(tmp_path / "flow.db")
    assert flow.main(["--db", db, "add", "cli task"]) == 0
    tid = capsys.readouterr().out.strip()
    assert flow.main(["--db", db, "next", "--assignee", "me"]) == 0
    out = capsys.readouterr().out
    assert f"#{tid}" in out and "[in_progress]" in out
    assert flow.main(["--db", db, "done", tid, "finished"]) == 0


# --- contract / structural invariants --------------------------------------


def test_context_survives_markdown_deletion(conn, tmp_path):
    """HLD-003 VERIFY: SQLite is the only source of truth; markdown is a one-way
    projection, never an input; the loop depends only on the CLI + text and names
    no specific AI"""
    # Deleting the projection must not lose data — context() reads the DB.
    tid = flow.add(conn, "task")
    flow.note(conn, tid, "important finding")
    md = tmp_path / ".flow" / "batons" / f"{tid}.md"
    if md.exists():
        md.unlink()
    t, entries = flow.context(conn, tid)
    assert t["text"] == "task"
    assert any(e["text"] == "important finding" for e in entries)


def test_cli_exposes_only_contract_verbs():
    # HLD-009: runners use only the listed verbs. The CLI surface is a stable
    # contract — adding or removing a verb must be a deliberate, test-visible change.
    src = Path(flow.__file__).read_text()
    verbs = set(re.findall(r'add_parser\(\s*"([a-z]+)"', src))
    assert verbs == {
        "add", "next", "context", "note", "done",
        "escalate", "split", "decide", "reply", "reopen", "list",
    }


def test_loop_contract_names_no_specific_ai():
    # HLD-003: the loop (core.md) and runtime (flow.py) are agnostic — they
    # name no specific AI. HLD.md may, in its tech notes; the contract files must not.
    root = Path(flow.__file__).parent
    blob = (root / "core.md").read_text().lower() + (root / "flow.py").read_text().lower()
    for vendor in ("claude", "devin", "codex", "openai", "anthropic", "gpt", "gemini"):
        assert vendor not in blob, f"agnostic contract names a specific AI: {vendor}"


def test_binary_reply_rule_in_core_md():
    # HLD-007 / FR-005: core.md must state the binary reply routing rule as an
    # explicit invariant sentence — both branches named, with explicit related-task
    # creation and original-task handling stated.
    root = Path(flow.__file__).parent
    text = (root / "core.md").read_text()
    assert "new related" in text and "flow add" in text
    assert "finish, continue, or re-park this one explicitly" in text, (
        "core.md missing explicit binary reply invariant "
        "(both branches must be stated; explicit original-task handling is required)"
    )


def test_ai_agnostic_readme():
    # HLD-003 / FR-008: README.md is user-facing documentation and must not name
    # specific AI systems — it should say "runner" or "AI session", never a brand.
    root = Path(flow.__file__).parent
    readme = (root / "README.md").read_text().lower()
    for vendor in ("claude", "devin", "codex", "openai", "anthropic", "gpt", "gemini"):
        assert vendor not in readme, f"README.md names a specific AI system: {vendor}"


# --- the regression ratchet, self-enforcing --------------------------------


def test_every_high_risk_invariant_has_a_test():
    # Institutionalizes the sweep that caught the bugs: every HIGH-risk HLD
    # section (each carries an HLD-VERIFY invariant) must be referenced by at
    # least one test here. Add a HIGH-risk section to HLD.md and this goes red
    # until you write its test.
    hld = (Path(flow.__file__).parent / "HLD.md").read_text()
    high, cur = [], None
    for line in hld.splitlines():
        m = re.match(r"^## (HLD-\d+)\b", line)
        if m:
            cur = m.group(1)
        elif line.startswith("HLD-RISK: HIGH") and cur:
            high.append(cur)
    tests = Path(__file__).read_text()
    missing = [a for a in high if a not in tests]
    assert not missing, f"HIGH-risk HLD invariants with no test: {missing}"


def test_high_risk_verify_texts_present_in_tests():
    """Every HIGH-risk HLD section's HLD-VERIFY text must appear verbatim
    (whitespace-normalised) somewhere in this test file — typically in a test
    docstring. Catches silent drift when HLD.md is updated but test docstrings
    are not updated to match."""
    hld_text = (Path(flow.__file__).parent / "HLD.md").read_text()

    def _n(s):
        return re.sub(r"\s+", " ", s).strip().rstrip(".")

    verify_map = {}
    cur, is_high = None, False
    for line in hld_text.splitlines():
        m = re.match(r"^## (HLD-\d+)\b", line)
        if m:
            cur, is_high = m.group(1), False
        elif line.startswith("HLD-RISK: HIGH") and cur:
            is_high = True
        elif line.startswith("HLD-VERIFY:") and is_high and cur:
            verify_map[cur] = line[len("HLD-VERIFY:"):].strip()

    tests_norm = _n(Path(__file__).read_text())
    missing = [hid for hid, vtext in verify_map.items() if _n(vtext) not in tests_norm]
    assert not missing, (
        "HIGH-risk HLD-VERIFY texts not present in test file — add a docstring "
        f"quoting the HLD-VERIFY line verbatim for: {missing}"
    )


# --- HLD-013 concurrency and durability ------------------------------------


def test_connection_hardening(tmp_path):  # HLD-013
    """HLD-013 VERIFY: concurrent `flow next` calls claim each task at most once (the
    claim takes the write lock before it reads the queue); every CLI operation is one
    all-or-nothing transaction (a crash leaves no partial state); the connection runs
    WAL + busy_timeout + synchronous=NORMAL"""
    c = flow.connect(tmp_path / "h.db")
    assert c.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
    assert c.execute("PRAGMA busy_timeout").fetchone()[0] >= 1000
    assert c.execute("PRAGMA synchronous").fetchone()[0] == 1  # NORMAL
    c.close()


def test_concurrent_next_claims_each_task_once(tmp_path):  # HLD-013
    import threading

    db = tmp_path / "c.db"
    c0 = flow.connect(db)
    for i in range(30):
        flow.add(c0, f"t{i}")
    c0.close()

    claimed = []
    lock = threading.Lock()

    def worker():
        c = flow.connect(db)
        while True:
            t = flow.next_task(c, assignee=None)
            if t is None:
                break
            with lock:
                claimed.append(t["id"])
        c.close()

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(claimed) == 30                    # none dropped
    assert sorted(claimed) == sorted(set(claimed))  # none claimed twice


def test_done_wakes_parent_atomically(conn):  # HLD-013
    parent = flow.add(conn, "parent")
    a, = flow.split(conn, parent, ["child"])
    assert state(conn, parent) == "blocked"
    flow.done(conn, a, "child done")
    # one transaction: child done AND parent woken, never half-applied
    assert state(conn, a) == "done"
    assert state(conn, parent) == "pending"


# --- HLD-010 work routing (soft affinity) ----------------------------------


def test_next_without_session_unchanged(conn):  # HLD-010
    a = flow.add(conn, "first", label="x")
    flow.add(conn, "second")
    t = flow.next_task(conn)  # no session: oldest pending regardless of label
    assert t["id"] == a and t["assignee"] is None


def test_session_binds_then_prefers_its_label(conn):  # HLD-010
    flow.add(conn, "db1", label="db")
    flow.add(conn, "web1", label="web")
    flow.add(conn, "db2", label="db")
    first = flow.next_task(conn, assignee="alice")   # binds alice -> first label
    second = flow.next_task(conn, assignee="alice")  # prefers same label
    assert second["label"] == first["label"]


def test_session_falls_back_when_label_dry(conn):  # HLD-010
    flow.add(conn, "db1", label="db")
    b = flow.add(conn, "web1", label="web")
    flow.next_task(conn, assignee="bob")  # claims db1, binds bob -> db
    t = flow.next_task(conn, assignee="bob")  # db dry -> fall back, don't idle
    assert t is not None and t["id"] == b


def test_hld010_verify_invariant(conn):
    """`flow next` without a session returns the oldest runnable task exactly as before;
    a session prefers its bound label, binds to the label of the first labeled task it
    claims, and falls back to any runnable task only when none of its label remain;
    a runner sees "none" only when no runnable work exists at all.

    HLD-010 VERIFY: `flow next` without a session returns the oldest runnable task
    exactly as before; a session prefers its bound label, binds to the label of the first
    labeled task it claims, and falls back to any runnable task only when none of its
    label remain; a runner sees "none" only when no runnable work exists at all"""
    # backward compat: no session → oldest runnable task
    oldest = flow.add(conn, "oldest", label="x")
    flow.add(conn, "newer", label="y")
    t = flow.next_task(conn, assignee="anon")
    assert t["id"] == oldest

    # session binds to label of first labeled task claimed
    flow.add(conn, "x2", label="x")
    flow.add(conn, "z1", label="z")
    t2 = flow.next_task(conn, assignee="sess")  # claims newer (label=y), binds sess->y
    assert t2["label"] == "y"
    t3 = flow.next_task(conn, assignee="sess")  # y dry → fall back to x2 or z1
    assert t3 is not None

    # runner sees None only when queue is empty
    flow.next_task(conn, assignee="drain1")
    flow.next_task(conn, assignee="drain2")
    nothing = flow.next_task(conn, assignee="drain3")
    assert nothing is None


# --- HLD-014 orphaned-work recovery (lease, reclaim, fence) -----------------


def test_migration_adds_columns_to_old_db(tmp_path):  # HLD-013 / HLD-014
    # An old DB predating the `label` and `reclaim_count` columns must be upgraded;
    # CREATE TABLE IF NOT EXISTS will not add a column to an existing table.
    import sqlite3

    db = tmp_path / ".flow" / "old.db"
    db.parent.mkdir(parents=True, exist_ok=True)
    raw = sqlite3.connect(db)
    raw.executescript(
        "CREATE TABLE tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, text TEXT NOT NULL,"
        " state TEXT NOT NULL DEFAULT 'pending', assignee TEXT, type TEXT,"
        " parent_id INTEGER, outcome TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);"
    )
    raw.commit()
    raw.close()
    c = flow.connect(db)
    cols = {r["name"] for r in c.execute("PRAGMA table_info(tasks)").fetchall()}
    assert "label" in cols and "reclaim_count" in cols
    c.close()


def test_orphaned_task_reclaimed(conn):  # HLD-014
    """HLD-014 VERIFY: a task whose session has been silent past the lease TTL is
    reclaimed to pending — in_progress only, never blocked — recording the reason
    and incrementing reclaim_count; after a reclaim threshold it is escalated instead
    of requeued; done/escalate/split by a session that no longer holds a session-owned
    task are rejected; note/decide/reply stay multi-writer; reclaim runs under the
    claim's BEGIN IMMEDIATE"""
    tid = flow.add(conn, "work")
    flow.next_task(conn, assignee="alice")        # alice claims
    _age(conn, tid, flow.LEASE_TTL + 10)          # alice goes silent
    t = flow.next_task(conn, assignee="bob")      # bob reclaims, then claims
    assert t["id"] == tid and t["assignee"] == "bob"
    assert flow._task(conn, tid)["reclaim_count"] == 1
    _, entries = flow.context(conn, tid)
    assert any("reclaimed" in e["text"] for e in entries)


def test_fresh_claim_not_reclaimed(conn):  # HLD-014
    tid = flow.add(conn, "work")
    flow.next_task(conn, assignee="alice")        # fresh claim, within TTL
    assert flow.next_task(conn, assignee="bob") is None
    assert flow._task(conn, tid)["assignee"] == "alice"


def test_blocked_task_never_reclaimed(conn):  # HLD-014
    tid = flow.add(conn, "work")
    flow.next_task(conn, assignee="alice")
    flow.escalate(conn, tid, "stuck", session="alice")  # owner parks it -> blocked
    _age(conn, tid, flow.LEASE_TTL + 10)
    assert flow.next_task(conn, assignee="bob") is None
    assert state(conn, tid) == "blocked"


def test_progress_refreshes_lease(conn):  # HLD-014
    tid = flow.add(conn, "work")
    flow.next_task(conn, assignee="alice")
    _age(conn, tid, flow.LEASE_TTL + 10)
    flow.note(conn, tid, "still working")         # refreshes the lease
    assert flow.next_task(conn, assignee="bob") is None
    assert flow._task(conn, tid)["assignee"] == "alice"


def test_stale_owner_cannot_done(conn):  # HLD-014
    tid = flow.add(conn, "work")
    flow.next_task(conn, assignee="alice")
    _age(conn, tid, flow.LEASE_TTL + 10)
    flow.next_task(conn, assignee="bob")          # reclaimed to bob
    with pytest.raises(flow.FlowError):
        flow.done(conn, tid, "alice finishing", session="alice")
    assert state(conn, tid) == "in_progress"      # still bob's, not completed


def test_owner_can_complete(conn):  # HLD-014
    tid = flow.add(conn, "work")
    flow.next_task(conn, assignee="alice")
    flow.done(conn, tid, "ok", session="alice")
    assert state(conn, tid) == "done"


def test_blackboard_not_fenced(conn):  # HLD-014
    tid = flow.add(conn, "work")
    flow.next_task(conn, assignee="alice")        # owner is alice
    flow.note(conn, tid, "observation from elsewhere")   # no session param: always allowed
    flow.decide(conn, tid, "a recorded call")
    _, entries = flow.context(conn, tid)
    kinds = {e["kind"] for e in entries}
    assert "note" in kinds and "decision" in kinds


def test_no_session_task_unfenced(conn):  # HLD-014
    tid = flow.add(conn, "work")
    flow.next_task(conn)                          # claimed with NO session (legacy)
    flow.done(conn, tid, "done via legacy path")  # no --session -> unfenced
    assert state(conn, tid) == "done"


def test_repeated_reclaim_escalates(conn):  # HLD-014
    tid = flow.add(conn, "poison")
    for _ in range(flow.RECLAIM_MAX + 1):
        flow.next_task(conn, assignee="runner")   # claim
        _age(conn, tid, flow.LEASE_TTL + 10)      # then go silent
    assert flow.next_task(conn, assignee="runner2") is None  # escalated, not requeued
    assert state(conn, tid) == "blocked"


def test_reclaim_escalation_clears_assignee(conn):  # HLD-004/005 + HLD-014
    # HLD-004/005: a task parked as blocked is unassigned — same invariant as escalate().
    tid = flow.add(conn, "poison")
    for _ in range(flow.RECLAIM_MAX + 1):
        flow.next_task(conn, assignee="runner")
        _age(conn, tid, flow.LEASE_TTL + 10)
    flow.next_task(conn, assignee="runner2")  # triggers the escalation
    assert state(conn, tid) == "blocked"
    assert flow._task(conn, tid)["assignee"] is None


def test_reclaim_escalation_keeps_label(conn):  # HLD-005 + HLD-014
    # HLD-005: clear assignee but keep label — regression guard for reclaim path.
    tid = flow.add(conn, "poison", label="infra")
    for _ in range(flow.RECLAIM_MAX + 1):
        flow.next_task(conn, assignee="runner")
        _age(conn, tid, flow.LEASE_TTL + 10)
    flow.next_task(conn, assignee="runner2")  # triggers the escalation
    assert state(conn, tid) == "blocked"
    assert flow._task(conn, tid)["label"] == "infra"


def test_cli_done_accepts_assignee_form(tmp_path):  # HLD-014
    # core.md prescribes `--assignee <me>` on done/escalate/split; the CLI must accept it
    # (the fence verbs are the point of HLD-014 — they must not error for a compliant runner).
    db = str(tmp_path / "flow.db")
    assert flow.main(["--db", db, "add", "ship"]) == 0
    assert flow.main(["--db", db, "next", "--assignee", "me"]) == 0
    assert flow.main(["--db", db, "done", "1", "shipped", "--assignee", "me"]) == 0


# --- HLD-009 CLI contract characterization (spec 017-cli-contract) ---------


def test_runner_verb_contracts(conn):
    # SC-001: each of the 8 runner verbs exercises its documented contract in isolation.
    # add: creates a pending task
    tid = flow.add(conn, "work item")
    assert state(conn, tid) == "pending"

    # next on non-empty: claims the task and returns it
    task = flow.next_task(conn, assignee="runner")
    assert task is not None
    assert task["id"] == tid
    assert state(conn, tid) == "in_progress"

    # next on empty (all claimed): returns None
    assert flow.next_task(conn, assignee="runner2") is None

    # context: returns the task and its baton entries
    t, entries = flow.context(conn, tid)
    assert t["id"] == tid
    assert isinstance(entries, list)

    # note: appends to baton; visible via context
    flow.note(conn, tid, "progress update")
    _, entries = flow.context(conn, tid)
    assert any(e["kind"] == "note" and "progress update" in e["text"] for e in entries)

    # decide: records a decision on the baton
    flow.decide(conn, tid, "use approach X")
    _, entries = flow.context(conn, tid)
    assert any(e["kind"] == "decision" and "use approach X" in e["text"] for e in entries)

    # done: completes the task with a stated outcome
    flow.done(conn, tid, "finished successfully")
    assert state(conn, tid) == "done"

    # escalate: parks a fresh task as blocked
    eid = flow.add(conn, "needs human input")
    flow.next_task(conn, assignee="runner")
    flow.escalate(conn, eid, "which option?")
    assert state(conn, eid) == "blocked"


def test_runner_verb_contracts_split(conn):
    # SC-001 (split): flow split creates children (pending), parks parent (blocked),
    # and parent wakes to pending when all children are done. (HLD-009 / HLD-005)
    pid = flow.add(conn, "big task")
    flow.next_task(conn, assignee="runner")

    child_ids = flow.split(conn, pid, ["child A", "child B"])
    assert len(child_ids) == 2
    assert state(conn, pid) == "blocked"
    assert state(conn, child_ids[0]) == "pending"
    assert state(conn, child_ids[1]) == "pending"

    # complete both children — parent must wake
    flow.next_task(conn, assignee="runner")  # claims child A
    flow.done(conn, child_ids[0], "A done")
    flow.next_task(conn, assignee="runner")  # claims child B
    flow.done(conn, child_ids[1], "B done")
    assert state(conn, pid) == "pending"


def test_human_ops_verbs_absent_from_runner_loop():
    # SC-002: reply, reopen, and list are human/ops-facing — they MUST NOT appear as
    # CLI commands in core.md (the runner loop definition).
    core = (Path(flow.__file__).parent / "core.md").read_text()

    # human/ops verbs are absent from the runner loop
    assert "flow reply" not in core
    assert "flow reopen" not in core
    assert "flow list" not in core

    # runner verbs ARE present — core.md teaches runners how to use them
    for verb in ("flow next", "flow context", "flow note", "flow decide",
                 "flow done", "flow escalate", "flow split", "flow add"):
        assert verb in core, f"runner verb missing from core.md: {verb}"


def test_hld004_verify_invariant(conn):
    """HLD-004 VERIFY: only four states exist; a task cannot be done with unfinished
    children; done is reopenable via reopen() or a late reply(); blocked wakes to pending
    only when all dependencies resolve; the done/escalate/split guard is on dependencies
    (blocked check), not on prior state — agents may operate from any non-blocked state"""
    # only four states exist
    assert flow.STATES == ("pending", "in_progress", "blocked", "done")
    assert len(flow.STATES) == 4

    # a task cannot be done with unfinished children
    parent = flow.add(conn, "parent")
    flow.next_task(conn, assignee="runner")
    flow.split(conn, parent, ["child A", "child B"])
    with pytest.raises(flow.FlowError):
        flow.done(conn, parent, "premature")  # parent is blocked by unfinished children

    # done is reopenable
    single = flow.add(conn, "single task")
    flow.next_task(conn, assignee="runner")
    flow.done(conn, single, "finished")
    assert state(conn, single) == "done"
    flow.reopen(conn, single)
    assert state(conn, single) == "pending"


def test_hld005_verify_invariant(conn):
    """HLD-005 VERIFY: escalate and split both park the task as blocked and free the
    runner; the guard is that the task must not be done (not: must be in_progress);
    a task is runnable only when it has no unmet dependencies"""
    # escalate parks the task as blocked and frees the runner
    task_a = flow.add(conn, "task A")
    task_b = flow.add(conn, "task B")
    flow.next_task(conn, assignee="runner")  # claims task_a
    flow.escalate(conn, task_a, "need human input")
    assert state(conn, task_a) == "blocked"
    claimed = flow.next_task(conn, assignee="runner")  # runner is free to claim task_b
    assert claimed is not None and claimed["id"] == task_b

    # split parks the parent as blocked and frees the runner; children are runnable
    parent = flow.add(conn, "parent")
    flow.next_task(conn, assignee="runner2")  # claims parent
    child_ids = flow.split(conn, parent, ["child X", "child Y"])
    assert state(conn, parent) == "blocked"
    # children have no unmet dependencies — they are runnable
    c1 = flow.next_task(conn, assignee="runner3")
    assert c1 is not None and c1["id"] in child_ids


def test_escalation_question_on_baton(conn):
    # SC-001: escalate records the question text on the baton as a kind="escalation" entry.
    tid = flow.add(conn, "task needing help")
    flow.next_task(conn, assignee="runner")
    flow.escalate(conn, tid, "which path?")
    _, entries = flow.context(conn, tid)
    assert any(e["kind"] == "escalation" and "which path?" in e["text"] for e in entries)


def test_escalation_triggers_in_core_md():
    # SC-002: core.md documents all four escalation triggers by name.
    core = (Path(flow.__file__).parent / "core.md").read_text()
    for trigger in ("Ambiguity", "Authority", "Irreversibility", "Repeated failure"):
        assert trigger in core, f"escalation trigger missing from core.md: {trigger}"


def test_hld007_verify_invariant(conn):
    """HLD-007 VERIFY: a human reply is appended to the baton and resolves the open
    escalation when the task is blocked; a reply to a done task reopens it to pending
    (late reply — signals premature completion); when the task wakes, the runner either
    continues this task or creates a new related task from the reply without silently
    merging scopes"""
    tid = flow.add(conn, "question task")
    flow.next_task(conn, assignee="runner")
    flow.escalate(conn, tid, "which approach?")
    assert state(conn, tid) == "blocked"
    flow.reply(conn, tid, "use approach A")
    assert state(conn, tid) == "pending"
    _, entries = flow.context(conn, tid)
    assert any(e["kind"] == "reply" and "use approach A" in e["text"] for e in entries)


def test_hld007_late_reply_reopens_done_task(conn):
    """HLD-007 VERIFY: a reply to a done task reopens it to pending (late reply —
    signals premature completion).

    HLD-004 VERIFY: done is reopenable via reopen() or a late reply()."""
    tid = flow.add(conn, "task")
    flow.next_task(conn, assignee="runner")
    flow.done(conn, tid, "seemed done")
    assert state(conn, tid) == "done"
    flow.reply(conn, tid, "actually you missed X")
    assert state(conn, tid) == "pending"
    _, entries = flow.context(conn, tid)
    assert any(e["kind"] == "reply" and "missed X" in e["text"] for e in entries)
    assert any(e["kind"] == "system" and "reopened by late reply" in e["text"] for e in entries)


def test_hld007_binary_reply_branches(conn):
    """HLD-007 VERIFY: when the task wakes, the runner either continues this task or
    creates a new related task from the reply without silently merging scopes.

    Branch A — reply is about this task: task wakes to pending, reply on baton, runner
    continues this task.
    Branch B — reply is new scope: runner creates a new task explicitly; original and
    new task are independent (scopes not silently merged)."""
    # Branch A: reply about this task → task wakes, reply visible, runner continues
    tid_a = flow.add(conn, "task A needs clarification")
    flow.next_task(conn, assignee="runner")
    flow.escalate(conn, tid_a, "which approach?")
    flow.reply(conn, tid_a, "use approach A — pertains to this task")
    assert state(conn, tid_a) == "pending"
    _, entries_a = flow.context(conn, tid_a)
    assert any(e["kind"] == "reply" and "approach A" in e["text"] for e in entries_a)

    # Branch B: reply is new scope → runner adds task explicitly; scopes stay separate
    tid_b = flow.add(conn, "task B")
    flow.next_task(conn, assignee="runner2")
    flow.escalate(conn, tid_b, "is there related work?")
    flow.reply(conn, tid_b, "yes — fix the login page too (new scope)")
    assert state(conn, tid_b) == "pending"
    # runner creates new task for new scope — does NOT merge into tid_b
    new_tid = flow.add(conn, "fix login page")
    assert state(conn, new_tid) == "pending"
    # original and new task are independent
    flow.next_task(conn, assignee="runner2")
    flow.done(conn, tid_b, "original scope complete; new scope tracked separately")
    assert state(conn, tid_b) == "done"
    assert state(conn, new_tid) == "pending"


def test_late_reply_on_done_child_parent_stays_done(conn):
    """Characterizes the done-parent + pending-child edge case.

    When flow reply reopens a done child, its done parent is NOT automatically
    reopened. The 'no done task with unfinished children' invariant is enforced
    at the transition to done only — not retroactively. The human decides
    explicitly whether to flow reopen the parent. (HLD-004 RATIONALE)"""
    parent = flow.add(conn, "parent")
    child, = flow.split(conn, parent, ["child"])
    flow.done(conn, child, "child done")
    assert state(conn, parent) == "pending"
    flow.done(conn, parent, "all done")
    assert state(conn, parent) == "done"

    flow.reply(conn, child, "child missed something")
    assert state(conn, child) == "pending"   # child reopened
    assert state(conn, parent) == "done"     # parent NOT auto-reopened; human decides


def test_hld008_verify_invariant(conn, tmp_path):
    """HLD-008 VERIFY: the baton lives in the database and is read via the CLI;
    markdown batons are a one-way projection; declared context is the only context
    the contract touches."""
    tid = flow.add(conn, "baton task")
    flow.note(conn, tid, "critical finding")
    # delete the markdown projection — declared context must still be accessible via context()
    md = tmp_path / ".flow" / "batons" / f"{tid}.md"
    if md.exists():
        md.unlink()
    t, entries = flow.context(conn, tid)
    assert t["id"] == tid
    assert any(e["kind"] == "note" and "critical finding" in e["text"] for e in entries)


def test_hld009_verify_invariant():
    """HLD-009 VERIFY: runners use only the listed verbs; no direct database access;
    reply, reopen, and list are human/ops-facing and not part of the runner loop.

    This test characterizes that core.md — the runner loop definition — structurally
    satisfies the HLD-009 VERIFY invariant.
    """
    core = (Path(flow.__file__).parent / "core.md").read_text()

    # no direct database access — core.md must not reference sqlite3 or .db paths
    assert "sqlite3" not in core
    assert ".db" not in core

    # only runner verbs appear as CLI commands — extract all `flow <verb>` patterns
    import re
    flow_verbs_in_core = set(re.findall(r'flow\s+(\w+)', core))
    runner_verbs = {"add", "next", "context", "note", "done", "escalate", "split", "decide"}
    human_ops_verbs = {"reply", "reopen", "list"}

    assert not (flow_verbs_in_core & human_ops_verbs), (
        f"human/ops verbs found as CLI commands in core.md: "
        f"{flow_verbs_in_core & human_ops_verbs}"
    )
    assert runner_verbs <= flow_verbs_in_core, (
        f"runner verbs missing from core.md: {runner_verbs - flow_verbs_in_core}"
    )


def test_hld002_vocabulary_in_core_md():
    """HLD-002 vocabulary terms must appear in core.md to prevent drift.

    HLD-002: Runner, Task, Baton, Handoff, Decision are the five load-bearing terms."""
    core = (Path(flow.__file__).parent / "core.md").read_text().lower()
    for term in ("runner", "task", "baton", "handoff", "decision"):
        assert term in core, f"HLD-002 vocabulary term missing from core.md: {term}"
