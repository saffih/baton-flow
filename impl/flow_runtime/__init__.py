"""Flow runtime — SQLite-backed task system with TEA architecture.

Single source of truth is the SQLite database, accessed exclusively through
the Database API (flow_runtime.database.Database). All AI-to-system
communication goes through the CLI (flow_runtime.cli).
"""

__version__ = "2.10.1"
