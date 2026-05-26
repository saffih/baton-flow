"""Flow Core Database API (HLD-010, HLD-019).

The exclusive access layer to the SQLite single source of truth. All reads
and writes go through this class. Enforces:
- WAL mode for concurrent access
- Parameterized queries (no string-built SQL with user values)
- Table-name whitelisting (ALLOWED_TABLES)
- Retry with exponential backoff on lock contention
"""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any, Optional

from flow_runtime.schema import ALLOWED_TABLES, INDEX_STATEMENTS, SCHEMA_STATEMENTS

DEFAULT_DB_PATH = ".flow/database.db"

# Columns that are writable on tasks via add_task/update_task kwargs.
_TASK_COLUMNS = frozenset(
    {
        "content", "status", "outcome", "assignee", "ref", "requires_capability",
        "priority", "due_date", "archived", "archived_at", "taken_by", "taken_at",
        "metadata", "task_type", "parent_task_id", "is_test", "title", "effort",
        "severity", "qid", "progress", "metadata_json", "done_at", "unique_id",
    }
)
_HINT_COLUMNS = frozenset(
    {"content", "status", "priority", "recipe", "archived", "archived_at", "metadata", "is_test", "unique_id"}
)
_REPORT_COLUMNS = frozenset(
    {
        "title", "status", "report_type", "content", "discussed_at", "cycle_ref",
        "lifecycle_state", "archived", "archived_at", "file_path", "task_id",
        "is_wip", "created_by", "metadata", "unique_id",
    }
)


class DatabaseError(Exception):
    """Raised for Database API contract violations (bad column, bad table)."""


