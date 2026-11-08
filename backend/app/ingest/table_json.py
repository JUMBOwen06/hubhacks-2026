"""Adapter: a dataset already in the table shape -> common schema.

Source file: data/seed/black_history_dataset_v2_2026-11-06.json (Owen, 41 records).

The file has one list per table (institution, record, record_date, entity,
record_entity, record_relation) with the same column names as schema.sql, so rows
are inserted as they are. Nothing is derived or guessed here: curator judgements
(holders, content notes, roles) are already in the file. Columns the file has that
the schema lacks are reported as warnings; columns the schema has that the file
lacks stay empty (unknown).
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

TABLE_ORDER = ["institution", "record", "record_date", "entity", "record_entity", "record_relation"]


def is_table_shaped(data: dict) -> bool:
    return isinstance(data, dict) and isinstance(data.get("record"), list) and "institution" in data


def _columns(conn: sqlite3.Connection, table: str) -> list[str]:
    return [r[1] for r in conn.execute(f"PRAGMA table_info({table})")]


def load(conn: sqlite3.Connection, path: Path) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    summary = {"source": Path(path).name, "format": "tables", "warnings": []}
    for table in TABLE_ORDER:
        rows = data.get(table) or []
        known = set(_columns(conn, table))
        extra = sorted({k for row in rows for k in row} - known)
        if extra:
            summary["warnings"].append(f"{table}: columns not in schema, ignored: {', '.join(extra)}")
        for row in rows:
            cols = [c for c in row if c in known]
            conn.execute(
                f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join('?' for _ in cols)})",
                [row[c] for c in cols],
            )
        summary[f"{table}_rows"] = len(rows)
    summary["record_rows"] = summary.pop("record_rows")
    expected = (data.get("meta") or {}).get("counts") or {}
    for table, n in expected.items():
        got = summary.get(f"{table}_rows")
        if got is not None and got != n:
            summary["warnings"].append(f"{table}: file meta says {n} rows, loaded {got}")
    return summary
