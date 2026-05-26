"""HTTP API + Web UI (HLD-021, HLD-017).

Dependency-free REST server built on the stdlib http.server. All endpoints
return JSON; the root path serves a minimal browser UI that consumes them.
The server reads/writes exclusively through the Database API.

Routes:
  GET    /                     Web UI
  GET    /api/health           health status
  GET    /api/metrics          task/session counts
  GET    /api/tasks            list tasks (?status=&priority=&limit=)
  POST   /api/tasks            create task {content, ...}
  GET    /api/tasks/{id}       task detail
  PUT    /api/tasks/{id}       update task
  DELETE /api/tasks/{id}       archive task (soft delete)
  POST   /api/tasks/{id}/done  mark done {outcome}
  GET    /api/reports          list reports
  POST   /api/reports          create report
  GET    /api/reports/{id}     report detail
  GET    /api/sessions         list active sessions
"""

from __future__ import annotations

import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable, Optional

from flow_runtime.config import resolve_env
from flow_runtime.database import Database, DatabaseError

Route = tuple[str, re.Pattern[str], Callable[..., Any]]


class FlowAPI:
    """Routing + handlers, decoupled from the HTTP transport for testability."""

    def __init__(self, db: Database) -> None:
        self.db = db
        self.routes: list[Route] = [
            ("GET", re.compile(r"^/api/health$"), self.health),
            ("GET", re.compile(r"^/api/metrics$"), self.metrics),
            ("GET", re.compile(r"^/api/tasks$"), self.list_tasks),
            ("POST", re.compile(r"^/api/tasks$"), self.create_task),
            ("POST", re.compile(r"^/api/tasks/(?P<id>\d+)/done$"), self.task_done),
            ("GET", re.compile(r"^/api/tasks/(?P<id>\d+)$"), self.get_task),
            ("PUT", re.compile(r"^/api/tasks/(?P<id>\d+)$"), self.update_task),
            ("DELETE", re.compile(r"^/api/tasks/(?P<id>\d+)$"), self.delete_task),
            ("GET", re.compile(r"^/api/reports$"), self.list_reports),
            ("POST", re.compile(r"^/api/reports$"), self.create_report),
            ("GET", re.compile(r"^/api/reports/(?P<id>\d+)$"), self.get_report),
            ("GET", re.compile(r"^/api/sessions$"), self.list_sessions),
        ]

    def dispatch(
        self, method: str, path: str, query: dict[str, str], body: dict[str, Any]
    ) -> tuple[int, Any]:
        for m, pattern, handler in self.routes:
            if m != method:
                continue
            match = pattern.match(path)
            if match:
                try:
                    return handler(query=query, body=body, **match.groupdict())
                except DatabaseError as exc:
                    return 400, {"error": str(exc)}
        return 404, {"error": "not found", "path": path}

    # --- handlers --------------------------------------------------------------

    def health(self, **_: Any) -> tuple[int, Any]:
        h = self.db.health_check()
        return (200 if h["status"] == "healthy" else 503), h

    def metrics(self, **_: Any) -> tuple[int, Any]:
        return 200, {
            "tasks": {
                "pending": self.db.get_task_count_for_ui(status="pending"),
                "in_progress": self.db.get_task_count_for_ui(status="in-progress"),
                "done": self.db.get_task_count_for_ui(status="done"),
                "total_active": self.db.get_task_count_for_ui(),
            },
            "sessions_active": len(self.db.list_sessions("active")),
        }

    def list_tasks(self, query: dict[str, str], **_: Any) -> tuple[int, Any]:
        tasks = self.db.list_tasks(
            status=query.get("status"),
            priority=query.get("priority"),
            archived=query.get("archived") == "true",
            limit=int(query["limit"]) if "limit" in query else None,
        )
        return 200, {"tasks": tasks, "total": len(tasks)}

    def create_task(self, body: dict[str, Any], **_: Any) -> tuple[int, Any]:
        content = body.get("content")
        if not content:
            return 400, {"error": "content is required"}
        kwargs = {k: v for k, v in body.items() if k != "content"}
        tid = self.db.add_task(content, **kwargs)
        return 201, {"id": tid, **(self.db.get_task(tid) or {})}

    def get_task(self, id: str, **_: Any) -> tuple[int, Any]:  # noqa: A002
        task = self.db.get_task(int(id))
        return (200, task) if task else (404, {"error": "task not found", "id": id})

    def update_task(self, id: str, body: dict[str, Any], **_: Any) -> tuple[int, Any]:  # noqa: A002
        if not self.db.get_task(int(id)):
            return 404, {"error": "task not found", "id": id}
        self.db.update_task(int(id), **body)
        return 200, self.db.get_task(int(id))

    def delete_task(self, id: str, **_: Any) -> tuple[int, Any]:  # noqa: A002
        if not self.db.get_task(int(id)):
            return 404, {"error": "task not found", "id": id}
        self.db.update_task(int(id), archived=1)
        return 200, {"deleted": True, "id": int(id)}

    def task_done(self, id: str, body: dict[str, Any], **_: Any) -> tuple[int, Any]:  # noqa: A002
        if not self.db.get_task(int(id)):
            return 404, {"error": "task not found", "id": id}
        self.db.mark_task_done(int(id), body.get("outcome", ""))
        return 200, self.db.get_task(int(id))

    def list_reports(self, query: dict[str, str], **_: Any) -> tuple[int, Any]:
        reports = self.db.list_reports(
            status=query.get("status"), report_type=query.get("report_type")
        )
        return 200, {"reports": reports, "total": len(reports)}

    def create_report(self, body: dict[str, Any], **_: Any) -> tuple[int, Any]:
        if not body.get("title"):
            return 400, {"error": "title is required"}
        rid = self.db.add_report(body)
        return 201, {"id": rid, **(self.db.get_report(rid) or {})}

    def get_report(self, id: str, **_: Any) -> tuple[int, Any]:  # noqa: A002
        report = self.db.get_report(int(id))
        return (200, report) if report else (404, {"error": "report not found", "id": id})

    def list_sessions(self, **_: Any) -> tuple[int, Any]:
        sessions = self.db.list_sessions("active")
        return 200, {"sessions": sessions, "total": len(sessions)}


