"""Build the SQLite database from the source files.

Usage (from the backend folder):
    python -m app.build                 # default paths
    python -m app.build --db my.db --dataset ../data-sets/file.json

The database is a build artifact: the JSON dataset stays the master copy.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

from . import config, db
from .ingest import verified_json


def rebuild_search_index(conn: sqlite3.Connection) -> int:
    """Refill record_search from the record and entity tables."""
    conn.execute("DELETE FROM record_search")
    conn.execute(
        """
        INSERT INTO record_search (record_id, title, description, entity_names)
        SELECT r.id,
               r.title_original,
               TRIM(COALESCE(r.description, '') || ' ' || COALESCE(r.container_title, '')
                    || ' ' || COALESCE(r.source_reference, '')),
               COALESCE((SELECT GROUP_CONCAT(name, ' | ') FROM (
                    SELECT DISTINCT e.name_preferred AS name
                    FROM record_entity re JOIN entity e ON e.id = re.entity_id
                    WHERE re.record_id = r.id
                    ORDER BY e.name_preferred)), '')
        FROM record r
        """
    )
    return conn.execute("SELECT COUNT(*) FROM record_search").fetchone()[0]


def validate(conn: sqlite3.Connection) -> list[str]:
    """Checks that should never fail. Returns human-readable warnings."""
    warnings = []
    for (rid,) in conn.execute(
        "SELECT id FROM record WHERE source_url NOT LIKE 'http%'"
    ):
        warnings.append(f"{rid}: source_url is not a web link")
    for (fk,) in conn.execute("PRAGMA foreign_key_check"):
        warnings.append(f"foreign key problem in table {fk}")
    undated = conn.execute(
        "SELECT COUNT(*) FROM record r WHERE NOT EXISTS (SELECT 1 FROM record_date d "
        "WHERE d.record_id = r.id AND d.kind <> 'publication' AND d.start_year IS NOT NULL)"
    ).fetchone()[0]
    if undated:
        warnings.append(f"{undated} records have no historical date; they show as 'Undated'")
    return warnings


def build_database(
    db_file: Path | None = None,
    dataset: Path | None = None,
    schema: Path | None = None,
) -> dict:
    db_file = Path(db_file or config.db_path())
    dataset = Path(dataset or config.dataset_path())
    schema = Path(schema or config.SCHEMA_PATH)

    db_file.parent.mkdir(parents=True, exist_ok=True)
    for suffix in ("", "-wal", "-shm", "-journal"):
        p = Path(str(db_file) + suffix)
        if p.exists():
            p.unlink()

    conn = db.connect(db_file)
    try:
        engine = db.apply_schema(conn, schema)
        sources = [verified_json.load(conn, dataset)]
        indexed = rebuild_search_index(conn)
        conn.commit()
        summary = {
            "db": str(db_file),
            "search_engine": engine,
            "sources": sources,
            "records_indexed": indexed,
            "institutions": conn.execute("SELECT COUNT(*) FROM institution").fetchone()[0],
            "entities": conn.execute("SELECT COUNT(*) FROM entity").fetchone()[0],
            "warnings": validate(conn),
        }
    finally:
        conn.close()
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the discovery hub database.")
    parser.add_argument("--db", type=Path, default=None, help="SQLite file to create")
    parser.add_argument("--dataset", type=Path, default=None, help="verified JSON dataset")
    args = parser.parse_args()
    print(json.dumps(build_database(args.db, args.dataset), indent=2))


if __name__ == "__main__":
    main()
