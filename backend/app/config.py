"""Paths and settings. Each value can be overridden with an environment variable."""
from __future__ import annotations

import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = BACKEND_DIR.parent
SCHEMA_PATH = BACKEND_DIR / "schema.sql"

_DEFAULT_DATASET = REPO_DIR / "data-sets" / "historical_resources_expanded_verified_2026-11-06.json"


def db_path() -> Path:
    """SQLite file the API reads. It is a build artifact: rebuilt from the dataset."""
    return Path(os.environ.get("HUBHACKS_DB", BACKEND_DIR / "data" / "hubhacks.db"))


def dataset_path() -> Path:
    """The research team's verified JSON (the master copy of the hand-checked records)."""
    return Path(os.environ.get("HUBHACKS_DATASET", _DEFAULT_DATASET))


def rebuild_on_start() -> bool:
    """Rebuild the database from the dataset every time the API starts (default on)."""
    return os.environ.get("HUBHACKS_REBUILD_ON_START", "1") != "0"
