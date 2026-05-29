"""Tests for the Baton Flow runtime: lifecycle, fork-join, escalation, reopen."""

import re
from pathlib import Path

import pytest

import flow


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


def test_children_inherit_assignee(conn):
    parent = flow.add(conn, "big", assignee="alice")
    a, = flow.split(conn, parent, ["a"])
    assert flow._task(conn, a)["assignee"] == "alice"


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
