#!/usr/bin/env python3
"""Load the Black history discovery dataset into a SQLite database.

Usage:
    python3 load_dataset.py [db_path] [json_path] [schema_path]

Defaults: black_history.db, black_history_dataset_v2_2026-11-06.json and
schema.sql, all in this script's folder. An existing db file is replaced.

Steps: create the tables from schema.sql, turn foreign keys on, insert every
table from the JSON, fill the record_search full-text index, check foreign
keys, print row counts. Standard library only.
"""
import json
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TABLE_ORDER = ["institution", "record", "record_date", "entity", "record_entity", "record_relation"]


def main():
    db_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "black_history.db")
    json_path = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
        HERE, "black_history_dataset_v2_2026-11-06.json")
    schema_path = sys.argv[3] if len(sys.argv) > 3 else os.path.join(HERE, "schema.sql")

    if os.path.exists(db_path):
        os.remove(db_path)

    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    with open(schema_path, encoding="utf-8") as f:
        schema_sql = f.read()

    con = sqlite3.connect(db_path)
    con.executescript(schema_sql)
    con.execute("PRAGMA foreign_keys = ON")
    if con.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
        sys.exit("Could not turn on foreign keys.")

    # 1. Insert tables in dependency order. A failing CHECK or FK stops the load.
    with con:
        for table in TABLE_ORDER:
            rows = data[table]
            if not rows:
                continue
            cols = list(rows[0].keys())
            sql = "INSERT INTO %s (%s) VALUES (%s)" % (
                table, ", ".join(cols), ", ".join("?" for _ in cols))
            for row in rows:
                try:
                    con.execute(sql, [row[c] for c in cols])
                except sqlite3.DatabaseError as e:
                    key = row.get("id") or (row.get("record_id"), row.get("entity_id"))
                    sys.exit("Failed to insert %s %s: %s" % (table, key, e))

    # 2. Fill the full-text index: title, description, and all linked entity names.
    with con:
        con.execute("DELETE FROM record_search")
        con.execute("""
            INSERT INTO record_search (record_id, title, description, entity_names)
            SELECT r.id,
                   r.title_original,
                   COALESCE(r.description, ''),
                   COALESCE((SELECT group_concat(name, ' | ')
                             FROM (SELECT DISTINCT e.name_preferred AS name
                                   FROM record_entity re
                                   JOIN entity e ON e.id = re.entity_id
                                   WHERE re.record_id = r.id
                                   UNION
                                   SELECT DISTINCT re.name_as_written
                                   FROM record_entity re
                                   WHERE re.record_id = r.id
                                     AND re.name_as_written IS NOT NULL)), '')
            FROM record r
        """)

    # 3. Checks.
    problems = con.execute("PRAGMA foreign_key_check").fetchall()
    if problems:
        sys.exit("Foreign key problems: %r" % problems)
    if con.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
        sys.exit("Integrity check failed.")

    # 4. Counts.
    print("Loaded %s" % db_path)
    for table in TABLE_ORDER + ["record_search"]:
        n = con.execute("SELECT COUNT(*) FROM %s" % table).fetchone()[0]
        expected = data["meta"]["counts"].get(table)
        note = "" if expected is None or expected == n else "  (JSON meta says %s!)" % expected
        print("  %-16s %4d%s" % (table, n, note))
    con.close()


if __name__ == "__main__":
    main()
