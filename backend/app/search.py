"""Search, record, entity and institution queries.

Search engines (same interface, chosen by what this Python's SQLite supports):
- fts5: BM25 ranking with column weights, prefix matching and English stemming.
- like: plain substring matching, used only when SQLite has no FTS5.

Every result explains why it matched, and no-result searches say so plainly.
"""
from __future__ import annotations

import difflib
import html
import re
import sqlite3
from dataclasses import dataclass, field

from . import db, labels, vocab

# Column weights for BM25: record_id (not searched), title, description, entity_names.
TITLE_W, DESC_W, ENT_W = 10.0, 3.0, 6.0
HL_OPEN, HL_CLOSE = "\x02", "\x03"
ENTITY_SEP = " | "
STOPWORDS = {"a", "an", "the", "of", "and", "or", "in", "on", "at", "to", "for", "by",
             "with", "from", "about", "records", "record", "related", "any", "some"}
# Weights for "connected records" (records sharing people, places, communities, subjects).
SHARED_WEIGHT = {"person": 3.0, "community": 3.0, "event": 3.0, "subject": 1.5, "place": 1.0}
# Roles that say who made a record. Every other role (subject, recipient, location,
# mentioned) says who or what the record is about.
MADE_BY_ROLES = {"author", "contributor", "creator"}
# A shared author or creator says less about the history than a shared subject.
MADE_BY_WEIGHT = 1.0
# A place linked to more than this share of all records (today Nova Scotia and Halifax)
# is too broad to connect two records on its own. Connections made only of such places
# are hidden; these places still count when the records share something else.
BROAD_PLACE_SHARE = 0.25
# Description excerpts in search results: about this many words, starting a few words
# before the first match.
EXCERPT_WORDS, EXCERPT_LEAD = 30, 8
HISTORICAL = "kind <> 'publication'"


# --------------------------------------------------------------------------- filters

@dataclass
class Filters:
    institution: list[str] = field(default_factory=list)       # source or holder id
    resource_type: list[str] = field(default_factory=list)
    digitized: list[str] = field(default_factory=list)
    access_mode: list[str] = field(default_factory=list)
    collection_method: list[str] = field(default_factory=list)
    entity: list[str] = field(default_factory=list)            # all must be linked
    year_from: int | None = None
    year_to: int | None = None
    include_undated: bool = False
    undated_only: bool = False                                  # only records with no historical date


def _in_clause(column: str, values: list[str], params: dict, key: str) -> str:
    names = []
    for i, v in enumerate(values):
        params[f"{key}{i}"] = v
        names.append(f":{key}{i}")
    return f"{column} IN ({', '.join(names)})"


def _filter_sql(f: Filters) -> tuple[str, dict]:
    clauses, params = [], {}
    if f.institution:
        a = _in_clause("r.record_source_id", f.institution, params, "inst_s")
        b = _in_clause("r.holding_institution_id", f.institution, params, "inst_h")
        clauses.append(f"({a} OR {b})")
    for col in ("resource_type", "digitized", "access_mode", "collection_method"):
        values = getattr(f, col)
        if values:
            clauses.append(_in_clause(f"r.{col}", values, params, col))
    for i, eid in enumerate(f.entity):
        params[f"ent{i}"] = eid
        clauses.append(
            f"EXISTS (SELECT 1 FROM record_entity re WHERE re.record_id = r.id "
            f"AND re.entity_id = :ent{i})"
        )
    if f.year_from is not None or f.year_to is not None:
        params["yf"] = f.year_from if f.year_from is not None else -100000
        params["yt"] = f.year_to if f.year_to is not None else 100000
        dated = (
            "EXISTS (SELECT 1 FROM record_date d WHERE d.record_id = r.id AND d." + HISTORICAL +
            " AND d.start_year IS NOT NULL AND COALESCE(d.end_year, d.start_year) >= :yf "
            "AND d.start_year <= :yt)"
        )
        if f.include_undated:
            dated = (
                f"({dated} OR NOT EXISTS (SELECT 1 FROM record_date d2 WHERE d2.record_id = r.id "
                f"AND d2.{HISTORICAL} AND d2.start_year IS NOT NULL))"
            )
        clauses.append(dated)
    if f.undated_only:  # the same records the "Undated" decade facet counts
        clauses.append(
            "NOT EXISTS (SELECT 1 FROM record_date d3 WHERE d3.record_id = r.id "
            f"AND d3.{HISTORICAL} AND d3.start_year IS NOT NULL)"
        )
    where = "".join(f" AND {c}" for c in clauses)
    return where, params


# --------------------------------------------------------------------------- query parsing

@dataclass
class ParsedQuery:
    text: str
    match: str | None                 # FTS5 MATCH expression (every listed term); None: nothing to search
    alternatives: list[list[str]]     # per query part: any of these strings must match
    related_terms: list[dict]         # terminology bridge groups used
    terms: list[str]                  # per query part: the words as the user typed them
    groups: list[bool] = field(default_factory=list)   # per query part: is it a synonym group?
    ignored: list[str] = field(default_factory=list)   # filler words left out of the search


def _phrase(term: str) -> str:
    return '"' + term.replace('"', " ") + '"'


def parse_query(q: str) -> ParsedQuery:
    """Split a query into parts that must all match.

    A query made only of filler words ("and or", "the") searches nothing: those words
    would only match by accident ("or" is the start of "oral" and "Orleans"), so the
    search browses all records instead, as an empty query does.
    """
    segments = vocab.segment(q)
    parts, alternatives, related, typed, groups, ignored = [], [], [], [], [], []
    for seg in segments:
        if seg["kind"] == "group":
            parts.append("(" + " OR ".join(_phrase(t) for t in seg["terms"]) + ")")
            alternatives.append(list(seg["terms"]))
            typed.append(seg["text"])
            groups.append(True)
            related.append({
                "searched": seg["text"],
                "also_searched": [t for t in seg["terms"] if t != seg["text"]],
                "group": seg["group"],
                "note": seg["note"],
            })
        elif seg["text"] in STOPWORDS:
            ignored.append(seg["text"])
        else:
            parts.append(_phrase(seg["text"]) + "*")
            alternatives.append([seg["text"]])
            typed.append(seg["text"])
            groups.append(False)
    return ParsedQuery(q, " AND ".join(parts) or None, alternatives, related, typed, groups, ignored)


