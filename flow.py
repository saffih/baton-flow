#!/usr/bin/env python3
"""Baton Flow — the agnostic task runtime.

SQLite is the single source of truth. Markdown under .flow/batons/ is a one-way
projection for human reading. Runners talk to this CLI only; never the DB directly.

Lifecycle:  pending -> in_progress -> done   (done is reopenable)
            in_progress -> blocked           (waiting on a human and/or children)
            blocked -> pending               (woken when every dependency resolves)

A task is runnable only when it has no unmet dependencies:
  - no open escalation (waiting on a human answer), and
  - no unfinished child task (split).
"""

import argparse
import os
import sqlite3
import sys
import tempfile
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

STATES = ("pending", "in_progress", "blocked", "done")

# HLD-014: a task in_progress with no progress past this many seconds is orphaned.
# Generous on purpose — a false reclaim is bounded by the fence (a stale owner's
# done/escalate/split is rejected), so the cost of waiting is low.
LEASE_TTL = 3600
# After this many reclaims a task is escalated to a human instead of requeued.
RECLAIM_MAX = 3


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# --- storage ---------------------------------------------------------------

SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    text       TEXT NOT NULL,
    state      TEXT NOT NULL DEFAULT 'pending'
                 CHECK(state IN ('pending','in_progress','blocked','done')),
    assignee   TEXT,
    label      TEXT,
    parent_id  INTEGER REFERENCES tasks(id),
    outcome    TEXT,
    reclaim_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tasks_state_updated ON tasks(state, updated_at);
CREATE TABLE IF NOT EXISTS baton_entries (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id    INTEGER NOT NULL REFERENCES tasks(id),
    kind       TEXT NOT NULL,
    text       TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS escalations (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id     INTEGER NOT NULL REFERENCES tasks(id),
    question    TEXT NOT NULL,
    answer      TEXT,
    created_at  TEXT NOT NULL,
    answered_at TEXT
);
CREATE TABLE IF NOT EXISTS sessions (
    name        TEXT PRIMARY KEY,
    bound_label TEXT,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);
"""


def connect(db_path: Path) -> sqlite3.Connection:
    """Open the database with durable, concurrency-safe settings (HLD-013).

    WAL allows concurrent readers; busy_timeout makes a competing writer wait
    instead of failing with "database is locked"; synchronous=NORMAL is the right
    durability/speed point under WAL. isolation_level=None hands transaction
    control to us so each operation is one explicit BEGIN IMMEDIATE..COMMIT.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(SCHEMA)
    _migrate(conn)
    return conn


def connect_existing_readonly(db_path: Path) -> sqlite3.Connection:
    """Open an existing database for diagnostics without creating or migrating it."""
    db_path = Path(db_path)
    if not db_path.exists():
        # INVARIANT: existence
        raise FlowError(f"database does not exist: {db_path}")
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, isolation_level=None)
    conn.row_factory = sqlite3.Row
    return conn


def _migrate(conn):
    """Add columns introduced after a database was first created.

    CREATE TABLE IF NOT EXISTS never alters an existing table, so a DB made by an
    earlier version is missing newer columns. Add them idempotently.
    """
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(tasks)").fetchall()}
    if "label" not in cols:  # label column added to replace the old `type` column; pre-existing rows get NULL
        conn.execute("ALTER TABLE tasks ADD COLUMN label TEXT")
    if "reclaim_count" not in cols:  # HLD-014
        conn.execute("ALTER TABLE tasks ADD COLUMN reclaim_count INTEGER NOT NULL DEFAULT 0")


@contextmanager
def _tx(conn):
    """One operation = one all-or-nothing transaction (HLD-013).

    BEGIN IMMEDIATE takes the write lock up front, so a read-then-write (the claim
    in next_task) cannot race another writer. A crash mid-operation leaves no
    partial state: either everything commits or it all rolls back.
    """
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    else:
        conn.execute("COMMIT")


# --- core operations -------------------------------------------------------


class FlowError(Exception):
    """A rule violation the runner should see and handle, not a crash."""


def _task(conn, task_id):
    row = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
    if row is None:
        # INVARIANT: existence
        raise FlowError(f"task {task_id} not found")
    return row


def _append(conn, task_id, kind, text):
    conn.execute(
        "INSERT INTO baton_entries (task_id, kind, text, created_at) VALUES (?,?,?,?)",
        (task_id, kind, text, now()),
    )


def _set_state(conn, task_id, state):
    conn.execute(
        "UPDATE tasks SET state=?, updated_at=? WHERE id=?", (state, now(), task_id)
    )


