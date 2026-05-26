"""Flow CLI (HLD-020).

Command grammar: ``flow <entity> <action> [identifier] [options]``.
All AI-to-system communication goes through this surface — never direct DB
access. ``--json`` emits machine-readable output; ``--env`` / FLOW_ENV select
the environment-isolated database.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Optional

from flow_runtime.config import resolve_env
from flow_runtime.database import Database, DatabaseError


def _db(args: argparse.Namespace) -> Database:
    cfg = resolve_env(getattr(args, "env", None))
    return Database(cfg.db_path)


def _emit(args: argparse.Namespace, human: str, payload: Any) -> None:
    if getattr(args, "json", False):
        print(json.dumps(payload, default=str, indent=2))
    else:
        print(human)


def _kv_options(pairs: list[str]) -> dict[str, Any]:
    """Parse trailing ``--key value`` option pairs into a dict."""
    out: dict[str, Any] = {}
    i = 0
    while i < len(pairs):
        token = pairs[i]
        if token.startswith("--"):
            key = token[2:].replace("-", "_")
            if i + 1 < len(pairs) and not pairs[i + 1].startswith("--"):
                out[key] = pairs[i + 1]
                i += 2
            else:
                out[key] = True
                i += 1
        else:
            i += 1
    return out


# --- command handlers ---------------------------------------------------------


def cmd_add(args: argparse.Namespace) -> int:
    db = _db(args)
    opts = _kv_options(args.options)
    if args.entity == "task":
        tid = db.add_task(args.value, **opts)
        _emit(args, f"Created task {tid}", {"id": tid})
        return 0
    if args.entity == "hint":
        hid = db.add_hint(args.value, **opts)
        _emit(args, f"Created hint {hid}", {"id": hid})
        return 0
    if args.entity == "report":
        report = {"title": opts.get("title", args.value or "untitled"), **opts}
        rid = db.add_report(report)
        _emit(args, f"Created report {rid}", {"id": rid})
        return 0
    print(f"add: unknown entity '{args.entity}'", file=sys.stderr)
    return 2


def cmd_list(args: argparse.Namespace) -> int:
    db = _db(args)
    opts = _kv_options(args.options)
    if args.entity == "tasks":
        rows = db.list_tasks(
            status=opts.get("status"),
            priority=opts.get("priority"),
            archived=bool(opts.get("archived", False)),
            limit=int(opts["limit"]) if "limit" in opts else None,
        )
        _emit(args, _fmt_tasks(rows), rows)
        return 0
    if args.entity == "hints":
        rows = db.list_hints(status=opts.get("status"), priority=opts.get("priority"))
        _emit(args, "\n".join(f"[{r['id']}] {r['content']}" for r in rows) or "(no hints)", rows)
        return 0
    if args.entity == "reports":
        rows = db.list_reports(status=opts.get("status"), report_type=opts.get("report_type"))
        _emit(args, "\n".join(f"[{r['id']}] {r['title']} ({r['report_type']})" for r in rows) or "(no reports)", rows)
        return 0
    if args.entity == "sessions":
        rows = db.list_sessions(status=opts.get("status", "active"))
        _emit(args, "\n".join(f"{r['name']} ({r['status']})" for r in rows) or "(no sessions)", rows)
        return 0
    print(f"list: unknown entity '{args.entity}'", file=sys.stderr)
    return 2


def cmd_get(args: argparse.Namespace) -> int:
    db = _db(args)
    ident = int(args.identifier) if args.entity != "session" else args.identifier
    getter = {"task": db.get_task, "hint": db.get_hint, "report": db.get_report, "session": db.get_session}.get(
        args.entity
    )
    if getter is None:
        print(f"get: unknown entity '{args.entity}'", file=sys.stderr)
        return 2
    row = getter(ident)
    if row is None:
        _emit(args, f"{args.entity} {ident} not found", None)
        return 1
    _emit(args, "\n".join(f"{k}: {v}" for k, v in row.items()), row)
    return 0


def cmd_update(args: argparse.Namespace) -> int:
    db = _db(args)
    opts = _kv_options(args.options)
    ident = int(args.identifier)
    if args.entity == "task":
        db.update_task(ident, **opts)
    elif args.entity == "hint":
        db.update_hint(ident, **opts)
    elif args.entity == "report":
        db.update_report(ident, **opts)
    else:
        print(f"update: unknown entity '{args.entity}'", file=sys.stderr)
        return 2
    _emit(args, f"Updated {args.entity} {ident}", {"id": ident, "updated": opts})
    return 0


def cmd_mark(args: argparse.Namespace) -> int:
    db = _db(args)
    opts = _kv_options(args.options)
    ident = int(args.identifier)
    if args.state == "done":
        db.mark_task_done(ident, opts.get("outcome", ""))
        _emit(args, f"Task {ident} marked done", {"id": ident, "status": "done"})
        return 0
    if args.state in ("acknowledged", "ack"):
        db.mark_task_acknowledged(ident, opts.get("reason", ""))
        _emit(args, f"Task {ident} acknowledged", {"id": ident, "status": "ack"})
        return 0
    print(f"mark: unknown state '{args.state}'", file=sys.stderr)
    return 2


def cmd_reserve(args: argparse.Namespace) -> int:
    db = _db(args)
    opts = _kv_options(args.options)
    session = opts.get("session", "")
    ok = db.reserve_task(int(args.identifier), session)
    _emit(args, "reserved" if ok else "already taken", {"reserved": ok})
    return 0 if ok else 1


def cmd_release(args: argparse.Namespace) -> int:
    db = _db(args)
    opts = _kv_options(args.options)
    ok = db.release_task(int(args.identifier), opts.get("session", ""))
    _emit(args, "released" if ok else "not held by session", {"released": ok})
    return 0 if ok else 1


def cmd_append(args: argparse.Namespace) -> int:
    db = _db(args)
    opts = _kv_options(args.options)
    ok = db.append_to_report(int(args.identifier), opts.get("content", ""))
    _emit(args, "appended" if ok else "report not found", {"appended": ok})
    return 0 if ok else 1


def cmd_health(args: argparse.Namespace) -> int:
    db = _db(args)
    h = db.health_check()
    _emit(args, f"status: {h['status']} | db: {h['db_path']}", h)
    return 0 if h["status"] == "healthy" else 1


def cmd_sync(args: argparse.Namespace) -> int:
    from flow_runtime.storage import Storage, project_all

    db = _db(args)
    storage = Storage(args.root) if args.root else Storage()
    result = project_all(db, storage)
    human = f"synced {result['written']} file(s) to {result['root']}"
    if result["errors"]:
        human += f" ({len(result['errors'])} error(s))"
    _emit(args, human, result)
    return 0 if not result["errors"] else 1


def cmd_serve(args: argparse.Namespace) -> int:
    from flow_runtime.server import main as serve_main

    serve_argv: list[str] = []
    if getattr(args, "env", None):
        serve_argv += ["--env", args.env]
    if args.port is not None:
        serve_argv += ["--port", str(args.port)]
    if args.host:
        serve_argv += ["--host", args.host]
    return serve_main(serve_argv)


def cmd_status(args: argparse.Namespace) -> int:
    db = _db(args)
    payload = {
        "pending": db.get_task_count_for_ui(status="pending"),
        "in_progress": db.get_task_count_for_ui(status="in-progress"),
        "done": db.get_task_count_for_ui(status="done"),
        "total_active": db.get_task_count_for_ui(),
        "sessions": len(db.list_sessions("active")),
    }
    human = " | ".join(f"{k}={v}" for k, v in payload.items())
    _emit(args, human, payload)
    return 0


# --- formatting ---------------------------------------------------------------


def _fmt_tasks(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "(no tasks)"
    lines = []
    for r in rows:
        title = r.get("title") or (r.get("content") or "")[:50]
        lines.append(f"[{r['id']:>4}] {r['status']:<12} {r.get('priority','normal'):<8} {title}")
    return "\n".join(lines)


# --- parser -------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="flow", description="Flow task system CLI")
    p.add_argument("--json", action="store_true", help="machine-readable JSON output")
    p.add_argument("--env", default=None, help="environment: production|test|development")
    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("add")
    sp.add_argument("entity")
    sp.add_argument("value", nargs="?", default="")
    sp.add_argument("options", nargs=argparse.REMAINDER, default=[])
    sp.set_defaults(func=cmd_add)

    sp = sub.add_parser("list")
    sp.add_argument("entity")
    sp.add_argument("options", nargs=argparse.REMAINDER, default=[])
    sp.set_defaults(func=cmd_list)

    sp = sub.add_parser("get")
    sp.add_argument("entity")
    sp.add_argument("identifier")
    sp.add_argument("options", nargs=argparse.REMAINDER, default=[])
    sp.set_defaults(func=cmd_get)

    sp = sub.add_parser("update")
    sp.add_argument("entity")
    sp.add_argument("identifier")
    sp.add_argument("options", nargs=argparse.REMAINDER, default=[])
    sp.set_defaults(func=cmd_update)

    sp = sub.add_parser("mark")
    sp.add_argument("entity")  # always "task"
    sp.add_argument("state")   # done | acknowledged
    sp.add_argument("identifier")
    sp.add_argument("options", nargs=argparse.REMAINDER, default=[])
    sp.set_defaults(func=cmd_mark)

    sp = sub.add_parser("reserve")
    sp.add_argument("entity")
    sp.add_argument("identifier")
    sp.add_argument("options", nargs=argparse.REMAINDER, default=[])
    sp.set_defaults(func=cmd_reserve)

    sp = sub.add_parser("release")
    sp.add_argument("entity")
    sp.add_argument("identifier")
    sp.add_argument("options", nargs=argparse.REMAINDER, default=[])
    sp.set_defaults(func=cmd_release)

    sp = sub.add_parser("append")
    sp.add_argument("entity")  # "report"
    sp.add_argument("identifier")
    sp.add_argument("options", nargs=argparse.REMAINDER, default=[])
    sp.set_defaults(func=cmd_append)

    sp = sub.add_parser("health")
    sp.add_argument("action", nargs="?", default="check")
    sp.add_argument("options", nargs=argparse.REMAINDER, default=[])
    sp.set_defaults(func=cmd_health)

    sp = sub.add_parser("status")
    sp.add_argument("options", nargs=argparse.REMAINDER, default=[])
    sp.set_defaults(func=cmd_status)

    sp = sub.add_parser("sync", help="project database to markdown")
    sp.add_argument("--root", default=None)
    sp.set_defaults(func=cmd_sync)

    sp = sub.add_parser("serve", help="start HTTP API + Web UI")
    sp.add_argument("--port", type=int, default=None)
    sp.add_argument("--host", default="127.0.0.1")
    sp.set_defaults(func=cmd_serve)

    return p


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except DatabaseError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