# --------------------------------------------------------------------------- one count per synonym

# The index's tokens for each term, e.g. "freedom seekers" -> ("freedom", "seeker").
# Keyed by (tokenizer, term); the terms are fixed in vocab.py, so this stays small.
_TOKENS: dict[tuple[str, str], tuple[str, ...]] = {}


def _index_tokenizer(conn: sqlite3.Connection) -> str:
    row = conn.execute("SELECT sql FROM sqlite_master WHERE name = 'record_search'").fetchone()
    m = re.search(r"tokenize\s*=\s*'([^']*)'", (row[0] if row else "") or "", re.I)
    return m.group(1) if m else "unicode61"  # FTS5's default tokenizer


def _tokens(conn: sqlite3.Connection, terms: list[str]) -> dict[str, tuple[str, ...]]:
    """Each term as the full-text index sees it, from SQLite's own tokenizer."""
    tokenizer = _index_tokenizer(conn)
    missing = [t for t in dict.fromkeys(terms) if (tokenizer, t) not in _TOKENS]
    if missing:
        quoted = "'" + tokenizer.replace("'", "''") + "'"
        conn.execute(f"CREATE VIRTUAL TABLE IF NOT EXISTS temp.term_probe USING fts5(t, tokenize = {quoted})")
        conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS temp.term_probe_vocab "
                     "USING fts5vocab('temp', 'term_probe', 'instance')")
        conn.execute("DELETE FROM temp.term_probe")
        conn.executemany("INSERT INTO temp.term_probe (rowid, t) VALUES (?, ?)", list(enumerate(missing, 1)))
        found: dict[int, list[str]] = {}
        for doc, term in conn.execute("SELECT doc, term FROM temp.term_probe_vocab ORDER BY doc, offset"):
            found.setdefault(doc, []).append(term)
        conn.execute("DELETE FROM temp.term_probe")
        for i, t in enumerate(missing, 1):
            _TOKENS[(tokenizer, t)] = tuple(found.get(i, ()))
    return {t: _TOKENS[(tokenizer, t)] for t in terms}


def _contains(longer: tuple[str, ...], shorter: tuple[str, ...]) -> bool:
    n = len(shorter)
    return any(longer[i:i + n] == shorter for i in range(len(longer) - n + 1))


def distinct_phrases(conn: sqlite3.Connection, terms: list[str]) -> list[str]:
    """The terms of a synonym group that can match differently, in the group's order.

    BM25 adds one score per phrase a record contains, so phrases the index sees as the
    same ("freedom seekers" and "freedom seeker" are both "freedom seeker") would count
    one use twice. A phrase that contains another one ("mary ann shadd cary" contains
    "mary ann shadd") adds no new matches either. Both are dropped from the query; the
    records found stay the same, and every term is still listed for display.
    """
    try:
        toks = _tokens(conn, terms)
    except sqlite3.Error:  # no fts5vocab: keep every term
        return list(dict.fromkeys(terms))
    kept: list[str] = []
    for t in sorted(dict.fromkeys(terms), key=lambda t: (len(toks[t]), terms.index(t))):
        if toks[t] and not any(_contains(toks[t], toks[k]) for k in kept):
            kept.append(t)
    return sorted(kept, key=terms.index) or list(dict.fromkeys(terms))


def fts_match(conn: sqlite3.Connection, pq: ParsedQuery) -> str | None:
    """The FTS5 MATCH expression, with each synonym group's repeated forms removed."""
    if not pq.match:
        return None
    parts = []
    for alts, is_group in zip(pq.alternatives, pq.groups, strict=True):
        if is_group:
            parts.append("(" + " OR ".join(_phrase(t) for t in distinct_phrases(conn, alts)) + ")")
        else:
            parts.append(_phrase(alts[0]) + "*")
    return " AND ".join(parts)


# --------------------------------------------------------------------------- matching

def _strip(s: str) -> str:
    return s.replace(HL_OPEN, "").replace(HL_CLOSE, "")


def _reset_hits(conn: sqlite3.Connection) -> None:
    """The temporary table that holds every matching record id (for the total and facets)."""
    conn.execute("CREATE TEMP TABLE IF NOT EXISTS hits (id TEXT PRIMARY KEY)")
    conn.execute("DELETE FROM hits")


def _fts_page(conn, pq: ParsedQuery, where: str, params: dict, sort: str,
              limit: int, offset: int) -> list[dict]:
    """Match inside SQLite: every matching id goes to `hits`, and only the requested
    page is ranked out, highlighted and explained."""
    base = (f"FROM record_search JOIN record r ON r.id = record_search.record_id "
            f"WHERE record_search MATCH :q {where}")
    p = dict(params, q=fts_match(conn, pq))
    conn.execute(f"INSERT OR IGNORE INTO hits (id) SELECT r.id {base}", p)
    # Ties keep the index order, so pages never overlap or skip a record.
    order = f"{_SORTS[sort]}, record_search.rowid" if sort in _SORTS else "score, record_search.rowid"
    sql = f"""
        SELECT r.id AS id,
               bm25(record_search, 0.0, {TITLE_W}, {DESC_W}, {ENT_W}) AS score,
               highlight(record_search, 1, :hl_o, :hl_c) AS hl_title,
               highlight(record_search, 2, :hl_o, :hl_c) AS hl_desc,
               highlight(record_search, 3, :hl_o, :hl_c) AS hl_ent
        {base}
        ORDER BY {order}
        LIMIT :limit OFFSET :offset
    """
    page = []
    for row in conn.execute(sql, dict(p, hl_o=HL_OPEN, hl_c=HL_CLOSE, limit=limit, offset=offset)):
        ents = [_strip(x) for x in (row["hl_ent"] or "").split(ENTITY_SEP) if HL_OPEN in x]
        page.append({
            "id": row["id"],
            "score": round(-row["score"], 4),  # higher is better
            "fields": [name for name, hl in (("title", row["hl_title"]),
                                             ("description", row["hl_desc"])) if hl and HL_OPEN in hl]
                      + (["people, places or subjects"] if ents else []),
            "entities": ents,
            "text": " ".join(_strip(row[k] or "") for k in ("hl_title", "hl_desc", "hl_ent")).lower(),
            "hl_title": row["hl_title"] or "",
            "hl_desc": row["hl_desc"] or "",
        })
    return page


