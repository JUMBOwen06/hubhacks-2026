"""If this Python's SQLite has no FTS5 (possible on some Windows installs), search still works."""
import tempfile
from pathlib import Path

import pytest

from app import build, db, search


@pytest.fixture(scope="module")
def like_conn():
    original = db.fts5_available
    db.fts5_available = lambda: False
    try:
        path = Path(tempfile.mkdtemp(prefix="hubhacks-like-")) / "like.db"
        summary = build.build_database(db_file=path)
    finally:
        db.fts5_available = original
    assert summary["search_engine"] == "like"
    c = db.connect(path)
    yield c
    c.close()


@pytest.mark.parametrize("q, expected", [
    ("Africville", {"JRN-007", "JRN-008", "BOOK-002"}),
    ("Tina Loo", {"JRN-007", "JRN-008"}),
    ("self-emancipated", {"JRN-011", "BIO-005"}),
    ("Mary Ann Shadd Cary", {"BIO-003"}),
])
def test_like_engine_matches_fts_results(like_conn, q, expected):
    r = search.search(like_conn, q)
    assert r["engine"] == "like"
    assert {x["id"] for x in r["results"]} == expected


def test_like_engine_highlights_and_skips_filler(like_conn):
    book = next(x for x in search.search(like_conn, "Africville")["results"] if x["id"] == "BOOK-002")
    assert book["highlight"]["title"] == "A Love Letter to <mark>Africville</mark>"
    assert "<mark>Africville</mark>" in book["highlight"]["description"]
    assert search.search(like_conn, "and or")["total"] == 27