def _make_handler(api: FlowAPI) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *args: Any) -> None:  # silence default logging
            pass

        def _send(self, status: int, payload: Any, content_type: str = "application/json") -> None:
            if content_type == "application/json":
                data = json.dumps(payload, default=str).encode()
            else:
                data = payload.encode() if isinstance(payload, str) else payload
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()
            self.wfile.write(data)

        def _route(self, method: str) -> None:
            path, _, raw_query = self.path.partition("?")
            if method == "GET" and path == "/":
                self._send(200, WEB_UI, content_type="text/html; charset=utf-8")
                return
            query = {}
            for pair in raw_query.split("&"):
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    query[k] = v
            body: dict[str, Any] = {}
            length = int(self.headers.get("Content-Length", 0) or 0)
            if length:
                try:
                    body = json.loads(self.rfile.read(length).decode() or "{}")
                except json.JSONDecodeError:
                    self._send(400, {"error": "invalid JSON body"})
                    return
            status, payload = api.dispatch(method, path, query, body)
            self._send(status, payload)

        def do_OPTIONS(self) -> None:
            self._send(204, "")

        def do_GET(self) -> None:
            self._route("GET")

        def do_POST(self) -> None:
            self._route("POST")

        def do_PUT(self) -> None:
            self._route("PUT")

        def do_DELETE(self) -> None:
            self._route("DELETE")

    return Handler


def make_server(host: str = "127.0.0.1", port: Optional[int] = None, env: str | None = None) -> ThreadingHTTPServer:
    cfg = resolve_env(env)
    db = Database(cfg.db_path)
    api = FlowAPI(db)
    return ThreadingHTTPServer((host, port if port is not None else cfg.port), _make_handler(api))


