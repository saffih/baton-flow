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
    # HLD-003 / HLD-008: SQLite is the source of truth; markdown is one-way.
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


# --- HLD-013 concurrency and durability ------------------------------------


def test_connection_hardening(tmp_path):  # HLD-013
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


def test_cli_done_accepts_assignee_form(tmp_path):  # HLD-014
    # core.md prescribes `--assignee <me>` on done/escalate/split; the CLI must accept it
    # (the fence verbs are the point of HLD-014 — they must not error for a compliant runner).
    db = str(tmp_path / "flow.db")
    assert flow.main(["--db", db, "add", "ship"]) == 0
    assert flow.main(["--db", db, "next", "--assignee", "me"]) == 0
    assert flow.main(["--db", db, "done", "1", "shipped", "--assignee", "me"]) == 0