def _touch(conn, task_id):
    """Refresh a task's lease stamp (HLD-014) without changing its state."""
    conn.execute("UPDATE tasks SET updated_at=? WHERE id=?", (now(), task_id))


def _is_blocked(conn, task_id) -> bool:
    open_esc = conn.execute(
        "SELECT 1 FROM escalations WHERE task_id=? AND answer IS NULL LIMIT 1",
        (task_id,),
    ).fetchone()
    if open_esc:
        return True
    open_child = conn.execute(
        "SELECT 1 FROM tasks WHERE parent_id=? AND state!='done' LIMIT 1", (task_id,)
    ).fetchone()
    return open_child is not None


def _reclaim_orphans(conn):
    """Return tasks whose holding session has gone silent past the lease (HLD-014).

    Runs inside next_task's transaction, before the queue is read, so reclaim and the
    subsequent claim share one BEGIN IMMEDIATE and cannot race. Only in_progress tasks
    are reclaimed; blocked tasks are parked by design. After RECLAIM_MAX reclaims a task
    is escalated to a human instead of being requeued forever. Returns the ids it touched
    so the caller can refresh their projections after the transaction commits.
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(seconds=LEASE_TTL)).isoformat(timespec="seconds")
    rows = conn.execute(
        "SELECT id, assignee, updated_at, reclaim_count FROM tasks"
        " WHERE state='in_progress' AND updated_at < ?",
        (cutoff,),
    ).fetchall()
    touched = []
    for r in rows:
        tid = r["id"]
        if r["reclaim_count"] + 1 > RECLAIM_MAX:
            conn.execute(
                "INSERT INTO escalations (task_id, question, created_at) VALUES (?,?,?)",
                (tid, f"orphaned {r['reclaim_count']}x; escalating to a human", now()),
            )
            _append(conn, tid, "escalation", f"reclaimed {r['reclaim_count']}x without completion; escalated")
            _set_state(conn, tid, "blocked")
            conn.execute("UPDATE tasks SET assignee=NULL WHERE id=?", (tid,))
        else:
            conn.execute(
                "UPDATE tasks SET state='pending', assignee=NULL,"
                " reclaim_count=reclaim_count+1, updated_at=? WHERE id=?",
                (now(), tid),
            )
            _append(conn, tid, "system", f"reclaimed: session {r['assignee']} silent since {r['updated_at']}")
        touched.append(tid)
    return touched


def _require_owner(conn, task_id, session):
    """Fence an ownership-implying transition (HLD-014).

    A named session may only done/escalate/split a task it still holds. An
    unidentified caller (session is None — the legacy/ops path, HLD-010) is unfenced,
    and a task with no session owner is unfenced. Blackboard writes never call this.
    """
    if session is None:
        return
    owner = _task(conn, task_id)["assignee"]
    if owner is not None and owner != session:
        # INVARIANT: ownership
        raise FlowError(f"you no longer hold task {task_id} (held by {owner})")


def _maybe_wake(conn, task_id):
    """If a blocked task has no remaining unmet dependencies, wake it to pending."""
    t = _task(conn, task_id)
    if t["state"] == "blocked" and not _is_blocked(conn, task_id):
        _set_state(conn, task_id, "pending")
        _append(conn, task_id, "system", "woken: all dependencies resolved")


def add(conn, text, label=None, parent_id=None):
    with _tx(conn):
        cur = conn.execute(
            "INSERT INTO tasks (text, state, label, parent_id, created_at, updated_at)"
            " VALUES (?, 'pending', ?, ?, ?, ?)",
            (text, label, parent_id, now(), now()),
        )
        task_id = cur.lastrowid
        _append(conn, task_id, "system", f"created: {text}")
    project(conn, task_id)
    return task_id


def next_task(conn, assignee=None):
    """Claim the oldest runnable task (HLD-010 routing, HLD-013 atomic claim).

    A named runner (`assignee`) is a session: it prefers work of its bound label,
    binds to the label of the first labeled task it takes, and falls back to any
    runnable task rather than idle. Claiming happens under a write lock taken
    before the SELECT, so two sessions can never both hold one task.
    """
    tid = None
    with _tx(conn):
        reclaimed = _reclaim_orphans(conn)  # HLD-014: return silent sessions' tasks first
        bound = None
        if assignee:
            r = conn.execute(
                "SELECT bound_label FROM sessions WHERE name=?", (assignee,)
            ).fetchone()
            bound = r["bound_label"] if r else None
        row = None
        if bound is not None:
            row = conn.execute(
                "SELECT * FROM tasks WHERE state='pending' AND label=? ORDER BY id LIMIT 1",
                (bound,),
            ).fetchone()
        if row is None:  # unbound, or bound label is dry -> fall back to any
            row = conn.execute(
                "SELECT * FROM tasks WHERE state='pending' ORDER BY id LIMIT 1"
            ).fetchone()
        if row is not None:
            tid = row["id"]
            if assignee and bound is None and row["label"] is not None:
                conn.execute(
                    "INSERT INTO sessions (name, bound_label, created_at, updated_at)"
                    " VALUES (?,?,?,?)"
                    " ON CONFLICT(name) DO UPDATE SET bound_label=excluded.bound_label,"
                    " updated_at=excluded.updated_at",
                    (assignee, row["label"], now(), now()),
                )
            conn.execute(
                "UPDATE tasks SET state='in_progress', assignee=?, updated_at=? WHERE id=?",
                (assignee, now(), tid),
            )
    for rid in reclaimed:  # refresh projections for tasks reclaimed/escalated above
        if rid != tid:
            project(conn, rid)
    if tid is None:
        return None
    project(conn, tid)
    return _task(conn, tid)


def context(conn, task_id):
    t = _task(conn, task_id)
    entries = conn.execute(
        "SELECT kind, text, created_at FROM baton_entries WHERE task_id=? ORDER BY id",
        (task_id,),
    ).fetchall()
    return t, entries


def note(conn, task_id, text):
    with _tx(conn):
        _task(conn, task_id)
        _append(conn, task_id, "note", text)
        _touch(conn, task_id)  # HLD-014: runner progress refreshes the lease
    project(conn, task_id)


def decide(conn, task_id, text):
    with _tx(conn):
        _task(conn, task_id)
        _append(conn, task_id, "decision", text)
        _touch(conn, task_id)  # HLD-014: runner progress refreshes the lease
    project(conn, task_id)


def escalate(conn, task_id, question, session=None):
    with _tx(conn):
        _require_owner(conn, task_id, session)
        t = _task(conn, task_id)
        if t["state"] == "done":
            # INVARIANT: lifecycle
            raise FlowError(f"task {task_id} is done; reopen it before escalating")
        open_esc = conn.execute(
            "SELECT 1 FROM escalations WHERE task_id=? AND answer IS NULL LIMIT 1",
            (task_id,),
        ).fetchone()
        if open_esc:
            # INVARIANT: lifecycle
            raise FlowError(f"task {task_id} already has an open escalation")
        conn.execute(
            "INSERT INTO escalations (task_id, question, created_at) VALUES (?,?,?)",
            (task_id, question, now()),
        )
        _append(conn, task_id, "escalation", question)
        _set_state(conn, task_id, "blocked")
        conn.execute("UPDATE tasks SET assignee=NULL WHERE id=?", (task_id,))
    project(conn, task_id)


def split(conn, task_id, child_texts, session=None):
    if not child_texts:
        # INVARIANT: dependency
        raise FlowError("split requires at least one child task")
    child_ids = []
    with _tx(conn):
        _require_owner(conn, task_id, session)
        parent = _task(conn, task_id)
        if parent["state"] == "done":
            # INVARIANT: lifecycle
            raise FlowError(f"task {task_id} is done; reopen it before splitting")
        for text in child_texts:
            cid = conn.execute(
                "INSERT INTO tasks (text, state, label, parent_id, created_at, updated_at)"
                " VALUES (?, 'pending', ?, ?, ?, ?)",
                (text, parent["label"], task_id, now(), now()),
            ).lastrowid
            _append(conn, cid, "system", f"created as child of task {task_id}")
            child_ids.append(cid)
        _append(conn, task_id, "split", f"split into tasks {child_ids}")
        _set_state(conn, task_id, "blocked")
        conn.execute("UPDATE tasks SET assignee=NULL WHERE id=?", (task_id,))
    project(conn, task_id)
    for cid in child_ids:
        project(conn, cid)
    return child_ids


def done(conn, task_id, outcome, session=None):
    parent_id = None
    with _tx(conn):
        _require_owner(conn, task_id, session)
        _task(conn, task_id)
        if _is_blocked(conn, task_id):
            # INVARIANT: dependency
            raise FlowError(
                f"task {task_id} cannot be done: it still has unmet dependencies "
                "(open escalation or unfinished children)"
            )
        conn.execute(
            "UPDATE tasks SET state='done', outcome=?, updated_at=? WHERE id=?",
            (outcome, now(), task_id),
        )
        _append(conn, task_id, "done", outcome)
        parent_id = _task(conn, task_id)["parent_id"]
        if parent_id is not None:
            _maybe_wake(conn, parent_id)  # same transaction: no stranded parent on crash
    project(conn, task_id)
    if parent_id is not None:
        project(conn, parent_id)


def reply(conn, task_id, text):
    """Human answers a blocked task or signals premature completion on a done task.

    On a blocked task: records the reply, closes the open escalation, and wakes
    the task. The runner decides on pickup whether the reply is about this task
    (continue) or new scope (a fresh `add`).

    On a done task: reopens it to pending (late reply — HLD-004/HLD-007). The
    runner re-reads the baton and decides whether to continue, add new scope, or
    re-close."""
    with _tx(conn):
        t = _task(conn, task_id)
        esc = conn.execute(
            "SELECT id FROM escalations WHERE task_id=? AND answer IS NULL ORDER BY id LIMIT 1",
            (task_id,),
        ).fetchone()
        if esc:
            conn.execute(
                "UPDATE escalations SET answer=?, answered_at=? WHERE id=?",
                (text, now(), esc["id"]),
            )
        _append(conn, task_id, "reply", text)
        if t["state"] == "done":
            _set_state(conn, task_id, "pending")
            _append(conn, task_id, "system", "reopened by late reply")
        else:
            _maybe_wake(conn, task_id)
    project(conn, task_id)


def reopen(conn, task_id):
    with _tx(conn):
        t = _task(conn, task_id)
        if t["state"] != "done":
            # INVARIANT: lifecycle
            raise FlowError(f"task {task_id} is not done (state={t['state']})")
        _set_state(conn, task_id, "pending")
        _append(conn, task_id, "system", "reopened")
    project(conn, task_id)


def list_tasks(conn):
    return conn.execute("SELECT * FROM tasks ORDER BY id").fetchall()


def _main_database_path(conn):
    for row in conn.execute("PRAGMA database_list").fetchall():
        if row["name"] == "main" and row["file"]:
            return Path(row["file"])
    return None


def integrity_check(conn):
    """Return SQLite integrity_check rows for the active database."""
    return [row[0] for row in conn.execute("PRAGMA integrity_check").fetchall()]


def _integrity_check_connection(conn):
    return [row[0] for row in conn.execute("PRAGMA integrity_check").fetchall()]


def _delete_sqlite_file_set(db_path):
    for path in (db_path, Path(f"{db_path}-wal"), Path(f"{db_path}-shm")):
        try:
            path.unlink()
        except FileNotFoundError:
            pass


def backup_database(conn, dest_path):
    """Create a SQLite-safe snapshot of the live database.

    This avoids the WAL-mode footgun of copying only flow.db while committed
    pages may still live in flow.db-wal.
    """
    dest_path = Path(dest_path)
    source_path = _main_database_path(conn)
    if source_path is not None and dest_path.resolve() == source_path.resolve():
        # INVARIANT: existence
        raise FlowError("backup destination must be different from the source database")
    if dest_path.exists():
        # INVARIANT: existence
        raise FlowError(f"backup destination already exists: {dest_path}")
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = tempfile.NamedTemporaryFile(
        delete=False,
        dir=dest_path.parent,
        prefix=f".{dest_path.name}.",
        suffix=".tmp",
    )
    tmp_path = Path(tmp.name)
    tmp.close()
    published = False
    try:
        dest = sqlite3.connect(tmp_path)
        try:
            conn.backup(dest)
            dest.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            dest.execute("PRAGMA journal_mode=DELETE")
            result = _integrity_check_connection(dest)
        finally:
            dest.close()
        if result != ["ok"]:
            # INVARIANT: existence
            raise FlowError(f"backup integrity check failed: {'; '.join(result)}")
        try:
            os.link(tmp_path, dest_path)
        except FileExistsError:
            # INVARIANT: existence
            raise FlowError(f"backup destination already exists: {dest_path}")
        _delete_sqlite_file_set(tmp_path)
        published = True
    finally:
        if not published:
            _delete_sqlite_file_set(tmp_path)
    return dest_path


# --- markdown projection (one-way) -----------------------------------------


def project(conn, task_id):
    """Render a task's baton to .flow/batons/<id>.md. Database stays the truth."""
    t = _task(conn, task_id)
    _, entries = context(conn, task_id)
    out = conn.execute("PRAGMA database_list").fetchone()
    db_file = Path(out["file"]) if out and out["file"] else None
    if db_file is None:
        return  # in-memory db: nothing to project
    batons = db_file.parent / "batons"
    batons.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# Baton — task {t['id']}",
        "",
        f"- **state**: {t['state']}",
        f"- **assignee**: {t['assignee'] or '—'}",
        f"- **label**: {t['label'] or '—'}",
        f"- **parent**: {t['parent_id'] or '—'}",
        f"- **outcome**: {t['outcome'] or '—'}",
        "",
        f"> {t['text']}",
        "",
        "## Context",
        "",
    ]
    for e in entries:
        lines.append(f"- `{e['created_at']}` **{e['kind']}**: {e['text']}")
    (batons / f"{t['id']}.md").write_text("\n".join(lines) + "\n")


