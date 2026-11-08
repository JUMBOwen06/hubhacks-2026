# Black History Hub

A discovery platform for African Canadian history records held across Canadian institutions, built as a proof of concept for the **Black Cultural Centre for Nova Scotia (BCCNS)** at HubHacks 2026 by team **Fivefold**.

Records of Black history in Canada are spread across museums, archives, libraries, universities, governments and community organizations, each with its own catalogue. Black History Hub lets people search descriptions of those records in one place, then sends them to the institution that holds or describes the original. It does **not** host, copy or replace any collection.

> **Status:** Working prototype. Search, filtering, record pages, the institutions page and the about page run on a manually verified dataset of 41 records from 21 institutions. Search runs on a SQLite + FastAPI backend, with a basic in-browser search as an offline fallback.

## Features

- **Unified search** across titles, descriptions, people, places, communities, subjects and institutions. Matching ignores capitals and accents, and title matches rank first.
- **Filters** by resource type (applied instantly) and by institution. Every search and filter is in the URL, so results can be shared as a link.
- **Record pages** showing the description, dates, people, places and subjects, where to find the original, how to access it, rights and reuse terms, related records and provenance.
- **Holder vs. source:** every record says which institution wrote the description and which holds the original. These are often different, and the platform never implies otherwise.
- **Provenance on every record:** verification status, when the details and link were last checked, who added it and how.
- **Content notes** on records whose titles use historical terminology now considered offensive; titles are kept as the source wrote them.
- **Institutions page** listing all 21 partner institutions, with links to their websites, catalogues and rights policies, and to their records here.
- **Accessible and responsive:** skip link, keyboard-friendly menu, descriptive alt text, a pausable carousel that respects reduced-motion settings, and layouts tested on phone and desktop.

## Running it locally

The backend (FastAPI + SQLite) builds the search database from `data/seed/` and serves the website at `/app/`. Needs Python 3.10+.

**Windows:** double-click `start.bat` in the repository root. The first run creates `backend\.venv` and installs the requirements; then it opens <http://127.0.0.1:8000/app/>. Close the window to stop the server.

**Any system**, from the repository root:

```bash
python -m venv backend/.venv
# Windows: backend\.venv\Scripts\activate    macOS/Linux: source backend/.venv/bin/activate
pip install -r backend/requirements.txt
uvicorn app.main:app --app-dir backend --port 8000
```

Then open <http://127.0.0.1:8000/app/>. API docs are at <http://127.0.0.1:8000/docs>; see `backend/README.md` for tests and settings.

**Offline fallback:** if the pages can't reach the API (for example when the repository root is served by a plain static server or VS Code Live Server), search, record and institution pages fall back to a basic in-browser search of the bundled JSON and show "Offline mode". That mode has no related-term matching, spelling suggestions, "why matched" lines or connected records, so use the backend for demos.

If a page looks out of date after you change files, hard-refresh with **Ctrl+Shift+R**.

## Project structure

```
frontend/
  index.html          Home: search, image carousel, featured records
  results.html        Search results (rendered by js/results.js)
  record.html         Single record page, e.g. record.html?id=SRC-001a (rendered by js/record.js)
  institutions.html   Partner institutions
  about.html          The problem, how it works, principles, coverage
  css/styles.css      All styles
  js/script.js        Shared page behaviour: mobile menu, carousel, search form
  js/data.js          Loads the dataset; shared labels and helpers
  js/results.js       Search, filtering and result cards
  js/record.js        Record page rendering
  Resources/          Carousel images
data/
  seed/black_history_dataset_v2_2026-11-06.json   The dataset (source of truth)
  exports/csv/        The same tables as CSV
  load_dataset.py     Loads the dataset into SQLite (backend work in progress)
```

### URL parameters

| Page | Parameter | Example |
| --- | --- | --- |
| `results.html` | `q`: search text | `results.html?q=africville` |
| | `type`: comma-separated resource types | `results.html?type=book,map` |
| | `institution`: institution ID | `results.html?institution=inst_nsa` |
| `record.html` | `id`: record ID | `record.html?id=BOOK-002` |

## Data

The dataset holds **metadata and links only**: short curator-written descriptions plus the authoritative URL at each institution. Tables:

| Table | Rows | Contents |
| --- | --- | --- |
| `record` | 41 | One institution's description of one resource, with access, rights and provenance fields |
| `institution` | 21 | Archives, libraries, museums, publishers and government sources |
| `entity` | 191 | People, places, communities, organizations, events and subjects |
| `record_entity` | 369 | Links records to entities, with a role (subject, author, location, …) |
| `record_date` | 74 | Dates by kind (published, document date, event, lifetime, …) |
| `record_relation` | 20 | Evidence-based links between related records |

35 of the 41 records are verified; 6 are marked as needing review. Just over half relate to Nova Scotia; others cover Quebec, Ontario, New Brunswick, Manitoba, Saskatchewan, Alberta and British Columbia.

## Technology

- **Frontend:** plain HTML, CSS and JavaScript with no build step and no dependencies.
- **Backend (in progress):** SQLite and FastAPI.

## Data, attribution and accuracy principles

- Store descriptions and links, not copies of images or documents. Public availability does not grant permission to copy.
- Always link back to the authoritative institutional record.
- Keep the holding institution and the record source separate.
- Keep separate records separate, even when they relate to the same person or event. Connections must be evidence-based.
- Track where information came from, and when it was added and last verified.
- Be transparent about what is and isn't covered.
- If information can't be verified, don't present it as fact. Any future AI-assisted search must only cite real records in the hub.

## Roadmap

- **Backend:** serve search and records from FastAPI and SQLite.
- **Dashboard:** dataset health (records needing review, stale links, unconfirmed holders, coverage gaps) and usage (top searches, searches with no results, clicks through to institutions).
- **Easier intake:** a template for new records that matches people, places and subjects to existing entries automatically, plus metadata harvesting from institutions that publish structured data.
- **Better search:** alternate and historical names (for example, Port Roseway = Shelburne), typo tolerance and date-range filters.
- **Coverage:** add records from Prince Edward Island, Newfoundland and Labrador, and the territories.
