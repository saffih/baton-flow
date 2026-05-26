"""Environment staging + config resolution (HLD-023, HLD-034).

FLOW_ENV selects an isolated database + port so prod/test/dev never collide.
The DB path can be overridden directly with FLOW_DB_PATH (used by tests).
"""

from __future__ import annotations

import os
from dataclasses import dataclass

PROD = "production"
TEST = "test"
DEV = "development"

_ALIASES = {
    "prod": PROD, "production": PROD,
    "test": TEST, "testing": TEST,
    "dev": DEV, "development": DEV,
}


@dataclass(frozen=True)
class EnvConfig:
    name: str
    db_path: str
    port: int


_ENVIRONMENTS = {
    PROD: EnvConfig(PROD, ".flow/database.db", 8321),
    TEST: EnvConfig(TEST, ".flow/test-database.db", 8323),
    DEV: EnvConfig(DEV, ".flow/dev-database.db", 8322),
}


def resolve_env(env: str | None = None) -> EnvConfig:
    """Resolve an environment name (or FLOW_ENV) to its config.

    Precedence: explicit arg > FLOW_ENV env var > production default.
    FLOW_DB_PATH overrides the resolved db_path when set.
    """
    raw = (env or os.environ.get("FLOW_ENV") or PROD).strip().lower()
    canonical = _ALIASES.get(raw, PROD)
    cfg = _ENVIRONMENTS[canonical]
    override = os.environ.get("FLOW_DB_PATH")
    if override:
        cfg = EnvConfig(cfg.name, override, cfg.port)
    return cfg
