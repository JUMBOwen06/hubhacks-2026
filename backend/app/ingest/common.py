"""Helpers shared by all source adapters."""
from __future__ import annotations

import datetime as _dt
import re
import sqlite3
import unicodedata

ARCHIVAL_TYPES = {"archival_document", "correspondence", "register", "map", "photograph"}


def slugify(text: str) -> str:
    t = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    t = re.sub(r"[^A-Za-z0-9]+", "-", t).strip("-").lower()
    return t or "x"


def today_iso() -> str:
    return _dt.date.today().isoformat()


def years_from_label(label: str) -> tuple[int, int] | None:
    """Derive a year range from a date label when the source gave no numbers.

    "mid-1960s" -> (1960, 1969); "1957-1964" -> (1957, 1964); "1783" -> (1783, 1783).
    Callers must mark the result approximate and origin='platform_generated'.
    """
    text = label or ""
    m = re.search(r"\b(\d{3})0s\b", text)
    if m:
        start = int(m.group(1)) * 10
        return start, start + 9
    m = re.search(r"\b(\d{4})\s*[–—-]\s*(\d{4})\b", text)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.search(r"\b(\d{4})\b", text)
    if m:
        return int(m.group(1)), int(m.group(1))
    return None


def ensure_entity(conn: sqlite3.Connection, entity_type: str, name: str, record_id: str) -> str:
    """Return the entity id for a name, creating the entity if needed.

    Never merge on a partial name: a single-word person name ("Hannah") gets an
    id scoped to the record it came from, so two different Hannahs stay apart.
    Exact full-name matches of the same type are treated as one entity.
    """
    name = " ".join(name.split())
    disambiguator = None
    if entity_type == "person" and " " not in name:
        eid = f"person:{slugify(name)}--{slugify(record_id)}"
        disambiguator = f"Named in record {record_id}; identity not linked to other records"
    else:
        eid = f"{entity_type}:{slugify(name)}"
    conn.execute(
        "INSERT OR IGNORE INTO entity (id, entity_type, name_preferred, disambiguator) "
        "VALUES (?, ?, ?, ?)",
        (eid, entity_type, name, disambiguator),
    )
    return eid


def link_entity(
    conn: sqlite3.Connection,
    record_id: str,
    entity_id: str,
    role: str,
    name_as_written: str,
    origin: str,
    link_basis: str,
) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO record_entity "
        "(record_id, entity_id, role, name_as_written, origin, link_basis) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (record_id, entity_id, role, name_as_written, origin, link_basis),
    )