class Database:
    """Exclusive SQLite access layer."""

    def __init__(
        self,
        db_path: str = DEFAULT_DB_PATH,
        *,
        auto_init: bool = True,
    ) -> None:
        self.db_path = str(db_path)
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        # A single shared connection for :memory: so schema persists across calls.
        self._memory_conn: Optional[sqlite3.Connection] = None
        if self.db_path == ":memory:":
            self._memory_conn = self._new_connection()
        if auto_init:
            self.initialize_schema()

    # --- connection management -------------------------------------------------

    def _new_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        if self.db_path != ":memory:":
            conn.execute("PRAGMA journal_mode = WAL")
        return conn

    def get_connection(self, max_retries: int = 3) -> sqlite3.Connection:
        """Return a connection, retrying with exponential backoff on lock."""
        if self._memory_conn is not None:
            return self._memory_conn
        delay = 0.1
        last_exc: Optional[Exception] = None
        for _ in range(max_retries):
            try:
                return self._new_connection()
            except sqlite3.OperationalError as exc:  # pragma: no cover - rare
                last_exc = exc
                time.sleep(delay)
                delay *= 2
        raise DatabaseError(f"could not acquire connection: {last_exc}")

    def _close(self, conn: sqlite3.Connection) -> None:
        if conn is not self._memory_conn:
            conn.close()

    def _write(self, sql: str, params: tuple[Any, ...] = ()) -> int:
        """Execute a write inside a transaction; return lastrowid."""
        conn = self.get_connection()
        try:
            cur = conn.execute(sql, params)
            conn.commit()
            return int(cur.lastrowid)
        finally:
            self._close(conn)

    def _query_all(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        conn = self.get_connection()
        try:
            rows = conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows]
        finally:
            self._close(conn)

    def _query_one(self, sql: str, params: tuple[Any, ...] = ()) -> Optional[dict[str, Any]]:
        conn = self.get_connection()
        try:
            row = conn.execute(sql, params).fetchone()
            return dict(row) if row else None
        finally:
            self._close(conn)

    # --- schema ----------------------------------------------------------------

    def initialize_schema(self) -> None:
        conn = self.get_connection()
        try:
            for stmt in SCHEMA_STATEMENTS:
                conn.execute(stmt)
            for stmt in INDEX_STATEMENTS:
                conn.execute(stmt)
            conn.commit()
        finally:
            self._close(conn)

    # --- tasks -----------------------------------------------------------------

    def add_task(self, content: str, **kwargs: Any) -> int:
        cols = self._validate_columns(kwargs, _TASK_COLUMNS, "tasks")
        cols["content"] = content
        cols.setdefault("unique_id", uuid.uuid4().hex)
        cols = self._encode_json_fields(cols)
        names = ", ".join(cols)
        placeholders = ", ".join("?" for _ in cols)
        return self._write(
            f"INSERT INTO tasks ({names}) VALUES ({placeholders})",
            tuple(cols.values()),
        )

    def update_task(self, task_id: int, **kwargs: Any) -> None:
        cols = self._validate_columns(kwargs, _TASK_COLUMNS, "tasks")
        if not cols:
            return
        cols = self._encode_json_fields(cols)
        assignments = ", ".join(f"{c} = ?" for c in cols)
        self._write(
            f"UPDATE tasks SET {assignments}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (*cols.values(), task_id),
        )

    def mark_task_done(
        self,
        task_id: int,
        outcome: str,
        outcome_length_threshold: Optional[int] = None,
    ) -> None:
        if outcome_length_threshold is not None and len(outcome) < outcome_length_threshold:
            raise DatabaseError(
                f"outcome shorter than required threshold {outcome_length_threshold}"
            )
        self._write(
            "UPDATE tasks SET status = 'done', outcome = ?, done_at = CURRENT_TIMESTAMP, "
            "updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (outcome, task_id),
        )

    def mark_task_acknowledged(self, task_id: int, reason: str = "") -> None:
        self._write(
            "UPDATE tasks SET status = 'ack', outcome = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (reason, task_id),
        )

    def get_task(self, task_id: int) -> Optional[dict[str, Any]]:
        return self._query_one("SELECT * FROM tasks WHERE id = ?", (task_id,))

    def list_tasks(
        self,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        archived: bool = False,
        limit: Optional[int] = None,
        sort_by: str = "created",
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        clauses = ["archived = ?"]
        params: list[Any] = [1 if archived else 0]
        if status is not None:
            clauses.append("status = ?")
            params.append(status)
        if priority is not None:
            clauses.append("priority = ?")
            params.append(priority)
        if kwargs.get("assignee") is not None:
            clauses.append("assignee = ?")
            params.append(kwargs["assignee"])
        order = {"created": "created_at", "updated": "updated_at", "priority": "priority"}.get(
            sort_by, "created_at"
        )
        sql = f"SELECT * FROM tasks WHERE {' AND '.join(clauses)} ORDER BY {order} DESC"
        if limit is not None:
            sql += " LIMIT ?"
            params.append(int(limit))
        return self._query_all(sql, tuple(params))

    # --- task reservation ------------------------------------------------------

    def reserve_task(self, task_id: int, session_name: str) -> bool:
        """Atomically reserve an unreserved task. Returns False if already taken."""
        conn = self.get_connection()
        try:
            cur = conn.execute(
                "UPDATE tasks SET taken_by = ?, taken_at = CURRENT_TIMESTAMP "
                "WHERE id = ? AND (taken_by IS NULL OR taken_by = '')",
                (session_name, task_id),
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            self._close(conn)

    def release_task(self, task_id: int, session_name: str) -> bool:
        conn = self.get_connection()
        try:
            cur = conn.execute(
                "UPDATE tasks SET taken_by = NULL, taken_at = NULL WHERE id = ? AND taken_by = ?",
                (task_id, session_name),
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            self._close(conn)

    def is_task_taken(self, task_id: int) -> bool:
        row = self._query_one("SELECT taken_by FROM tasks WHERE id = ?", (task_id,))
        return bool(row and row.get("taken_by"))

    # --- hints -----------------------------------------------------------------

    def add_hint(self, content: str, **kwargs: Any) -> int:
        cols = self._validate_columns(kwargs, _HINT_COLUMNS, "hints")
        cols["content"] = content
        cols.setdefault("unique_id", uuid.uuid4().hex)
        cols = self._encode_json_fields(cols)
        names = ", ".join(cols)
        placeholders = ", ".join("?" for _ in cols)
        return self._write(
            f"INSERT INTO hints ({names}) VALUES ({placeholders})", tuple(cols.values())
        )

    def update_hint(self, hint_id: int, **kwargs: Any) -> None:
        cols = self._validate_columns(kwargs, _HINT_COLUMNS, "hints")
        if not cols:
            return
        cols = self._encode_json_fields(cols)
        assignments = ", ".join(f"{c} = ?" for c in cols)
        self._write(
            f"UPDATE hints SET {assignments}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (*cols.values(), hint_id),
        )

    def get_hint(self, hint_id: int) -> Optional[dict[str, Any]]:
        return self._query_one("SELECT * FROM hints WHERE id = ?", (hint_id,))

    def list_hints(
        self,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        archived: Optional[bool] = None,
        sort_by: str = "created",
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if status is not None:
            clauses.append("status = ?")
            params.append(status)
        if priority is not None:
            clauses.append("priority = ?")
            params.append(priority)
        if archived is not None:
            clauses.append("archived = ?")
            params.append(1 if archived else 0)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        order = {"created": "created_at", "updated": "updated_at"}.get(sort_by, "created_at")
        return self._query_all(f"SELECT * FROM hints {where} ORDER BY {order} DESC", tuple(params))

    # --- reports ---------------------------------------------------------------

    def add_report(self, report: dict[str, Any]) -> int:
        cols = self._validate_columns(report, _REPORT_COLUMNS, "reports")
        if "title" not in cols:
            raise DatabaseError("report requires a 'title'")
        cols.setdefault("unique_id", uuid.uuid4().hex)
        cols = self._encode_json_fields(cols)
        names = ", ".join(cols)
        placeholders = ", ".join("?" for _ in cols)
        return self._write(
            f"INSERT INTO reports ({names}) VALUES ({placeholders})", tuple(cols.values())
        )

    def update_report(self, report_id: int, **kwargs: Any) -> None:
        cols = self._validate_columns(kwargs, _REPORT_COLUMNS, "reports")
        if not cols:
            return
        cols = self._encode_json_fields(cols)
        assignments = ", ".join(f"{c} = ?" for c in cols)
        self._write(
            f"UPDATE reports SET {assignments}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (*cols.values(), report_id),
        )

    def get_report(self, report_id: int) -> Optional[dict[str, Any]]:
        return self._query_one("SELECT * FROM reports WHERE id = ?", (report_id,))

    def list_reports(
        self,
        status: Optional[str] = None,
        archived: Optional[bool] = None,
        report_type: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if status is not None:
            clauses.append("status = ?")
            params.append(status)
        if archived is not None:
            clauses.append("archived = ?")
            params.append(1 if archived else 0)
        if report_type is not None:
            clauses.append("report_type = ?")
            params.append(report_type)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        return self._query_all(
            f"SELECT * FROM reports {where} ORDER BY created_at DESC", tuple(params)
        )

    def append_to_report(self, report_id: int, content: str) -> bool:
        conn = self.get_connection()
        try:
            cur = conn.execute(
                "UPDATE reports SET content = COALESCE(content, '') || ?, "
                "updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (content, report_id),
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            self._close(conn)

    def get_wip_report_by_task_id(self, task_id: int) -> Optional[dict[str, Any]]:
        return self._query_one(
            "SELECT * FROM reports WHERE task_id = ? AND is_wip = 1 ORDER BY updated_at DESC LIMIT 1",
            (task_id,),
        )

    # --- UI-optimized queries --------------------------------------------------

    def get_tasks_for_ui(
        self,
        status: Optional[str] = None,
        assignee: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        clauses = ["archived = 0"]
        params: list[Any] = []
        if status is not None:
            clauses.append("status = ?")
            params.append(status)
        if assignee is not None:
            clauses.append("assignee = ?")
            params.append(assignee)
        params.append(int(limit))
        return self._query_all(
            f"SELECT id, title, content, status, priority, assignee, created_at, updated_at "
            f"FROM tasks WHERE {' AND '.join(clauses)} ORDER BY updated_at DESC LIMIT ?",
            tuple(params),
        )

    def get_task_count_for_ui(
        self, status: Optional[str] = None, assignee: Optional[str] = None
    ) -> int:
        clauses = ["archived = 0"]
        params: list[Any] = []
        if status is not None:
            clauses.append("status = ?")
            params.append(status)
        if assignee is not None:
            clauses.append("assignee = ?")
            params.append(assignee)
        row = self._query_one(
            f"SELECT COUNT(*) AS n FROM tasks WHERE {' AND '.join(clauses)}", tuple(params)
        )
        return int(row["n"]) if row else 0

    # --- config ----------------------------------------------------------------

    def set_config(self, key: str, value: str) -> None:
        self._write(
            "INSERT INTO config (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP",
            (key, value),
        )

    def get_config(self, key: str) -> Optional[str]:
        row = self._query_one("SELECT value FROM config WHERE key = ?", (key,))
        return row["value"] if row else None

    # --- sessions --------------------------------------------------------------

    def register_session(
        self,
        session_id: str,
        name: str,
        *,
        pid: Optional[int] = None,
        capabilities: Optional[str] = None,
        context_directory: Optional[str] = None,
    ) -> None:
        self._write(
            "INSERT INTO sessions (session_id, name, created_at, last_activity, status, pid, capabilities, context_directory) "
            "VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 'active', ?, ?, ?) "
            "ON CONFLICT(session_id) DO UPDATE SET last_activity = CURRENT_TIMESTAMP, status = 'active'",
            (session_id, name, pid, capabilities, context_directory),
        )

    def touch_session(self, session_id: str) -> None:
        self._write(
            "UPDATE sessions SET last_activity = CURRENT_TIMESTAMP WHERE session_id = ?",
            (session_id,),
        )

    def list_sessions(self, status: Optional[str] = "active") -> list[dict[str, Any]]:
        if status is None:
            return self._query_all("SELECT * FROM sessions ORDER BY last_activity DESC")
        return self._query_all(
            "SELECT * FROM sessions WHERE status = ? ORDER BY last_activity DESC", (status,)
        )

    def get_session(self, name: str) -> Optional[dict[str, Any]]:
        return self._query_one(
            "SELECT * FROM sessions WHERE name = ? ORDER BY last_activity DESC LIMIT 1", (name,)
        )

    # --- health ----------------------------------------------------------------

    def health_check(self) -> dict[str, Any]:
        try:
            conn = self.get_connection()
            try:
                conn.execute("SELECT 1").fetchone()
                tables = [
                    r["name"]
                    for r in conn.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    ).fetchall()
                ]
            finally:
                self._close(conn)
            present = sorted(set(tables) & ALLOWED_TABLES)
            missing = sorted(ALLOWED_TABLES - set(tables))
            return {
                "status": "healthy" if not missing else "degraded",
                "db_path": self.db_path,
                "tables_present": present,
                "tables_missing": missing,
            }
        except Exception as exc:  # pragma: no cover - defensive
            return {"status": "unhealthy", "error": str(exc), "db_path": self.db_path}

    # --- helpers ---------------------------------------------------------------

    @staticmethod
    def _validate_columns(
        kwargs: dict[str, Any], allowed: frozenset[str], table: str
    ) -> dict[str, Any]:
        if table not in ALLOWED_TABLES:
            raise DatabaseError(f"table not allowed: {table}")
        bad = set(kwargs) - allowed
        if bad:
            raise DatabaseError(f"unknown column(s) for {table}: {', '.join(sorted(bad))}")
        return dict(kwargs)

    @staticmethod
    def _encode_json_fields(cols: dict[str, Any]) -> dict[str, Any]:
        out = dict(cols)
        for field in ("metadata",):
            if field in out and isinstance(out[field], (dict, list)):
                out[field] = json.dumps(out[field])
        return out