def _like_pattern(pq: ParsedQuery) -> re.Pattern | None:
    """Every query term as one regex, longest first, ignoring case, curly quotes and spacing."""
    terms = sorted({vocab.normalize(a) for alts in pq.alternatives for a in alts if a.strip()},
                   key=len, reverse=True)
    if not terms:
        return None

    def one(term: str) -> str:
        return r"\s+".join("".join("['‘’]" if ch == "'" else re.escape(ch) for ch in word)
                           for word in term.split())
    return re.compile("|".join(one(t) for t in terms), re.I)


def _mark(text: str, pattern: re.Pattern | None) -> str:
    """Wrap each match of pattern in the highlight markers, as FTS5's highlight() does."""
    if not pattern or not text:
        return text or ""
    return pattern.sub(lambda m: HL_OPEN + m.group(0) + HL_CLOSE, text)


def _like_page(conn, pq: ParsedQuery, where: str, params: dict, sort: str,
               limit: int, offset: int) -> list[dict]:
    """The fallback engine scores in Python, so it matches every record, then pages."""
    sql = f"""
        SELECT r.id AS id, s.title, s.description, s.entity_names
        FROM record_search s JOIN record r ON r.id = s.record_id
        WHERE 1 = 1 {where}
    """
    pattern = _like_pattern(pq)
    hits = []
    for row in conn.execute(sql, params):
        title = vocab.normalize(row["title"] or "")
        desc = vocab.normalize(row["description"] or "")
        ent_list = [e for e in (row["entity_names"] or "").split(ENTITY_SEP) if e]
        ents = vocab.normalize(" | ".join(ent_list))
        score, fields, matched_ents, ok = 0.0, set(), set(), True
        for alts in pq.alternatives:
            best = 0.0
            for a in alts:
                a = vocab.normalize(a)
                if a in title:
                    best = max(best, TITLE_W); fields.add("title")
                if a in ents:
                    best = max(best, ENT_W); fields.add("people, places or subjects")
                    matched_ents.update(e for e in ent_list if a in vocab.normalize(e))
                if a in desc:
                    best = max(best, DESC_W); fields.add("description")
            if best == 0:
                ok = False
                break
            score += best
        if ok:
            hits.append({"id": row["id"], "score": score,
                         "fields": [f for f in ("title", "description", "people, places or subjects") if f in fields],
                         "entities": sorted(matched_ents),
                         "text": " ".join([title, desc, ents]),
                         "hl_title": _mark(row["title"] or "", pattern),
                         "hl_desc": _mark(row["description"] or "", pattern) if "description" in fields
                         else row["description"] or ""})
    if sort in _SORTS:
        order = {r[0]: i for i, r in enumerate(conn.execute(
            f"SELECT r.id FROM record r WHERE 1 = 1 {where} ORDER BY {_SORTS[sort]}, r.rowid", params))}
        hits.sort(key=lambda h: order.get(h["id"], 1 << 30))
    else:
        hits.sort(key=lambda h: -h["score"])
    conn.executemany("INSERT OR IGNORE INTO hits (id) VALUES (?)", [(h["id"],) for h in hits])
    return hits[offset: offset + limit]


# --------------------------------------------------------------------------- highlights

def _runs(marked: str) -> list[tuple[str, bool]]:
    """Split highlight() output into (text, is_match) pieces."""
    runs, buf, inside = [], [], False
    for ch in marked:
        if ch in (HL_OPEN, HL_CLOSE):
            if buf:
                runs.append(("".join(buf), inside))
                buf = []
            inside = ch == HL_OPEN
        else:
            buf.append(ch)
    if buf:
        runs.append(("".join(buf), inside))
    return runs


def _render(runs: list[tuple[str, bool]], start: int = 0, end: int | None = None) -> str:
    """HTML for the characters start..end: text escaped, matches wrapped in <mark>."""
    out, pos = [], 0
    for text, hit in runs:
        a, b = max(start, pos), min(pos + len(text), end if end is not None else pos + len(text))
        if a < b:
            piece = html.escape(text[a - pos:b - pos])
            out.append(f"<mark>{piece}</mark>" if hit else piece)
        pos += len(text)
    return "".join(out)


def highlight_title(marked: str) -> str:
    """The whole title as HTML with the matched words in <mark>."""
    return _render(_runs(marked))


def description_excerpt(marked: str, description: str | None) -> str | None:
    """About EXCERPT_WORDS words of the description around its first match, as HTML
    with <mark>, or None when the description itself has no match.

    The index's description field also holds the journal name and catalogue reference
    after the description, so only the part that is the description is used.
    """
    desc = (description or "").strip(" ")  # the index trims spaces, as SQL TRIM() does
    runs = _runs(marked)
    plain = "".join(t for t, _ in runs)
    if not desc.strip() or not plain.startswith(desc):
        return None
    end_desc = len(desc)
    pos, first = 0, None
    for text, hit in runs:
        if hit and pos < end_desc:
            first = pos
            break
        pos += len(text)
    if first is None:
        return None
    words = [m.span() for m in re.finditer(r"\S+", plain[:end_desc])]
    i = next((k for k, (a, b) in enumerate(words) if b > first), len(words) - 1)
    lo = max(0, min(i - EXCERPT_LEAD, len(words) - EXCERPT_WORDS))
    hi = min(len(words), lo + EXCERPT_WORDS)
    start, end = words[lo][0], words[hi - 1][1]
    return (("… " if lo > 0 else "") + _render(runs, start, end)
            + (" …" if hi < len(words) else ""))