def main(argv: list[str] | None = None) -> int:
    import argparse

    p = argparse.ArgumentParser(prog="flow-ui", description="Flow HTTP API + Web UI")
    p.add_argument("--env", default=None)
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=None)
    args = p.parse_args(argv)
    server = make_server(args.host, args.port, args.env)
    host, port = server.server_address
    print(f"Flow UI on http://{host}:{port}  (env={resolve_env(args.env).name})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
    return 0


WEB_UI = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Flow</title>
<style>
  body { font-family: -apple-system, system-ui, sans-serif; margin: 0; background: #0f1115; color: #e6e6e6; }
  header { padding: 16px 24px; background: #161922; border-bottom: 1px solid #262b36; display: flex; align-items: center; gap: 16px; }
  h1 { font-size: 18px; margin: 0; }
  #metrics { display: flex; gap: 16px; font-size: 13px; color: #9aa4b2; }
  #metrics b { color: #e6e6e6; }
  main { padding: 24px; max-width: 900px; margin: 0 auto; }
  form { display: flex; gap: 8px; margin-bottom: 24px; }
  input, select, button { padding: 8px 12px; border-radius: 6px; border: 1px solid #2c3340; background: #1b1f29; color: #e6e6e6; font-size: 14px; }
  button { background: #3b82f6; border-color: #3b82f6; cursor: pointer; }
  button:hover { background: #2f6fd6; }
  .task { display: flex; align-items: center; gap: 12px; padding: 12px 16px; background: #161922; border: 1px solid #262b36; border-radius: 8px; margin-bottom: 8px; }
  .task .title { flex: 1; }
  .badge { font-size: 11px; padding: 2px 8px; border-radius: 12px; background: #2c3340; }
  .badge.done { background: #166534; }
  .badge.pending { background: #92580c; }
  .badge.in-progress { background: #1e40af; }
  .task button { padding: 4px 10px; font-size: 12px; background: #2c3340; border-color: #2c3340; }
  .muted { color: #6b7280; font-size: 13px; }
</style>
</head>
<body>
<header>
  <h1>Flow</h1>
  <div id="metrics"></div>
</header>
<main>
  <form id="add-form">
    <input id="content" placeholder="New task..." style="flex:1" required>
    <select id="priority">
      <option value="normal">normal</option>
      <option value="high">high</option>
      <option value="low">low</option>
    </select>
    <button type="submit">Add</button>
  </form>
  <div id="tasks"></div>
</main>
<script>
async function api(method, path, body) {
  const opts = { method, headers: { 'Content-Type': 'application/json' } };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(path, opts);
  return res.json();
}
async function refresh() {
  const m = await api('GET', '/api/metrics');
  document.getElementById('metrics').innerHTML =
    `pending <b>${m.tasks.pending}</b>` +
    ` &middot; in-progress <b>${m.tasks.in_progress}</b>` +
    ` &middot; done <b>${m.tasks.done}</b>` +
    ` &middot; sessions <b>${m.sessions_active}</b>`;
  const { tasks } = await api('GET', '/api/tasks');
  const el = document.getElementById('tasks');
  if (!tasks.length) { el.innerHTML = '<p class="muted">No tasks yet.</p>'; return; }
  el.innerHTML = tasks.map(t => `
    <div class="task" data-id="${t.id}">
      <span class="badge ${t.status}">${t.status}</span>
      <span class="title">${(t.title || t.content || '').replace(/</g,'&lt;')}</span>
      <span class="muted">${t.priority}</span>
      ${t.status !== 'done' ? `<button onclick="markDone(${t.id})">Done</button>` : ''}
      <button onclick="del(${t.id})">Archive</button>
    </div>`).join('');
}
async function markDone(id) { await api('POST', `/api/tasks/${id}/done`, { outcome: 'completed via UI' }); refresh(); }
async function del(id) { await api('DELETE', `/api/tasks/${id}`); refresh(); }
document.getElementById('add-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const content = document.getElementById('content').value.trim();
  if (!content) return;
  await api('POST', '/api/tasks', { content, priority: document.getElementById('priority').value, title: content });
  document.getElementById('content').value = '';
  refresh();
});
refresh();
setInterval(refresh, 5000);
</script>
</body>
</html>"""


if __name__ == "__main__":
    raise SystemExit(main())
