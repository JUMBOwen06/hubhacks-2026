"""SQLite connection helpers and schema setup."""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path

# Used only when this Python's SQLite was built without FTS5.
_FALLBACK_SEARCH_TABLE = """
CREATE TABLE IF NOT EXISTS record_search (
    record_id    TEXT PRIMARY KEY,
    title        TEXT,
    description  TEXT,
    entity_names TEXT
);
"""


def fts5_available() -> bool:
    try:
        con = sqlite3.connect(":memory:")
        con.execute("CREATE VIRTUAL TABLE t USING fts5(a)")
        con.close()
        return True
    except sqlite3.OperationalError:
        return False


def connect(path: Path | str) -> sqlite3.Connection:
    # check_same_thread=False: FastAPI may open the connection and run the
    # endpoint on different worker threads. Each request gets its own connection.
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def apply_schema(conn: sqlite3.Connection, schema_path: Path) -> str:
    """Create all tables. Returns the search engine in use: 'fts5' or 'like'."""
    sql = schema_path.read_text(encoding="utf-8")
    engine = "fts5"
    if not fts5_available():
        sql = re.sub(r"-- fts:begin.*?-- fts:end", _FALLBACK_SEARCH_TABLE, sql, flags=re.S)
        engine = "like"
    conn.executescript(sql)
    return engine


def search_engine(conn: sqlite3.Connection) -> str:
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE name = 'record_search'"
    ).fetchone()
    return "fts5" if row and "fts5" in (row[0] or "").lower() else "like"