def _why(hit: dict, pq: ParsedQuery, roles: dict[str, list[str]]) -> dict:
    ents = [{"name": n, "roles": roles.get(n, [])} for n in hit["entities"]]
    related = []
    for g in pq.related_terms:
        searched = g["searched"]
        # Terms from the group found in this record, other than the one typed
        # (and its plural/singular form).
        used = [t for t in g["also_searched"]
                if t in hit["text"] and t not in searched and searched not in t]
        # Drop terms contained in a longer matched term ("slave" inside "fugitive slave").
        used = [t for t in used if not any(t != u and t in u for u in used)]
        if used:
            related.append({"searched": searched, "matched": used})
    parts = []
    if "title" in hit["fields"]:
        parts.append("Title")
    if "description" in hit["fields"]:
        parts.append("Description")
    parts += [f"{e['name']} ({', '.join(e['roles'])})" if e["roles"] else e["name"] for e in ents]
    parts += [f"related term {', '.join(repr(m) for m in r['matched'])} for {r['searched']!r}"
              for r in related]
    return {"summary": "Matched: " + "; ".join(parts) if parts else "Matched",
            "fields": hit["fields"], "entities": ents, "related_terms": related}


# --------------------------------------------------------------------------- summaries

_SUMMARY_SQL = """
SELECT r.id, r.title_original, r.resource_type, r.date_display, r.description, r.content_note,
       r.source_url, r.digitized, r.access_mode, r.collection_method, r.verification_status,
       r.last_verified_at, r.holder_status,
       src.id AS src_id, src.name AS src_name,
       hold.id AS hold_id, hold.name AS hold_name,
       (SELECT MIN(start_year) FROM record_date d WHERE d.record_id = r.id AND d.kind <> 'publication')
           AS earliest_year
FROM record r
JOIN institution src ON src.id = r.record_source_id
LEFT JOIN institution hold ON hold.id = r.holding_institution_id
WHERE r.id IN ({ids})
"""


def _placeholders(ids: list[str], params: dict, key: str = "id") -> str:
    return ", ".join(_param_list(ids, params, key))


def _param_list(ids, params, key):
    out = []
    for i, v in enumerate(ids):
        params[f"{key}{i}"] = v
        out.append(f":{key}{i}")
    return out


def summaries(conn: sqlite3.Connection, ids: list[str]) -> dict[str, dict]:
    if not ids:
        return {}
    params: dict = {}
    rows = conn.execute(_SUMMARY_SQL.format(ids=_placeholders(ids, params)), params).fetchall()
    out = {}
    for r in rows:
        out[r["id"]] = {
            "id": r["id"],
            "title": r["title_original"],
            "resource_type": r["resource_type"],
            "date_display": r["date_display"],
            "earliest_year": r["earliest_year"],
            "description": r["description"],
            "content_note": r["content_note"],
            "record_source": {"id": r["src_id"], "name": r["src_name"]},
            "holding_institution": {"id": r["hold_id"], "name": r["hold_name"]} if r["hold_id"] else None,
            "holder_status": r["holder_status"],
            "digitized": r["digitized"],
            "access_mode": r["access_mode"],
            "source_url": r["source_url"],
            "collection_method": r["collection_method"],
            "verification_status": r["verification_status"],
            "last_verified_at": r["last_verified_at"],
        }
    # People, places, communities, subjects per record.
    params = {}
    for row in conn.execute(
        f"""SELECT re.record_id, e.id, e.name_preferred, e.entity_type, re.role
            FROM record_entity re JOIN entity e ON e.id = re.entity_id
            WHERE re.record_id IN ({_placeholders(ids, params)})
            ORDER BY e.entity_type, e.name_preferred""", params):
        s = out.get(row["record_id"])
        if s is None:
            continue
        bucket = s.setdefault("entities", {}).setdefault(row["entity_type"], [])
        existing = next((x for x in bucket if x["id"] == row["id"]), None)
        if existing:
            existing["roles"].append(row["role"])
        else:
            bucket.append({"id": row["id"], "name": row["name_preferred"], "roles": [row["role"]]})
    # Other institutions' descriptions of the same resource (curated, confirmed).
    for rid, other in _same_resource_pairs(conn, ids):
        s = out[rid]
        s.setdefault("also_available_from", []).append(other)
    for s in out.values():
        s.setdefault("entities", {})
        s.setdefault("also_available_from", [])
    return out


def _same_resource_pairs(conn, ids):
    params: dict = {}
    ph = _placeholders(ids, params)
    rows = conn.execute(
        f"""SELECT rr.record_a_id AS a, rr.record_b_id AS b FROM record_relation rr
            WHERE rr.relation_type = 'describes_same_resource' AND rr.status = 'confirmed'
              AND (rr.record_a_id IN ({ph}) OR rr.record_b_id IN ({ph}))""", params).fetchall()
    wanted = set(ids)
    for row in rows:
        for mine, other in ((row["a"], row["b"]), (row["b"], row["a"])):
            if mine in wanted:
                o = conn.execute(
                    "SELECT r.id, r.source_url, i.name FROM record r JOIN institution i "
                    "ON i.id = r.record_source_id WHERE r.id = ?", (other,)).fetchone()
                if o:
                    yield mine, {"record_id": o["id"], "institution": o["name"], "source_url": o["source_url"]}


