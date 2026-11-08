"""Adapter: the research team's hand-verified JSON -> common schema (verified tier).

Source format: the research team's v1 verified JSON (historical_resources_expanded_verified_2026-11-06.json,
now the test fixture backend/tests/fixtures/verified_v1_27_records.json).

Rules (from the team's data principles):
- One `record` row per access point: each institution's description is its own row.
  When one resource has several access points (e.g. Book of Negroes at Nova Scotia
  Archives and LAC), the rows are linked with a curated `describes_same_resource`
  relation instead of being merged.
- Empty means unknown. Values derived here by rule are listed in `change_notes` or
  marked origin='platform_generated'.
- Curator judgements made in this file (holder overrides, content notes, role
  overrides) are listed in the dicts below so the team can review them in one place.
"""
from __future__ import annotations

import itertools
import json
import sqlite3
from pathlib import Path

from .common import (
    ARCHIVAL_TYPES,
    ensure_entity,
    link_entity,
    slugify,
    today_iso,
    years_from_label,
)

ADDED_BY = "research-team"

# Institution registry. Keys are the names used in the dataset.
INSTITUTIONS: dict[str, dict] = {
    "Nova Scotia Archives": dict(
        id="inst_nsa", type="archive",
        website_url="https://archives.novascotia.ca",
        location="Halifax, Nova Scotia",
        rights_policy_url="https://archives.novascotia.ca/copying-use-protocols/",
    ),
    "Library and Archives Canada": dict(
        id="inst_lac", type="archive",
        website_url="https://library-archives.canada.ca",
        catalogue_url="https://recherche-collection-search.bac-lac.gc.ca/eng",
        location="Ottawa, Ontario",
        rights_policy_url="https://www.canada.ca/en/library-archives/terms-conditions.html",
    ),
    "Parks Canada": dict(
        id="inst_parks", type="government",
        website_url="https://parks.canada.ca",
        rights_policy_url="https://parks.canada.ca/termes-terms",
    ),
    "Acadiensis (University of New Brunswick Libraries)": dict(
        id="inst_acadiensis", type="publisher",
        website_url="https://journals.lib.unb.ca/index.php/Acadiensis",
        location="Fredericton, New Brunswick",
    ),
    "Ontario History (Ontario Historical Society / Érudit)": dict(
        id="inst_ontario_history", type="publisher",
        website_url="https://www.erudit.org/en/journals/onhistory/",
    ),
    "Fernwood Publishing (Roseway imprint)": dict(
        id="inst_fernwood", type="publisher",
        website_url="https://fernwoodpublishing.ca",
    ),
    "The National Archives (United Kingdom)": dict(
        id="inst_tna_uk", type="archive",
        website_url="https://www.nationalarchives.gov.uk",
        location="Kew, London, United Kingdom",
    ),
}

RESOURCE_TYPES = {
    "historical register": "register",
    "archival document": "archival_document",
    "historical map": "map",
    "historical correspondence": "correspondence",
    "historic person profile": "person_profile",
    "research guide": "research_guide",
    "journal forum": "journal_article",
    "journal article": "journal_article",
    "book": "book",
}

# Curator judgement: who holds the original, where the dataset notes say so.
HOLDER_OVERRIDES = {
    "SRC-001": (
        "inst_tna_uk", "unconfirmed",
        "Research team notes: the British original is held by The National Archives (UK); "
        "the American version is a separate original. Not independently confirmed.",
    ),
}

# Curator judgement: cautions shown with the record. DRAFT for BCCNS review.
CONTENT_NOTES = {
    "SRC-001": "The title is the register's historical name and contains an outdated term "
               "for Black people. It is kept as written so the record can be found and cited.",
    "SRC-004": "The original letter contains discriminatory historical language. "
               "No quotation from it is reproduced here.",
    "JRN-011": "The title uses the historical term \"fugitive slave\". Current usage prefers "
               "\"freedom seeker\" or \"self-emancipated person\".",
}

