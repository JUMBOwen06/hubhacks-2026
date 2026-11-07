# Backend: Black History Discovery Hub API

Python + SQLite + FastAPI. It indexes descriptions of records held by other
institutions and links to the authoritative source. It never copies collections.

The JSON in `data-sets/` is the master copy. The SQLite database is a build artifact:
the API rebuilds it from the dataset every time it starts.

## Run it

Needs Python 3.10 or newer. From the repo root:

**Windows (PowerShell)**
```powershell
cd backend
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**macOS / Linux**
```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/docs to try every endpoint in the browser.

Check whether your Python's SQLite has full-text search (FTS5). If it doesn't, search
still works, using simpler text matching:
```bash
python -c "import sqlite3; sqlite3.connect(':memory:').execute('create virtual table t using fts5(a)'); print('FTS5 OK')"
```

Build the database without starting the server: `python -m app.build`
Run the tests: `pip install -r requirements-dev.txt` then `pytest`

Tip: the repo lives in OneDrive. If SQLite reports "database is locked", point the
database at a local folder: `$env:HUBHACKS_DB="$env:TEMP\hubhacks.db"` (PowerShell).

## Endpoints (all GET)

| Endpoint | What it returns |
| --- | --- |
| `/search?q=` | Results with a "why this matched" explanation, filter counts (facets), and suggestions when nothing matches |
| `/records/{id}` | Full record: access, rights, provenance, dates, people/places, curated relations, connected records |
| `/entities?type=person\|place\|community\|subject` | Browse lists with record counts |
| `/entities/{id}` | Connection page, e.g. `/entities/community:africville` |
| `/institutions`, `/institutions/{id}` | Sources page: what each institution supplies or holds |
| `/suggest?q=` | Autocomplete: people, places, communities, subjects, titles |
| `/stats` | Counts for the About page and the pitch |
| `/vocab` | The terminology bridge (draft), shown for transparency |
| `/health` | Record count and search engine in use |

### `/search` filters
All optional, and every list filter can repeat (`resource_type=book&resource_type=map`).

`institution` (source or holder id), `resource_type`, `digitized`, `access_mode`,
`collection_method` (`manual` = verified tier, `export` = imported), `entity` (entity id;
records must link to all), `year_from`, `year_to` (overlap with historical dates, not
publication dates), `include_undated`, `sort` (`relevance`, `date`, `title`), `limit`, `offset`.
Empty `q` = browse everything with filters.

### Result card (each item in `results`)
```text
id, title, resource_type, date_display, earliest_year, description, content_note,
record_source {id, name}, holding_institution {id, name} | null, holder_status,
digitized, access_mode, source_url, collection_method, verification_status, last_verified_at,
entities {person|place|community|subject: [{id, name, roles}]},
also_available_from [{record_id, institution, source_url}],   # same resource, other institution
why {summary, fields, entities, related_terms},               # only when q is given
score
```
Show `source_url` as the "View at source" button. Show `content_note` before the
description when present. `also_available_from` is the "one resource, several doors" link.

## How the data is handled

- **One row per institution's description.** The Book of Negroes is described by Nova
  Scotia Archives and LAC, so it has two records (`SRC-001-nsa`, `SRC-001-lac`) joined by
  a curated `describes_same_resource` relation. They are never merged.
- **Record source vs holder.** `record_source` supplied the description; `holding_institution`
  holds the original. `holder_status` says how sure we are; nothing is marked `confirmed`
  without evidence.
- **Empty means unknown.** Values derived by rule are marked: date ranges worked out from
  labels like "mid-1960s" have `origin = platform_generated`, and `change_notes` says
  `digitized` and `access_mode` were derived from the access text.
- **Provenance stays with the record.** `/records/{id}` returns `provenance`, including
  `last_verified_at` and `source_evidence` (what the checker looked at), for the provenance panel.
- **People are never merged on name alone.** A one-word name ("Hannah") gets an id tied to
  its record. Mary Ann Shadd and Adrienne Shadd are separate people.
- **Curator judgements live in one place** for team review: `HOLDER_OVERRIDES`,
  `CONTENT_NOTES` and `ROLE_OVERRIDES` in `app/ingest/verified_json.py`.
- **Terminology bridge** (`app/vocab.py`, draft for BCCNS review): current terms also find
  historical wording, e.g. "freedom seekers" finds a title that says "fugitive slave".

## Search, briefly

SQLite FTS5 with BM25 ranking. Title counts 10x, people/places/subjects 6x, description
3x. Prefix matching and English stemming are on. Query words are ANDed; a terminology
group is searched as an OR of its terms. Each result reports which fields, people or
related terms matched. "Connected records" share people, communities, subjects or places,
with people and communities weighted most.

## Adding a source

Write an adapter in `app/ingest/` with `load(conn, path) -> summary dict` that inserts
rows into the tables, then call it in `app/build.py` next to `verified_json.load`. Use
`collection_method = 'export'` and `verification_status = 'unverified'` for imported
records so they show as the imported tier.

Next adapters planned:
- LAC Collection Search export (waiting on a real export file to map its fields)
- CSV template for community organizations

## Layout

```text
backend/
  schema.sql              tables (matches database_tables_and_columns.md)
  app/main.py             FastAPI endpoints
  app/search.py           search, filters, facets, record/entity/institution queries
  app/vocab.py            terminology bridge (draft)
  app/build.py            builds the database from the sources
  app/ingest/             one adapter per source format
  tests/                  pytest suite (31 tests)
```