# --------------------------------------------------------------------------- search

_SORTS = {
    "title": "r.title_original COLLATE NOCASE",
    "date": "(SELECT MIN(start_year) FROM record_date d WHERE d.record_id = r.id AND d.kind <> 'publication') "
            "IS NULL, (SELECT MIN(start_year) FROM record_date d WHERE d.record_id = r.id "
            "AND d.kind <> 'publication'), r.title_original COLLATE NOCASE",
}


def _facets(conn: sqlite3.Connection) -> dict:
    """Counts over every matching record (the `hits` table), not just the page."""
    def counts(column: str) -> list[dict]:
        return [{"value": r[0], "label": labels.label(column, r[0]), "count": r[1]} for r in conn.execute(
            f"SELECT r.{column}, COUNT(*) FROM record r JOIN hits h ON h.id = r.id "
            f"GROUP BY 1 ORDER BY 2 DESC, 1")]

    facets = {c: counts(c) for c in ("resource_type", "digitized", "access_mode", "collection_method")}
    facets["institution"] = [
        {"value": r[0], "label": r[1], "count": r[2]} for r in conn.execute(
            "SELECT i.id, i.name, COUNT(*) FROM record r JOIN hits h ON h.id = r.id "
            "JOIN institution i ON i.id = r.record_source_id GROUP BY i.id ORDER BY 3 DESC, 2")]
    decades: dict = {}
    for (y,) in conn.execute(
        "SELECT (SELECT MIN(start_year) FROM record_date d WHERE d.record_id = r.id "
        "AND d.kind <> 'publication') FROM record r JOIN hits h ON h.id = r.id"):
        key = "undated" if y is None else f"{(y // 10) * 10}s"
        decades[key] = decades.get(key, 0) + 1
    # Each decade carries the filter it stands for: "1950s" -> year_from=1950, year_to=1959;
    # "undated" -> undated_only=true.
    facets["decade"] = [
        {"value": k, "label": "Undated" if k == "undated" else k, "count": v,
         "year_from": None if k == "undated" else int(k[:-1]),
         "year_to": None if k == "undated" else int(k[:-1]) + 9,
         "undated_only": k == "undated"}
        for k, v in sorted(decades.items(), key=lambda kv: (kv[0] == "undated", kv[0]))]
    # roles: how each entity appears in these results, so the frontend can tell
    # authors ("author") apart from the people the records are about ("subject").
    for etype in ("person", "place", "community", "subject"):
        facets[etype] = [
            {"value": r[0], "label": r[1], "count": r[2], "roles": sorted(r[3].split(","))}
            for r in conn.execute(
                "SELECT e.id, e.name_preferred, COUNT(DISTINCT re.record_id), GROUP_CONCAT(DISTINCT re.role) "
                "FROM record_entity re "
                "JOIN hits h ON h.id = re.record_id JOIN entity e ON e.id = re.entity_id "
                "WHERE e.entity_type = ? GROUP BY e.id ORDER BY 3 DESC, 2 LIMIT 15", (etype,))]
    return facets


def suggest_corrections(conn: sqlite3.Connection, q: str) -> list[str]:
    names = [r[0] for r in conn.execute("SELECT name_preferred FROM entity")]
    names += [r[0] for r in conn.execute("SELECT title_original FROM record")]
    lower = {vocab.normalize(n): n for n in names}
    found = difflib.get_close_matches(vocab.normalize(q), list(lower), n=3, cutoff=0.75)
    if found:
        return [lower[f] for f in found]
    # Word by word: "africvile history" -> "africville history"
    words = {w for n in lower for w in n.replace("|", " ").split() if len(w) > 3}
    fixed, changed = [], False
    for tok in vocab.normalize(q).split():
        if tok in words or len(tok) <= 3:
            fixed.append(tok)
            continue
        m = difflib.get_close_matches(tok, list(words), n=1, cutoff=0.8)
        fixed.append(m[0] if m else tok)
        changed = changed or bool(m)
    return [" ".join(fixed)] if changed else []


def search(conn: sqlite3.Connection, q: str = "", filters: Filters | None = None,
           sort: str = "relevance", limit: int = 20, offset: int = 0) -> dict:
    filters = filters or Filters()
    where, params = _filter_sql(filters)
    q = (q or "").strip()
    engine = db.search_engine(conn)
    pq = parse_query(q) if q else None
    matched = bool(pq and pq.match)  # False for an empty query or one of only filler words

    _reset_hits(conn)
    if matched:
        try:
            page_fn = _fts_page if engine == "fts5" else _like_page
            page = page_fn(conn, pq, where, params, sort, limit, offset)
        except sqlite3.OperationalError:
            engine = "like"  # unusual characters the FTS parser rejects
            _reset_hits(conn)
            page = _like_page(conn, pq, where, params, sort, limit, offset)
    else:  # browse: every record that passes the filters
        conn.execute(f"INSERT OR IGNORE INTO hits (id) SELECT r.id FROM record r WHERE 1 = 1 {where}", params)
        order_by = _SORTS.get(sort, _SORTS["title"])
        page = [{"id": r[0], "score": None} for r in conn.execute(
            f"SELECT r.id FROM record r WHERE 1 = 1 {where} ORDER BY {order_by}, r.rowid "
            f"LIMIT :limit OFFSET :offset", dict(params, limit=limit, offset=offset))]
    total = conn.execute("SELECT COUNT(*) FROM hits").fetchone()[0]

    info = summaries(conn, [h["id"] for h in page])
    results = []
    for h in page:
        card = dict(info[h["id"]])
        card["score"] = h["score"]
        if matched:
            roles = {}
            for etype_list in card["entities"].values():
                for e in etype_list:
                    roles[e["name"]] = e["roles"]
            card["why"] = _why(h, pq, roles)
            # HTML with the matched words in <mark>; record text is escaped first.
            card["highlight"] = {"title": highlight_title(h["hl_title"]),
                                 "description": description_excerpt(h["hl_desc"], card["description"])}
        results.append(card)

    total_records = conn.execute("SELECT COUNT(*) FROM record").fetchone()[0]
    total_institutions = conn.execute(
        "SELECT COUNT(DISTINCT record_source_id) FROM record").fetchone()[0]
    message = None
    suggestions: list[str] = []
    if total == 0:
        message = (f"No records in this index match. The index currently holds {total_records} "
                   f"records from {total_institutions} institutions, so this does not mean the "
                   f"material doesn't exist.")
        if matched:
            suggestions = suggest_corrections(conn, q)
    return {
        "query": q,
        "engine": engine,
        "total": total,
        "limit": limit,
        "offset": offset,
        "results": results,
        "facets": _facets(conn),
        "interpreted": {"terms": pq.terms if pq else [],
                        "related_terms": pq.related_terms if pq else [],
                        "ignored": pq.ignored if pq else []},
        "suggestions": suggestions,
        "message": message,
    }


