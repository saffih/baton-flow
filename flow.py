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
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

STATES = ("pending", "in_progress", "blocked", "done")


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# --- storage ---------------------------------------------------------------

SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    text       TEXT NOT NULL,
    state      TEXT NOT NULL DEFAULT 'pending',
    assignee   TEXT,
    type       TEXT,
    parent_id  INTEGER REFERENCES tasks(id),
    outcome    TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
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
"""


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(SCHEMA)
    return conn


# --- core operations -------------------------------------------------------


class FlowError(Exception):
    """A rule violation the runner should see and handle, not a crash."""


def _task(conn, task_id):
    row = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
    if row is None:
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


def _maybe_wake(conn, task_id):
    """If a blocked task has no remaining unmet dependencies, wake it to pending."""
    t = _task(conn, task_id)
    if t["state"] == "blocked" and not _is_blocked(conn, task_id):
        _set_state(conn, task_id, "pending")
        _append(conn, task_id, "system", "woken: all dependencies resolved")


def add(conn, text, assignee=None, type=None, parent_id=None):
    cur = conn.execute(
        "INSERT INTO tasks (text, state, assignee, type, parent_id, created_at, updated_at)"
        " VALUES (?, 'pending', ?, ?, ?, ?, ?)",
        (text, assignee, type, parent_id, now(), now()),
    )
    task_id = cur.lastrowid
    _append(conn, task_id, "system", f"created: {text}")
    conn.commit()
    project(conn, task_id)
    return task_id


def next_task(conn, assignee=None):
    """Claim the oldest runnable task. Unassigned tasks are a shared pool."""
    if assignee:
        row = conn.execute(
            "SELECT * FROM tasks WHERE state='pending' AND (assignee=? OR assignee IS NULL)"
            " ORDER BY id LIMIT 1",
            (assignee,),
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT * FROM tasks WHERE state='pending' ORDER BY id LIMIT 1"
        ).fetchone()
    if row is None:
        return None
    if assignee and row["assignee"] is None:
        conn.execute("UPDATE tasks SET assignee=? WHERE id=?", (assignee, row["id"]))
    _set_state(conn, row["id"], "in_progress")
    conn.commit()
    project(conn, row["id"])
    return _task(conn, row["id"])


def context(conn, task_id):
    t = _task(conn, task_id)
    entries = conn.execute(
        "SELECT kind, text, created_at FROM baton_entries WHERE task_id=? ORDER BY id",
        (task_id,),
    ).fetchall()
    return t, entries


def note(conn, task_id, text):
    _task(conn, task_id)
    _append(conn, task_id, "note", text)
    conn.commit()
    project(conn, task_id)


def decide(conn, task_id, text):
    _task(conn, task_id)
    _append(conn, task_id, "decision", text)
    conn.commit()
    project(conn, task_id)


def escalate(conn, task_id, question):
    _task(conn, task_id)
    conn.execute(
        "INSERT INTO escalations (task_id, question, created_at) VALUES (?,?,?)",
        (task_id, question, now()),
    )
    _append(conn, task_id, "escalation", question)
    _set_state(conn, task_id, "blocked")
    conn.commit()
    project(conn, task_id)


def split(conn, task_id, child_texts):
    parent = _task(conn, task_id)
    child_ids = []
    for text in child_texts:
        cid = conn.execute(
            "INSERT INTO tasks (text, state, assignee, parent_id, created_at, updated_at)"
            " VALUES (?, 'pending', ?, ?, ?, ?)",
            (text, parent["assignee"], task_id, now(), now()),
        ).lastrowid
        _append(conn, cid, "system", f"created as child of task {task_id}")
        child_ids.append(cid)
    _append(conn, task_id, "split", f"split into tasks {child_ids}")
    _set_state(conn, task_id, "blocked")
    conn.commit()
    project(conn, task_id)
    for cid in child_ids:
        project(conn, cid)
    return child_ids


def done(conn, task_id, outcome):
    _task(conn, task_id)
    if _is_blocked(conn, task_id):
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
    conn.commit()
    project(conn, task_id)
    if parent_id is not None:
        _maybe_wake(conn, parent_id)
        conn.commit()
        project(conn, parent_id)


def reply(conn, task_id, text):
    """Human answers a blocked task. Records the reply on the baton, closes the
    open escalation, and wakes the task. The runner decides on pickup whether the
    reply is about this task (continue) or new scope (a fresh `add`)."""
    _task(conn, task_id)
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
    conn.commit()
    _maybe_wake(conn, task_id)
    conn.commit()
    project(conn, task_id)


def reopen(conn, task_id):
    t = _task(conn, task_id)
    if t["state"] != "done":
        raise FlowError(f"task {task_id} is not done (state={t['state']})")
    _set_state(conn, task_id, "pending")
    _append(conn, task_id, "system", "reopened")
    conn.commit()
    project(conn, task_id)


def list_tasks(conn):
    return conn.execute("SELECT * FROM tasks ORDER BY id").fetchall()


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
        f"- **type**: {t['type'] or '—'}",
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
    p.add_argument("--assignee")
    p.add_argument("--type")

    p = sub.add_parser("next", help="claim the next runnable task")
    p.add_argument("--assignee")

    p = sub.add_parser("context", help="read a task's baton")
    p.add_argument("id", type=int)

    p = sub.add_parser("note", help="append to the baton")
    p.add_argument("id", type=int)
    p.add_argument("text")

    p = sub.add_parser("done", help="complete a task")
    p.add_argument("id", type=int)
    p.add_argument("outcome")

    p = sub.add_parser("escalate", help="park a task waiting on a human")
    p.add_argument("id", type=int)
    p.add_argument("question")

    p = sub.add_parser("split", help="spawn children; park the parent")
    p.add_argument("id", type=int)
    p.add_argument("children", nargs="+")

    p = sub.add_parser("decide", help="record a decision")
    p.add_argument("id", type=int)
    p.add_argument("text")

    p = sub.add_parser("reply", help="(human) answer a blocked task")
    p.add_argument("id", type=int)
    p.add_argument("text")

    p = sub.add_parser("reopen", help="reopen a done task")
    p.add_argument("id", type=int)

    sub.add_parser("list", help="list all tasks")

    args = parser.parse_args(argv)
    conn = connect(Path(args.db))
    try:
        return _dispatch(conn, args)
    except FlowError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    finally:
        conn.close()


def _dispatch(conn, args):
    if args.cmd == "add":
        print(add(conn, args.text, assignee=args.assignee, type=args.type))
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
        done(conn, args.id, args.outcome)
    elif args.cmd == "escalate":
        escalate(conn, args.id, args.question)
    elif args.cmd == "split":
        print(split(conn, args.id, args.children))
    elif args.cmd == "decide":
        decide(conn, args.id, args.text)
    elif args.cmd == "reply":
        reply(conn, args.id, args.text)
    elif args.cmd == "reopen":
        reopen(conn, args.id)
    elif args.cmd == "list":
        for t in list_tasks(conn):
            _print_task(t)
    return 0


if __name__ == "__main__":
    sys.exit(main())