# Curator judgement: a more specific role than 'subject' for a named person.
ROLE_OVERRIDES = {
    ("SRC-004", "Earl Bathurst"): "recipient",
}


def _ensure_institution(conn: sqlite3.Connection, name: str) -> str:
    info = INSTITUTIONS.get(name) or dict(id=f"inst_{slugify(name)}", type="other")
    conn.execute(
        "INSERT OR IGNORE INTO institution "
        "(id, name, type, website_url, catalogue_url, location, description, rights_policy_url) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            info["id"], name, info["type"], info.get("website_url"), info.get("catalogue_url"),
            info.get("location"), info.get("description"), info.get("rights_policy_url"),
        ),
    )
    return info["id"]


def _institution_policy(conn: sqlite3.Connection, inst_id: str) -> str | None:
    row = conn.execute("SELECT rights_policy_url FROM institution WHERE id = ?", (inst_id,)).fetchone()
    return row[0] if row else None


def classify_access(resource_type: str, access_text: str) -> tuple[str, str]:
    """(digitized, access_mode) derived by rule from the team's access text."""
    t = (access_text or "").lower()
    if resource_type == "person_profile":
        return "not_applicable", "online"
    if "digitized" in t and ("in-person" in t or "in person" in t):
        return "partial", "mixed"
    if "transcription" in t:
        return "partial", "online"
    if "digitized" in t:
        return "yes", "online"
    if "html" in t or "pdf" in t:
        return "yes", "online"
    return "unknown", "unknown"


def _holder(rec_id: str, resource_type: str, source_inst: str, reference: str | None):
    if rec_id in HOLDER_OVERRIDES:
        return HOLDER_OVERRIDES[rec_id]
    if resource_type in ARCHIVAL_TYPES:
        if reference:
            return (
                source_inst, "unconfirmed",
                "The record source's own reference code points to its holdings; "
                "not independently confirmed.",
            )
        return None, "unknown", None
    # Profiles, articles, guides and book listings describe themselves.
    return None, "not_applicable", None


def _date_kind(kind_text: str | None) -> str:
    k = (kind_text or "").lower()
    if "life" in k:
        return "life"
    if "period" in k:
        return "period_discussed"
    if any(w in k for w in ("letter", "map", "register", "document", "recorded", "certificate")):
        return "document"
    return "event"


def _date_rows(rec: dict) -> list[tuple]:
    rows = []
    for d in rec.get("dates") or []:
        label = d.get("label") or ""
        start, end = d.get("startYear"), d.get("endYear")
        approx = 1 if d.get("approximate") else 0
        origin = "source_stated"
        if start is None and end is None:
            parsed = years_from_label(label)
            if parsed:
                start, end = parsed
                approx, origin = 1, "platform_generated"
        rows.append((_date_kind(d.get("kind")), label, start, end, approx, origin))
    pub = rec.get("publicationDate")
    if pub:
        year = int(pub[:4]) if pub[:4].isdigit() else None
        rows.append(("publication", pub, year, year, 0, "source_stated"))
    return rows


def _link_entities(conn: sqlite3.Connection, rec: dict, record_id: str, resource_type: str) -> int:
    n = 0
    basis = "Listed under '{}' in the team's verified research dataset"

    def add(entity_type: str, name: str, role: str, field: str) -> None:
        nonlocal n
        eid = ensure_entity(conn, entity_type, name, rec["id"])
        link_entity(conn, record_id, eid, role, name, "source_stated", basis.format(field))
        n += 1

    author_role = "creator" if resource_type in ARCHIVAL_TYPES else "author"
    for name in rec.get("authors") or []:
        add("person", name, author_role, "authors")
    for name in rec.get("contributors") or []:
        add("person", name, "contributor", "contributors")
    for name in rec.get("people") or []:
        add("person", name, ROLE_OVERRIDES.get((rec["id"], name), "subject"), "people")
    for name in rec.get("places") or []:
        add("place", name, "location", "places")
    for name in rec.get("communities") or []:
        add("community", name, "subject", "communities")
    # A subject tag that repeats a person or community name on the same record is
    # already linked; skip it so connection pages don't show duplicates.
    already = {x.lower() for x in (rec.get("people") or []) + (rec.get("communities") or [])}
    for name in rec.get("subjects") or []:
        if name.lower() not in already:
            add("subject", name, "subject", "subjects")
    return n