# --------------------------------------------------------------------------- detail pages

def get_record(conn: sqlite3.Connection, record_id: str) -> dict | None:
    r = conn.execute("SELECT * FROM record WHERE id = ?", (record_id,)).fetchone()
    if not r:
        return None
    card = summaries(conn, [record_id])[record_id]

    def inst(iid):
        row = conn.execute("SELECT * FROM institution WHERE id = ?", (iid,)).fetchone() if iid else None
        return dict(row) if row else None

    card.update({
        "description_origin": r["description_origin"],
        "language": r["language"],
        "container_title": r["container_title"],
        "notes": r["notes"],
        "record_source": inst(r["record_source_id"]),
        "holding_institution": inst(r["holding_institution_id"]),
        "holder_note": r["holder_note"],
        "dates": [dict(d) for d in conn.execute(
            "SELECT kind, label, start_year, end_year, approximate, origin FROM record_date "
            "WHERE record_id = ? ORDER BY kind = 'publication', start_year", (record_id,))],
        "access": {k: r[k] for k in ("source_url", "source_reference", "digital_url", "digitized",
                                     "access_mode", "access_instructions", "access_restrictions")},
        "rights": {k: r[k] for k in ("rights_statement", "rights_url", "reuse_scope")},
        "provenance": {k: r[k] for k in ("collection_method", "imported_at", "added_by",
                                         "last_verified_at", "source_evidence", "verification_status",
                                         "link_last_checked", "change_notes", "description_origin")},
    })
    # Curated relations (both directions).
    relations = []
    for rel in conn.execute(
        "SELECT * FROM record_relation WHERE (record_a_id = ? OR record_b_id = ?) AND status <> 'rejected'",
        (record_id, record_id)):
        other = rel["record_b_id"] if rel["record_a_id"] == record_id else rel["record_a_id"]
        o = summaries(conn, [other]).get(other)
        if o:
            relations.append({"relation_type": rel["relation_type"], "basis": rel["basis"],
                              "status": rel["status"], "evidence_note": rel["evidence_note"],
                              "record": {k: o[k] for k in ("id", "title", "record_source", "source_url",
                                                           "resource_type")}})
    card["relations"] = relations
    card["connected"] = connected_records(conn, record_id, exclude={x["record"]["id"] for x in relations})
    return card


def _same_maker_label(roles: set[str]) -> str:
    """Label for an entity that made both records (wrote, created or contributed)."""
    made = roles & MADE_BY_ROLES
    if made == {"author"}:
        return "Same author"
    if made == {"creator"}:
        return "Same creator"
    if made == {"contributor"}:
        return "Same contributor"
    return labels.LABELS["connection_link"]["same_author"]


def _connection(entity_type: str, roles_here: set[str], roles_there: set[str]) -> tuple[str, str, float]:
    """How one shared entity links two records: (link code, label, weight).

    It is a shared subject (or place) only when both records are about it. Someone
    who wrote both records is the same author, never a subject the records share.
    """
    about_here, about_there = roles_here - MADE_BY_ROLES, roles_there - MADE_BY_ROLES
    if about_here and about_there:
        link = "shared_place" if entity_type == "place" else "shared_subject"
        return link, labels.LABELS["connection_link"][link], SHARED_WEIGHT.get(entity_type, 1.0)
    made_here, made_there = roles_here & MADE_BY_ROLES, roles_there & MADE_BY_ROLES
    if made_here and made_there:
        return "same_author", _same_maker_label(made_here | made_there), MADE_BY_WEIGHT
    # Made one record and is named in the other.
    return "named_in_both", labels.LABELS["connection_link"]["named_in_both"], MADE_BY_WEIGHT


def _shared_summary(items: list[dict]) -> str:
    """Join names by label, e.g. "Shares a subject: Africville; Same author: Tina Loo"."""
    groups: dict[str, list[str]] = {}
    for x in items:
        groups.setdefault(x["label"], []).append(x["name"])
    return "; ".join(f"{k}: {', '.join(v)}" for k, v in groups.items())


def broad_places(conn: sqlite3.Connection) -> set[str]:
    """Places linked to more than BROAD_PLACE_SHARE of all records."""
    total = conn.execute("SELECT COUNT(*) FROM record").fetchone()[0]
    return {r[0] for r in conn.execute(
        """SELECT e.id FROM entity e JOIN record_entity re ON re.entity_id = e.id
           WHERE e.entity_type = 'place' GROUP BY e.id
           HAVING COUNT(DISTINCT re.record_id) > ?""", (BROAD_PLACE_SHARE * total,))}


