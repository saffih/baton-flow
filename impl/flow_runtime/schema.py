"""SQLite schema definition (HLD-026).

Single source of truth: 7 core tables. Schema is idempotent — safe to run
on every connection via initialize_schema().
"""

from __future__ import annotations

# Tables the Database API is permitted to operate on. Used for table-name
# whitelisting to prevent injection via dynamic table references.
ALLOWED_TABLES = frozenset(
    {
        "hints",
        "tasks",
        "reports",
        "sessions",
        "config",
        "task_notes",
        "report_links",
    }
)

SCHEMA_STATEMENTS: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS hints (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        unique_id TEXT UNIQUE,
        content TEXT NOT NULL,
        status TEXT DEFAULT 'enabled',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        priority TEXT DEFAULT 'normal',
        recipe TEXT,
        archived BOOLEAN DEFAULT 0,
        archived_at TIMESTAMP,
        metadata JSON DEFAULT '{}',
        is_test BOOLEAN DEFAULT 0
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        unique_id TEXT UNIQUE,
        content TEXT NOT NULL,
        status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'in-progress', 'done', 'ack', 'archived')),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        done_at TIMESTAMP,
        outcome TEXT,
        assignee TEXT,
        ref TEXT,
        requires_capability TEXT,
        priority TEXT DEFAULT 'normal',
        due_date TIMESTAMP,
        archived INTEGER DEFAULT 0 CHECK(archived IN (0, 1)),
        archived_at TIMESTAMP,
        taken_by TEXT,
        taken_at TIMESTAMP,
        metadata JSON DEFAULT '{}',
        task_type TEXT DEFAULT 'normal',
        parent_task_id INTEGER,
        is_test BOOLEAN DEFAULT 0,
        title TEXT,
        effort TEXT DEFAULT 'M',
        severity TEXT,
        qid TEXT,
        progress INTEGER DEFAULT 0,
        metadata_json TEXT DEFAULT '{}',
        schema_version INTEGER DEFAULT 1
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        unique_id TEXT UNIQUE,
        title TEXT NOT NULL,
        status TEXT DEFAULT 'new',
        report_type TEXT DEFAULT 'wip',
        content TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        discussed_at TIMESTAMP,
        cycle_ref TEXT,
        lifecycle_state TEXT DEFAULT 'new' CHECK(lifecycle_state IN ('new', 'read', 'in_progress', 'discussed', 'done', 'archived')),
        lifecycle_state_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        archived BOOLEAN DEFAULT 0,
        archived_at TIMESTAMP,
        file_path TEXT,
        task_id INTEGER,
        is_wip BOOLEAN DEFAULT 0,
        created_by TEXT DEFAULT 'agent',
        metadata JSON DEFAULT '{}'
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS sessions (
        session_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        created_at TIMESTAMP NOT NULL,
        last_activity TIMESTAMP NOT NULL,
        status TEXT NOT NULL DEFAULT 'active',
        pid INTEGER,
        capabilities TEXT,
        failover_target TEXT,
        context_directory TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS config (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        metadata JSON DEFAULT '{}'
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS task_notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id INTEGER NOT NULL,
        content TEXT NOT NULL,
        author TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS report_links (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_report_id INTEGER NOT NULL,
        target_report_id INTEGER NOT NULL,
        link_type TEXT NOT NULL DEFAULT 'reference',
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (source_report_id) REFERENCES reports(id) ON DELETE CASCADE,
        FOREIGN KEY (target_report_id) REFERENCES reports(id) ON DELETE CASCADE,
        CHECK(source_report_id != target_report_id)
    )
    """,
)

INDEX_STATEMENTS: tuple[str, ...] = (
    "CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)",
    "CREATE INDEX IF NOT EXISTS idx_tasks_assignee ON tasks(assignee)",
    "CREATE INDEX IF NOT EXISTS idx_tasks_archived ON tasks(archived)",
    "CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority)",
    "CREATE INDEX IF NOT EXISTS idx_hints_status ON hints(status)",
    "CREATE INDEX IF NOT EXISTS idx_reports_type ON reports(report_type)",
    "CREATE INDEX IF NOT EXISTS idx_reports_task ON reports(task_id)",
    "CREATE INDEX IF NOT EXISTS idx_task_notes_task ON task_notes(task_id)",
    "CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status)",
)