# --- CLI -------------------------------------------------------------------


def _print_task(t):
    print(f"#{t['id']} [{t['state']}] {t['text']}")


def main(argv=None, db_path=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(prog="flow", description="Baton Flow runtime")
    parser.add_argument("--db", default=db_path or ".flow/flow.db")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("add", help="create a task")
    p.add_argument("text")
    p.add_argument("--label")

    p = sub.add_parser("next", help="claim the next runnable task")
    p.add_argument("--session", "--assignee", dest="assignee")

    p = sub.add_parser("context", help="read a task's baton")
    p.add_argument("id", type=int)

    p = sub.add_parser("note", help="append to the baton")
    p.add_argument("id", type=int)
    p.add_argument("text")

    p = sub.add_parser("done", help="complete a task")
    p.add_argument("id", type=int)
    p.add_argument("outcome")
    p.add_argument("--session", "--assignee", dest="session")

    p = sub.add_parser("escalate", help="park a task waiting on a human")
    p.add_argument("id", type=int)
    p.add_argument("question")
    p.add_argument("--session", "--assignee", dest="session")

    p = sub.add_parser("split", help="spawn children; park the parent")
    p.add_argument("id", type=int)
    p.add_argument("children", nargs="+")
    p.add_argument("--session", "--assignee", dest="session")

    p = sub.add_parser("decide", help="record a decision")
    p.add_argument("id", type=int)
    p.add_argument("text")

    p = sub.add_parser("reply", help="(human) answer a blocked task")
    p.add_argument("id", type=int)
    p.add_argument("text")

    p = sub.add_parser("reopen", help="reopen a done task")
    p.add_argument("id", type=int)

    sub.add_parser("list", help="list all tasks")

    p = sub.add_parser("backup", help="write a SQLite-safe database backup")
    p.add_argument("path")

    sub.add_parser("check", help="run SQLite integrity_check")

    args = parser.parse_args(argv)
    db_path = Path(args.db)
    if args.cmd in {"backup", "check"}:
        try:
            conn = connect_existing_readonly(db_path)
            try:
                return _dispatch(conn, args)
            finally:
                conn.close()
        except FlowError as e:
            print(f"error: {e}", file=sys.stderr)
            return 1

    conn = connect(db_path)
    try:
        return _dispatch(conn, args)
    except FlowError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    finally:
        conn.close()


def _dispatch(conn, args):
    if args.cmd == "add":
        print(add(conn, args.text, label=args.label))
    elif args.cmd == "next":
        t = next_task(conn, assignee=args.assignee)
        if t is None:
            print("none")
            return 0
        _print_task(t)
    elif args.cmd == "context":
        t, entries = context(conn, args.id)
        _print_task(t)
        for e in entries:
            print(f"  [{e['kind']}] {e['text']}")
    elif args.cmd == "note":
        note(conn, args.id, args.text)
    elif args.cmd == "done":
        done(conn, args.id, args.outcome, session=args.session)
    elif args.cmd == "escalate":
        escalate(conn, args.id, args.question, session=args.session)
    elif args.cmd == "split":
        print(split(conn, args.id, args.children, session=args.session))
    elif args.cmd == "decide":
        decide(conn, args.id, args.text)
    elif args.cmd == "reply":
        reply(conn, args.id, args.text)
    elif args.cmd == "reopen":
        reopen(conn, args.id)
    elif args.cmd == "list":
        for t in list_tasks(conn):
            _print_task(t)
    elif args.cmd == "backup":
        path = backup_database(conn, Path(args.path))
        print(f"backup written to {path}")
    elif args.cmd == "check":
        result = integrity_check(conn)
        for line in result:
            print(line)
        return 0 if result == ["ok"] else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