def connected_records(conn: sqlite3.Connection, record_id: str, exclude: set[str] | None = None,
                      limit: int = 6) -> list[dict]:
    """Other records sharing people, places, communities or subjects (found by query).

    Each shared entity says how it links the two records (``link`` and ``label``) and
    its roles in each record, so an author of both records is shown as the same
    author and never as a subject the records share.
    """
    exclude = (exclude or set()) | {record_id}
    pairs: dict[tuple[str, str], dict] = {}
    for row in conn.execute(
        """SELECT re2.record_id AS other, e.id, e.name_preferred, e.entity_type,
                  re1.role AS role_here, re2.role AS role_there
           FROM record_entity re1
           JOIN record_entity re2 ON re2.entity_id = re1.entity_id AND re2.record_id <> re1.record_id
           JOIN entity e ON e.id = re1.entity_id
           WHERE re1.record_id = ?""", (record_id,)):
        if row["other"] in exclude:
            continue
        p = pairs.setdefault((row["other"], row["id"]), {
            "id": row["id"], "name": row["name_preferred"], "type": row["entity_type"],
            "roles_here": set(), "roles_there": set()})
        p["roles_here"].add(row["role_here"])
        p["roles_there"].add(row["role_there"])
    shared: dict[str, dict] = {}
    for (other, _), p in pairs.items():
        link, text, weight = _connection(p["type"], p["roles_here"], p["roles_there"])
        s = shared.setdefault(other, {"score": 0.0, "shared": []})
        s["score"] += weight
        s["shared"].append({"id": p["id"], "name": p["name"], "type": p["type"], "link": link,
                            "label": text, "weight": weight, "roles_here": sorted(p["roles_here"]),
                            "roles_there": sorted(p["roles_there"])})
    # Hide connections made only of broad places: two records that share nothing but
    # "Nova Scotia" (today 18 of the 27 records) or "Halifax" say little about each other.
    broad = broad_places(conn)
    shared = {k: s for k, s in shared.items()
              if not all(x["link"] == "shared_place" and x["id"] in broad for x in s["shared"])}
    top = sorted(shared.items(), key=lambda kv: (-kv[1]["score"], kv[0]))[:limit]
    info = summaries(conn, [k for k, _ in top])
    out = []
    for rid, s in top:
        o = info[rid]
        items = sorted(s["shared"], key=lambda x: (-x["weight"], x["name"]))
        out.append({"id": rid, "title": o["title"], "resource_type": o["resource_type"],
                    "record_source": o["record_source"], "score": s["score"],
                    "summary": _shared_summary(items), "shared": items})
    return out


def list_entities(conn: sqlite3.Connection, entity_type: str | None = None, q: str | None = None,
                  limit: int = 100) -> list[dict]:
    sql = """SELECT e.id, e.entity_type, e.name_preferred, e.disambiguator,
                    COUNT(DISTINCT re.record_id) AS record_count,
                    COUNT(DISTINCT r.record_source_id) AS institution_count,
                    GROUP_CONCAT(DISTINCT re.role) AS roles
             FROM entity e JOIN record_entity re ON re.entity_id = e.id
             JOIN record r ON r.id = re.record_id WHERE 1 = 1"""
    params: dict = {"limit": limit}
    if entity_type:
        sql += " AND e.entity_type = :t"
        params["t"] = entity_type
    if q:
        sql += " AND e.name_preferred LIKE :q"
        params["q"] = f"%{q}%"
    sql += " GROUP BY e.id ORDER BY record_count DESC, e.name_preferred COLLATE NOCASE LIMIT :limit"
    out = []
    for r in conn.execute(sql, params):
        row = dict(r)
        row["roles"] = sorted(row["roles"].split(",")) if row["roles"] else []  # e.g. ["author"]
        out.append(row)
    return out


_CO_RELATIONS = ("named_together", "made_record_naming", "named_in_work_by", "co_credited")
_MAKER_PHRASE = {"author": "Author of", "creator": "Creator of", "contributor": "Contributor to"}


def _n_records(n: int) -> str:
    return f"{n} record" if n == 1 else f"{n} records"


def _co_relation(mine: set[str], theirs: set[str]) -> str:
    """How another entity shares one record with this entity, from this entity's side."""
    mine_about, theirs_about = mine - MADE_BY_ROLES, theirs - MADE_BY_ROLES
    if mine_about and theirs_about:
        return "named_together"       # the record is about both
    if mine_about:
        return "made_record_naming"   # they made a record that names this entity
    if theirs_about:
        return "named_in_work_by"     # this entity made a record that names them
    return "co_credited"              # both made it


def _co_label(relation: str, n: int, name: str, made_roles: set[str]) -> str:
    if relation == "named_together":
        return "In the same record" if n == 1 else f"In {n} of the same records"
    if relation == "made_record_naming":
        phrase = _MAKER_PHRASE[next(iter(made_roles))] if len(made_roles) == 1 else "Credited on"
        return f"{phrase} {_n_records(n)} naming {name}"
    if relation == "named_in_work_by":
        return f"Named in {_n_records(n)} by {name}"
    return f"Credited with {name} on {_n_records(n)}"


