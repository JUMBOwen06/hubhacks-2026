"""Anonymous usage counts for the Impact page.

Privacy by design: no cookies, no IP addresses, no user agents, no location and no
visitor IDs are stored. Each row is one event with the day it happened (no time of day).
A "visit" is counted once per browser tab session by the page itself, which keeps a flag
in sessionStorage and never sends an identifier.

The counts live in their own SQLite file, separate from the search database, because the
search database is rebuilt from the dataset on every start.
"""
from __future__ import annotations

import datetime as dt
import re
import sqlite3
from pathlib import Path

KINDS = {"visit", "page_view", "search", "source_click"}
PAGES = {"index", "results", "record", "institutions", "about"}
_RECORD_ID = re.compile(r"^[A-Za-z0-9_.:-]{1,40}$")
MAX_QUERY_LEN = 80

_SCHEMA = """
CREATE TABLE IF NOT EXISTS event (
    id           INTEGER PRIMARY KEY,
    day          TEXT NOT NULL,      -- YYYY-MM-DD, no time of day
    kind         TEXT NOT NULL,      -- visit | page_view | search | source_click
    page         TEXT,               -- page name for page_view
    query        TEXT,               -- normalized search words, for search
    result_count INTEGER,            -- for search
    record_id    TEXT                -- record page viewed, or record whose source was opened
);
CREATE INDEX IF NOT EXISTS event_kind_day ON event(kind, day);
"""


def connect(path: Path | str) -> sqlite3.Connection:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    return conn


def normalize_query(q: str | None) -> str | None:
    if not q:
        return None
    q = " ".join(str(q).lower().split())[:MAX_QUERY_LEN]
    return q or None


def record_event(conn: sqlite3.Connection, payload: dict, today: dt.date | None = None) -> bool:
    """Store one event. Returns False (and stores nothing) for anything malformed."""
    kind = payload.get("kind")
    if kind not in KINDS:
        return False
    page = payload.get("page")
    page = page if page in PAGES else None
    record_id = payload.get("record_id")
    record_id = record_id if isinstance(record_id, str) and _RECORD_ID.match(record_id) else None
    query = normalize_query(payload.get("query")) if kind == "search" else None
    if kind == "search" and not query:
        return False
    if kind == "source_click" and not record_id:
        return False
    results = payload.get("results")
    results = results if isinstance(results, int) and 0 <= results < 100000 else None
    day = (today or dt.date.today()).isoformat()
    conn.execute(
        "INSERT INTO event (day, kind, page, query, result_count, record_id) VALUES (?,?,?,?,?,?)",
        (day, kind, page if kind == "page_view" else None, query,
         results if kind == "search" else None, record_id),
    )
    conn.commit()
    return True


def summary(conn: sqlite3.Connection, main: sqlite3.Connection, days: int = 14,
            today: dt.date | None = None, top: int = 10) -> dict:
    """Totals, a daily series and the lists the Impact page shows."""
    today = today or dt.date.today()
    since = (today - dt.timedelta(days=days - 1)).isoformat()

    def count(kind, extra=""):
        return conn.execute(f"SELECT COUNT(*) FROM event WHERE kind = ? {extra}", (kind,)).fetchone()[0]

    totals = {
        "visits": count("visit"),
        "page_views": count("page_view"),
        "searches": count("search"),
        "searches_no_results": count("search", "AND result_count = 0"),
        "source_clicks": count("source_click"),
        "institutions_reached": 0,
    }

    series = {}
    for i in range(days):
        d = (today - dt.timedelta(days=days - 1 - i)).isoformat()
        series[d] = {"day": d, "visits": 0, "searches": 0, "source_clicks": 0}
    for r in conn.execute(
        "SELECT day, kind, COUNT(*) n FROM event WHERE day >= ? AND kind IN ('visit','search','source_click') "
        "GROUP BY day, kind", (since,)
    ):
        if r["day"] in series:
            key = {"visit": "visits", "search": "searches", "source_click": "source_clicks"}[r["kind"]]
            series[r["day"]][key] = r["n"]

    top_searches = [dict(r) for r in conn.execute(
        "SELECT query, COUNT(*) AS count, MAX(result_count) AS results FROM event "
        "WHERE kind = 'search' GROUP BY query ORDER BY count DESC, query LIMIT ?", (top,))]
    no_results = [dict(r) for r in conn.execute(
        "SELECT query, COUNT(*) AS count, MAX(day) AS last_day FROM event "
        "WHERE kind = 'search' AND result_count = 0 GROUP BY query ORDER BY count DESC, last_day DESC LIMIT ?", (top,))]

    # Where people were sent: resolve each clicked record to the institution that supplies it.
    clicks = conn.execute(
        "SELECT record_id, COUNT(*) n FROM event WHERE kind = 'source_click' GROUP BY record_id").fetchall()
    by_inst: dict[str, dict] = {}
    for r in clicks:
        row = main.execute(
            "SELECT i.id, i.name FROM record r JOIN institution i ON i.id = r.record_source_id WHERE r.id = ?",
            (r["record_id"],)).fetchone()
        if not row:
            continue
        item = by_inst.setdefault(row["id"], {"id": row["id"], "name": row["name"], "count": 0})
        item["count"] += r["n"]
    sent_to = sorted(by_inst.values(), key=lambda x: (-x["count"], x["name"]))
    totals["institutions_reached"] = len(sent_to)

    viewed = []
    for r in conn.execute(
        "SELECT record_id, COUNT(*) n FROM event WHERE kind = 'page_view' AND page = 'record' "
        "AND record_id IS NOT NULL GROUP BY record_id ORDER BY n DESC, record_id LIMIT ?", (top,)):
        row = main.execute("SELECT title_original FROM record WHERE id = ?", (r["record_id"],)).fetchone()
        if row:
            viewed.append({"id": r["record_id"], "title": row[0], "count": r["n"]})

    first = conn.execute("SELECT MIN(day) FROM event").fetchone()[0]
    return {
        "since": first,
        "days": days,
        "totals": totals,
        "daily": list(series.values()),
        "top_searches": top_searches,
        "searches_no_results": no_results,
        "sent_to_institutions": sent_to[:top],
        "most_viewed_records": viewed,
        "privacy": "Anonymous counts only. No cookies, IP addresses, user agents, location or visitor IDs are stored.",
    }
