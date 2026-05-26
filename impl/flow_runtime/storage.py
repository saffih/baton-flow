"""Storage API + one-way markdown projection (HLD-022, HLD-014).

The Storage API owns markdown files under a storage root, one directory per
table. Sync is strictly one-way: database -> markdown. Markdown is never read
back to mutate the database. Sync failures are non-blocking by contract, so
project_all swallows per-entity errors and reports them rather than raising.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from flow_runtime.database import Database

# Tables that get projected to markdown and their directory names.
_PROJECTED = {
    "tasks": "tasks",
    "reports": "reports",
}


class Storage:
    """Markdown file storage for projected database entities."""

    def __init__(self, root: str = ".flow/markdown") -> None:
        self.root = Path(root)

    # --- low-level file ops (HLD-022) -----------------------------------------

    def get_table_directory(self, table: str) -> str:
        return str(self.root / table)

    def get_file_path(self, table: str, item_id: int) -> str:
        return str(self.root / table / f"{item_id}.md")

    def write_file(self, table: str, item_id: int, content: str) -> str:
        path = Path(self.get_file_path(table, item_id))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return str(path)

    def read_file(self, table: str, item_id: int) -> Optional[str]:
        path = Path(self.get_file_path(table, item_id))
        return path.read_text(encoding="utf-8") if path.exists() else None

    def delete_file(self, table: str, item_id: int) -> bool:
        path = Path(self.get_file_path(table, item_id))
        if path.exists():
            path.unlink()
            return True
        return False

    def file_exists(self, table: str, item_id: int) -> bool:
        return Path(self.get_file_path(table, item_id)).exists()


# --- markdown rendering -------------------------------------------------------


def render_task(task: dict[str, Any]) -> str:
    title = task.get("title") or (task.get("content") or "")[:60]
    lines = [
        f"# Task {task['id']}: {title}",
        "",
        f"- **Status**: {task.get('status')}",
        f"- **Priority**: {task.get('priority')}",
        f"- **Assignee**: {task.get('assignee') or '_unassigned_'}",
        f"- **Created**: {task.get('created_at')}",
        f"- **Updated**: {task.get('updated_at')}",
    ]
    if task.get("taken_by"):
        lines.append(f"- **Reserved by**: {task['taken_by']}")
    if task.get("done_at"):
        lines.append(f"- **Done at**: {task['done_at']}")
    lines += ["", "## Content", "", task.get("content") or ""]
    if task.get("outcome"):
        lines += ["", "## Outcome", "", task["outcome"]]
    return "\n".join(lines) + "\n"


def render_report(report: dict[str, Any]) -> str:
    lines = [
        f"# Report {report['id']}: {report.get('title')}",
        "",
        f"- **Type**: {report.get('report_type')}",
        f"- **Status**: {report.get('status')}",
        f"- **Lifecycle**: {report.get('lifecycle_state')}",
        f"- **Task**: {report.get('task_id') or '_none_'}",
        f"- **Created**: {report.get('created_at')}",
        "",
        "## Content",
        "",
        report.get("content") or "",
    ]
    return "\n".join(lines) + "\n"


_RENDERERS = {"tasks": render_task, "reports": render_report}


def render_status(db: Database) -> str:
    """Render flow-status.md — the summary core.md reads (HLD-014)."""
    tasks = db.list_tasks(limit=200)
    pending = [t for t in tasks if t["status"] == "pending"]
    in_progress = [t for t in tasks if t["status"] == "in-progress"]
    lines = [
        "# Flow Status",
        "",
        f"- Pending: {len(pending)}",
        f"- In progress: {len(in_progress)}",
        f"- Active sessions: {len(db.list_sessions('active'))}",
        "",
        "## Open tasks",
        "",
    ]
    for t in pending + in_progress:
        title = t.get("title") or (t.get("content") or "")[:60]
        lines.append(f"- [{t['id']}] ({t['status']}/{t['priority']}) {title}")
    if not (pending or in_progress):
        lines.append("_No open tasks._")
    return "\n".join(lines) + "\n"


# --- projection (one-way DB -> markdown) --------------------------------------


def project_all(db: Database, storage: Optional[Storage] = None) -> dict[str, Any]:
    """Project all projected tables + flow-status.md to markdown.

    One-way and non-blocking: a render/write error for one entity is recorded
    in ``errors`` and does not abort the rest of the projection.
    """
    storage = storage or Storage()
    written = 0
    errors: list[str] = []

    for table in _PROJECTED:
        rows = db.list_tasks(limit=1000) if table == "tasks" else db.list_reports()
        renderer = _RENDERERS[table]
        for row in rows:
            try:
                storage.write_file(table, int(row["id"]), renderer(row))
                written += 1
            except Exception as exc:  # non-blocking by contract
                errors.append(f"{table}/{row.get('id')}: {exc}")

    try:
        status_path = storage.root / "flow-status.md"
        status_path.parent.mkdir(parents=True, exist_ok=True)
        status_path.write_text(render_status(db), encoding="utf-8")
    except Exception as exc:  # pragma: no cover - defensive
        errors.append(f"flow-status.md: {exc}")

    return {"written": written, "errors": errors, "root": str(storage.root)}