def _appears_with(conn: sqlite3.Connection, entity_id: str, name: str, limit: int = 12) -> list[dict]:
    """Other entities named in the same records as this one, and how they share them.

    Sharing a record never means two people met or worked together, so each item says
    exactly how the record links them: the author of a book about Viola Desmond is
    "Author of 1 record naming Viola Desmond", not someone she appears with.
    """
    per_record: dict[tuple[str, str], dict] = {}
    for row in conn.execute(
        """SELECT e2.id, e2.name_preferred AS name, e2.entity_type, re2.record_id,
                  re1.role AS my_role, re2.role AS their_role
           FROM record_entity re1
           JOIN record_entity re2 ON re2.record_id = re1.record_id AND re2.entity_id <> re1.entity_id
           JOIN entity e2 ON e2.id = re2.entity_id
           WHERE re1.entity_id = ?""", (entity_id,)):
        p = per_record.setdefault((row["id"], row["record_id"]), {
            "name": row["name"], "entity_type": row["entity_type"], "mine": set(), "theirs": set()})
        p["mine"].add(row["my_role"])
        p["theirs"].add(row["their_role"])
    others: dict[str, dict] = {}
    for (oid, rec), p in per_record.items():
        relation = _co_relation(p["mine"], p["theirs"])
        o = others.setdefault(oid, {"name": p["name"], "entity_type": p["entity_type"], "records": set(),
                                    "roles": set(), "by_relation": {}, "made_roles": {}})
        o["records"].add(rec)
        o["roles"] |= p["theirs"]
        o["by_relation"].setdefault(relation, set()).add(rec)
        o["made_roles"].setdefault(relation, set()).update(p["theirs"] & MADE_BY_ROLES)
    out = []
    for oid, o in others.items():
        # Most shared records first; ties follow the order of _CO_RELATIONS.
        ranked = sorted(o["by_relation"], key=lambda r: (-len(o["by_relation"][r]), _CO_RELATIONS.index(r)))
        out.append({
            "id": oid, "name": o["name"], "entity_type": o["entity_type"],
            "shared_records": len(o["records"]), "roles": sorted(o["roles"]),
            "relation": ranked[0],
            "label": "; ".join(_co_label(r, len(o["by_relation"][r]), name, o["made_roles"][r])
                               for r in ranked),
        })
    out.sort(key=lambda x: (-x["shared_records"], x["name"]))
    return out[:limit]


def get_entity(conn: sqlite3.Connection, entity_id: str) -> dict | None:
    e = conn.execute("SELECT * FROM entity WHERE id = ?", (entity_id,)).fetchone()
    if not e:
        return None
    roles: dict[str, list[str]] = {}
    for row in conn.execute("SELECT record_id, role FROM record_entity WHERE entity_id = ?", (entity_id,)):
        roles.setdefault(row["record_id"], []).append(row["role"])
    info = summaries(conn, list(roles))
    records = sorted(info.values(), key=lambda s: (s["earliest_year"] is None, s["earliest_year"] or 0, s["title"]))
    for s in records:
        s["roles"] = roles[s["id"]]
    co = _appears_with(conn, entity_id, e["name_preferred"])
    return {
        **dict(e),
        "aliases": vocab.aliases_for(e["name_preferred"]),
        "record_count": len(records),
        "institution_count": len({s["record_source"]["id"] for s in records}),
        "records": records,
        "appears_with": co,
    }


def list_institutions(conn: sqlite3.Connection) -> list[dict]:
    return [dict(r) for r in conn.execute(
        """SELECT i.*,
                  (SELECT COUNT(*) FROM record r WHERE r.record_source_id = i.id) AS records_supplied,
                  (SELECT COUNT(*) FROM record r WHERE r.holding_institution_id = i.id) AS records_held,
                  (SELECT MAX(last_verified_at) FROM record r WHERE r.record_source_id = i.id) AS last_verified
           FROM institution i ORDER BY records_supplied DESC, i.name""")]


def get_institution(conn: sqlite3.Connection, institution_id: str) -> dict | None:
    row = next((i for i in list_institutions(conn) if i["id"] == institution_id), None)
    if not row:
        return None
    supplied = [r[0] for r in conn.execute(
        "SELECT id FROM record WHERE record_source_id = ? ORDER BY title_original", (institution_id,))]
    held = [r[0] for r in conn.execute(
        "SELECT id FROM record WHERE holding_institution_id = ? ORDER BY title_original", (institution_id,))]
    info = summaries(conn, list(dict.fromkeys(supplied + held)))
    return {**row, "records": [info[i] for i in supplied], "holds_originals_for": [info[i] for i in held]}


def suggest(conn: sqlite3.Connection, q: str, limit: int = 8) -> list[dict]:
    q = (q or "").strip()
    if not q:
        return []
    out = [{"kind": "entity", "id": r["id"], "label": r["name_preferred"], "entity_type": r["entity_type"],
            "record_count": r["record_count"]}
           for r in conn.execute(
               """SELECT e.id, e.name_preferred, e.entity_type, COUNT(DISTINCT re.record_id) AS record_count
                  FROM entity e JOIN record_entity re ON re.entity_id = e.id
                  WHERE e.name_preferred LIKE :prefix OR e.name_preferred LIKE :inner
                  GROUP BY e.id
                  ORDER BY e.name_preferred LIKE :prefix DESC, record_count DESC, e.name_preferred
                  LIMIT :limit""",
               {"prefix": f"{q}%", "inner": f"% {q}%", "limit": limit})]
    out += [{"kind": "record", "id": r["id"], "label": r["title_original"]}
            for r in conn.execute("SELECT id, title_original FROM record WHERE title_original LIKE ? "
                                  "ORDER BY title_original LIMIT ?", (f"%{q}%", max(0, limit - len(out))))]
    return out


def stats(conn: sqlite3.Connection) -> dict:
    def grouped(col):
        return {r[0]: r[1] for r in conn.execute(f"SELECT {col}, COUNT(*) FROM record GROUP BY 1 ORDER BY 2 DESC")}
    return {
        "records": conn.execute("SELECT COUNT(*) FROM record").fetchone()[0],
        "institutions_supplying": conn.execute("SELECT COUNT(DISTINCT record_source_id) FROM record").fetchone()[0],
        "institutions_total": conn.execute("SELECT COUNT(*) FROM institution").fetchone()[0],
        "entities": {r[0]: r[1] for r in conn.execute("SELECT entity_type, COUNT(*) FROM entity GROUP BY 1")},
        "by_collection_method": grouped("collection_method"),
        "by_verification_status": grouped("verification_status"),
        "by_resource_type": grouped("resource_type"),
        "by_digitized": grouped("digitized"),
        "links_checked": conn.execute("SELECT COUNT(*) FROM record WHERE link_last_checked IS NOT NULL").fetchone()[0],
        "search_engine": db.search_engine(conn),
    }
