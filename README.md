# Black History Hub

A discovery platform for African Canadian history records held across Canadian institutions, built as a proof of concept for the [Black Cultural Centre for Nova Scotia (BCCNS)](https://bccns.com/) at HubHacks 2026 by team **Fivefold**.

Records of Black history in Canada are spread across museums, archives, libraries, universities, governments and community organizations, each with its own catalogue. Black History Hub lets people search descriptions of those records in one place, then sends them to the institution that holds or describes the original. It does **not** host, copy or replace any collection.

> **Status:** Working prototype. Search, filtering, record pages, the institutions page, the about page and an anonymous Impact page run on a manually verified dataset of 43 records from 22 institutions. Search runs on a SQLite + FastAPI backend, with a basic in-browser search as an offline fallback. This is a student prototype, not an official BCCNS service.

## Contents

- [Features](#features)
- [Getting started](#getting-started)
- [Running the tests](#running-the-tests)
- [Project structure](#project-structure)
- [Data](#data)
- [Technology](#technology)
- [Data, attribution and accuracy principles](#data-attribution-and-accuracy-principles)
- [Roadmap](#roadmap)
- [Team and acknowledgements](#team-and-acknowledgements)

## Features

- **Unified search** across titles, descriptions, people, places, communities, subjects and institutions. Matching ignores capitals and accents, understands related and historical terms, suggests spellings when nothing matches, and says why each result matched.
- **Filters** by resource type (applied instantly) and by institution. Every search and filter is in the URL, so results can be shared as a link.
- **Record pages** showing the description, dates, people, places and subjects, where to find the original, how to access it, rights and reuse terms, related records and provenance.
- **Holder vs. source:** every record says which institution wrote the description and which holds the original. These are often different, and the platform never implies otherwise.
- **Provenance on every record:** verification status, when the details and link were last checked, who added it and how. Fields we can't verify are left empty rather than guessed.
- **Content notes** on records whose titles use historical terminology now considered offensive; titles are kept as the source wrote them.
- **Institutions page** listing all 22 partner institutions, with links to their websites, catalogues and rights policies, and to their records here.
- **Impact page** (`/app/impact.html`): anonymous daily counts of visits, searches, searches with no results and clicks through to institutions. No IP addresses, cookies or locations are stored.
- **Accessible and responsive:** skip link, keyboard-friendly menu, descriptive alt text, a pausable carousel that respects reduced-motion settings, and layouts tested on phone and desktop.

## Getting started

### Prerequisites

- **Python 3.10 or newer.** Check with `python3 --version` (macOS/Linux) or `py --version` (Windows). Get it from [python.org](https://www.python.org/downloads/).
- On Debian/Ubuntu Linux you may also need the venv module: `sudo apt install python3-venv`.
- No Node.js or build step is needed; the frontend is plain HTML, CSS and JavaScript.

The backend (FastAPI + SQLite) builds the search database from `data/seed/` every time it starts and serves the website at `/app/`.

### Quick start

| System | How to start | How to stop |
| --- | --- | --- |
| **Windows** | Double-click `start.bat` in the repository root. | Close the window. |
| **macOS / Linux** | In a terminal, from the repository root: `./start.sh` (or `bash start.sh`). | Press **Ctrl+C**. |

The first run creates `backend/.venv` and installs the requirements, which takes a minute. The browser opens at <http://127.0.0.1:8000/app/> once the server is ready. If port 8000 is already in use, the launcher picks the next free port (8001, 8002, …) and prints the address it used. To prefer another port, run `PORT=8001 ./start.sh` on macOS/Linux or `set PORT=8001` before `start.bat` in Command Prompt.

If an earlier setup was interrupted, just run the launcher again: it checks that the requirements are installed and finishes installing them if not.

If macOS says the script isn't executable, run `chmod +x start.sh` once.

### Manual setup

From the repository root:

**macOS / Linux**

```bash
python3 -m venv backend/.venv
source backend/.venv/bin/activate
pip install -r backend/requirements.txt
uvicorn app.main:app --app-dir backend --port 8000
```

**Windows (PowerShell)**

```powershell
py -m venv backend\.venv
backend\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
uvicorn app.main:app --app-dir backend --port 8000
```

Then open <http://127.0.0.1:8000/app/>. Interactive API docs are at <http://127.0.0.1:8000/docs>; see [`backend/README.md`](backend/README.md) for every endpoint and setting.

### Troubleshooting

- **"Offline mode" on the results page:** the pages couldn't reach the API (for example the repository was opened with a plain static server or VS Code Live Server), so search, record and institution pages fall back to a basic in-browser search of the bundled JSON. That mode has no related-term matching, spelling suggestions, "why matched" lines or connected records, so start the backend for demos.
- **A page looks out of date** after you change files: hard-refresh with **Ctrl+Shift+R** (**Cmd+Shift+R** on macOS).
- **"database is locked"** when the repository is in OneDrive or another synced folder: point the database at a local folder, for example `HUBHACKS_DB=/tmp/hubhacks.db ./start.sh`, or `$env:HUBHACKS_DB="$env:TEMP\hubhacks.db"` in PowerShell before `uvicorn`.
- **Port 8000 already in use:** `start.bat` and `start.sh` move to the next free port automatically and print the address; open that one. With the manual setup, pass another port, for example `--port 8001`.
- **"No module named uvicorn"** or another missing module: the requirements didn't finish installing (often a dropped connection on the first run). Run `start.bat` or `./start.sh` again and it reinstalls them, or run `backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt` (Windows) / `backend/.venv/bin/python -m pip install -r backend/requirements.txt` (macOS/Linux).
- **The launcher says the virtual environment is broken** (for example after Python was reinstalled or upgraded): it deletes and recreates `backend/.venv` itself. If that fails, delete the `backend/.venv` folder and run the launcher again.

## Running the tests

With the virtual environment active, from the repository root:

```bash
pip install -r backend/requirements-dev.txt
cd backend
pytest
```

All 61 tests should pass.

## Project structure

```
start.bat             One-click start on Windows
start.sh              One-click start on macOS and Linux
frontend/
  index.html          Home: search, image carousel, featured records
  results.html        Search results (rendered by js/results.js)
  record.html         Single record page, e.g. record.html?id=SRC-001a (rendered by js/record.js)
  institutions.html   Partner institutions (rendered by js/institutions.js)
  about.html          The problem, how it works, principles, coverage
  impact.html         Anonymous usage counts (not linked in the menu)
  css/styles.css      All styles
  js/script.js        Shared page behaviour: mobile menu, carousel, search form
  js/data.js          Talks to the API, with the offline fallback; shared labels and helpers
  js/results.js       Search, filtering and result cards
  js/record.js        Record page rendering
  js/institutions.js  Institution cards and sorting
  js/track.js         Anonymous usage events for the Impact page
  js/impact.js        Impact page rendering
  Resources/          Carousel images
backend/
  app/main.py         FastAPI app: API endpoints, serves frontend/ at /app/ and data/ at /data/
  app/search.py       Search, ranking, filters and "why matched" explanations
  app/build.py        Builds the SQLite database from the dataset
  app/impact.py       Anonymous usage counts
  launch.py           Used by start.bat/start.sh: picks a free port, opens the browser when the server is ready
  app/ingest/         Dataset importers
  schema.sql          Database schema
  tests/              Test suite (pytest)
data/
  seed/black_history_dataset_v2_2026-11-06.json   The dataset (source of truth)
  exports/csv/        The same tables as CSV
  load_dataset.py     Standalone script that loads the dataset into a SQLite file
docs/
  database_tables_and_columns.md   Every table and column explained
```

### URL parameters

| Page | Parameter | Example |
| --- | --- | --- |
| `results.html` | `q`: search text | `results.html?q=africville` |
| | `type`: comma-separated resource types | `results.html?type=book,map` |
| | `institution`: institution ID | `results.html?institution=inst_nsa` |
| `record.html` | `id`: record ID | `record.html?id=BOOK-002` |

## Data

The dataset holds **metadata and links only**: short curator-written descriptions plus the authoritative URL at each institution. Tables (column details in [`docs/database_tables_and_columns.md`](docs/database_tables_and_columns.md)):

| Table | Rows | Contents |
| --- | --- | --- |
| `record` | 43 | One institution's description of one resource, with access, rights and provenance fields |
| `institution` | 22 | Archives, libraries, museums, publishers and government sources |
| `entity` | 197 | People, places, communities, organizations, events and subjects |
| `record_entity` | 390 | Links records to entities, with a role (subject, author, location, …) |
| `record_date` | 78 | Dates by kind (published, document date, event, lifetime, …) |
| `record_relation` | 20 | Evidence-based links between related records |

35 of the 43 records are verified; 8 are marked as needing review. Just over half relate to Nova Scotia; others cover Quebec, Ontario, New Brunswick, Manitoba, Saskatchewan, Alberta and British Columbia.

To add or correct records, edit the JSON in `data/seed/` and restart the server; the database is rebuilt on every start.

## Technology

- **Frontend:** plain HTML, CSS and JavaScript with no build step and no dependencies.
- **Backend:** Python, FastAPI and SQLite (with FTS5 full-text search when available), tested with pytest.

## Data, attribution and accuracy principles

- Store descriptions and links, not copies of images or documents. Public availability does not grant permission to copy.
- Always link back to the authoritative institutional record.
- Keep the holding institution and the record source separate.
- Keep separate records separate, even when they relate to the same person or event. Connections must be evidence-based.
- Track where information came from, and when it was added and last verified.
- Be transparent about what is and isn't covered.
- If information can't be verified, don't present it as fact. Leave the field empty instead. Any future search assistant must only cite real records in the hub.

## Roadmap

- **Dashboard:** extend the Impact page with dataset health (records needing review, stale links, unconfirmed holders, coverage gaps).
- **Easier intake:** a template for new records that matches people, places and subjects to existing entries automatically, plus metadata harvesting from institutions that publish structured data.
- **Better search:** more alternate and historical names (for example, Port Roseway = Shelburne) and date-range filters in the interface.
- **Coverage:** add records from Prince Edward Island, Newfoundland and Labrador, and the territories.
- **Hosting:** deploy the app so people can use it without running it locally.

## Team and acknowledgements

Built by team **Fivefold** at HubHacks 2026 for the Black Cultural Centre for Nova Scotia. Record descriptions link to, and credit, the institutions that hold and describe the originals; their own rights and reuse terms apply.

No licence has been chosen for this repository yet, so all rights are reserved by the authors until one is added.