def load(conn: sqlite3.Connection, path: Path, added_by: str = ADDED_BY) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    imported_at = today_iso()
    summary = {"source": Path(path).name, "records_in_file": 0, "record_rows": 0,
               "relations": 0, "links": 0, "warnings": []}

    for rec in data.get("records", []):
        summary["records_in_file"] += 1
        access_points = rec.get("accessPoints") or []
        if not access_points:
            summary["warnings"].append(f"{rec.get('id')}: no access point, skipped")
            continue
        resource_type = RESOURCE_TYPES.get((rec.get("resourceType") or "").lower(), "other")
        if resource_type == "other":
            summary["warnings"].append(f"{rec['id']}: unmapped resource type {rec.get('resourceType')!r}")
        title = rec["title"]
        container = rec.get("sourcePublication")
        if container and container.strip() == title.strip():
            container = None
        description_origin = (
            "source_paraphrased" if resource_type in ("journal_article", "book") else "curator_written"
        )
        historical_labels = [d.get("label") for d in rec.get("dates") or [] if d.get("label")]
        date_display = "; ".join(historical_labels) or None

        row_ids = []
        for ap in access_points:
            source_inst = _ensure_institution(conn, ap["institution"])
            record_id = rec["id"] if len(access_points) == 1 else f"{rec['id']}-{source_inst.removeprefix('inst_')}"
            reference = ap.get("institutionalReference")
            holding, holder_status, holder_note = _holder(rec["id"], resource_type, source_inst, reference)
            if holding == "inst_tna_uk":
                _ensure_institution(conn, "The National Archives (United Kingdom)")
            digitized, access_mode = classify_access(resource_type, ap.get("access") or "")
            conn.execute(
                """INSERT INTO record (
                    id, title_original, description, description_origin, resource_type, language,
                    date_display, content_note, container_title, notes,
                    record_source_id, holding_institution_id, holder_status, holder_note,
                    source_url, source_reference, digital_url, digitized, access_mode,
                    access_instructions, access_restrictions, rights_statement, rights_url,
                    reuse_scope, collection_method, imported_at, added_by, last_verified_at,
                    source_evidence, verification_status, link_last_checked, change_notes
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    record_id, ap.get("sourceTitle") or title, rec.get("description"),
                    description_origin, resource_type, None,
                    date_display, CONTENT_NOTES.get(rec["id"]), container, rec.get("notes"),
                    source_inst, holding, holder_status, holder_note,
                    ap["url"], reference, None, digitized, access_mode,
                    ap.get("access"), None, rec.get("rightsNotes"),
                    ap.get("policyUrl") or _institution_policy(conn, source_inst),
                    "metadata_and_link_only", "manual", imported_at, added_by,
                    rec.get("verificationDate"),
                    rec.get("sourceEvidence"),
                    "verified" if rec.get("verificationDate") else "unverified",
                    None,
                    f"Loaded from {Path(path).name} (dataset id {rec['id']}). "
                    "digitized and access_mode derived by rule from the access text.",
                ),
            )
            conn.executemany(
                "INSERT INTO record_date (record_id, kind, label, start_year, end_year, approximate, origin) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                [(record_id, *row) for row in _date_rows(rec)],
            )
            summary["links"] += _link_entities(conn, rec, record_id, resource_type)
            row_ids.append(record_id)
            summary["record_rows"] += 1

        for a, b in itertools.combinations(row_ids, 2):
            conn.execute(
                "INSERT INTO record_relation (record_a_id, record_b_id, relation_type, basis, "
                "evidence_note, status, created_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (a, b, "describes_same_resource", "curator_judgement", rec.get("notes"),
                 "confirmed", added_by, rec.get("verificationDate")),
            )
            summary["relations"] += 1
    return summary
