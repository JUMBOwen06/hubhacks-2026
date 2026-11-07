"""HTTP API for the Black History Discovery Hub.

Run from the backend folder:
    uvicorn app.main:app --reload
Interactive docs: http://127.0.0.1:8000/docs
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from . import build, config, db, search, vocab


@asynccontextmanager
async def lifespan(app: FastAPI):
    if config.rebuild_on_start() or not config.db_path().exists():
        summary = build.build_database()
        print(f"Built {summary['db']}: {summary['records_indexed']} records, "
              f"search engine {summary['search_engine']}")
    yield


app = FastAPI(
    title="Black History Discovery Hub API",
    version="0.1.0",
    description=(
        "Proof of concept for the Black Cultural Centre for Nova Scotia (RBC HubHacks 2026). "
        "The hub indexes descriptions of records held by other institutions and links to the "
        "authoritative source; it does not copy collections."
    ),
    lifespan=lifespan,
)
# Open for local frontend development. Restrict origins before any public deployment.
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"])


def get_conn():
    conn = db.connect(config.db_path())
    try:
        yield conn
    finally:
        conn.close()


@app.get("/", tags=["meta"])
def root():
    return {
        "name": app.title,
        "docs": "/docs",
        "endpoints": ["/search", "/records/{id}", "/entities", "/entities/{id}", "/institutions",
                      "/institutions/{id}", "/suggest", "/stats", "/vocab", "/health"],
    }


@app.get("/health", tags=["meta"])
def health(conn=Depends(get_conn)):
    return {"status": "ok", "records": conn.execute("SELECT COUNT(*) FROM record").fetchone()[0],
            "search_engine": db.search_engine(conn)}


@app.get("/search", tags=["search"])
def search_records(
    q: str = Query("", description="Free text: people, places, communities, subjects, titles"),
    institution: list[str] | None = Query(None, description="Institution id (record source or holder)"),
    resource_type: list[str] | None = Query(None),
    digitized: list[str] | None = Query(None),
    access_mode: list[str] | None = Query(None),
    collection_method: list[str] | None = Query(None, description="manual = verified tier, export = imported"),
    entity: list[str] | None = Query(None, description="Entity id(s); records must link to all"),
    year_from: int | None = Query(None, description="Historical date overlaps this year or later"),
    year_to: int | None = Query(None),
    include_undated: bool = Query(False, description="Keep undated records when filtering by year"),
    sort: Literal["relevance", "date", "title"] = "relevance",
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    conn=Depends(get_conn),
):
    filters = search.Filters(
        institution=institution or [], resource_type=resource_type or [], digitized=digitized or [],
        access_mode=access_mode or [], collection_method=collection_method or [], entity=entity or [],
        year_from=year_from, year_to=year_to, include_undated=include_undated,
    )
    return search.search(conn, q, filters, sort=sort, limit=limit, offset=offset)


@app.get("/records/{record_id}", tags=["records"])
def record_detail(record_id: str, conn=Depends(get_conn)):
    rec = search.get_record(conn, record_id)
    if not rec:
        raise HTTPException(404, f"No record {record_id!r}")
    return rec


@app.get("/entities", tags=["connections"])
def entities(
    type: Literal["person", "place", "community", "subject", "event"] | None = None,
    q: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    conn=Depends(get_conn),
):
    return search.list_entities(conn, type, q, limit)


@app.get("/entities/{entity_id}", tags=["connections"])
def entity_detail(entity_id: str, conn=Depends(get_conn)):
    ent = search.get_entity(conn, entity_id)
    if not ent:
        raise HTTPException(404, f"No entity {entity_id!r}")
    return ent


@app.get("/institutions", tags=["institutions"])
def institutions(conn=Depends(get_conn)):
    return search.list_institutions(conn)


@app.get("/institutions/{institution_id}", tags=["institutions"])
def institution_detail(institution_id: str, conn=Depends(get_conn)):
    inst = search.get_institution(conn, institution_id)
    if not inst:
        raise HTTPException(404, f"No institution {institution_id!r}")
    return inst


@app.get("/suggest", tags=["search"])
def suggest(q: str = "", limit: int = Query(8, ge=1, le=20), conn=Depends(get_conn)):
    return search.suggest(conn, q, limit)


@app.get("/stats", tags=["meta"])
def stats(conn=Depends(get_conn)):
    return search.stats(conn)


@app.get("/vocab", tags=["meta"])
def terminology():
    """The terminology bridge (draft for BCCNS review), shown for transparency."""
    return {"status": "draft for BCCNS and community review", "groups": vocab.GROUPS}
