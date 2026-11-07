from app import search
from app.search import Filters


def ids(result):
    return {r["id"] for r in result["results"]}


def test_community_search(conn):
    assert ids(search.search(conn, "Africville")) == {"JRN-007", "JRN-008", "BOOK-002"}


def test_person_search_covers_authors(conn):
    r = search.search(conn, "Tina Loo")
    assert ids(r) == {"JRN-007", "JRN-008"}
    assert all("author" in x["why"]["summary"] for x in r["results"])


def test_terminology_bridge(conn):
    r = search.search(conn, "self-emancipated")
    assert ids(r) == {"JRN-011", "BIO-005"}
    jrn = next(x for x in r["results"] if x["id"] == "JRN-011")
    assert "fugitive slave" in jrn["why"]["related_terms"][0]["matched"]


def test_alias_does_not_merge_different_people(conn):
    assert ids(search.search(conn, "Mary Ann Shadd Cary")) == {"BIO-003"}


def test_historical_place_names(conn):
    assert {"JRN-010", "JRN-011", "BIO-003"} <= ids(search.search(conn, "Upper Canada", limit=50))


def test_year_filter_uses_historical_dates(conn):
    r = search.search(conn, "", Filters(year_from=1780, year_to=1790), limit=50)
    assert ids(r) == {"SRC-001-nsa", "SRC-001-lac", "SRC-002", "SRC-005", "SRC-006", "JRN-002"}


def test_filters_combine(conn):
    r = search.search(conn, "Black Loyalists", Filters(institution=["inst_parks"]))
    assert ids(r) == {"SRC-005", "SRC-006"}


def test_one_resource_many_doors(conn):
    r = search.search(conn, "book of negroes")
    nsa = next(x for x in r["results"] if x["id"] == "SRC-001-nsa")
    assert nsa["also_available_from"][0]["record_id"] == "SRC-001-lac"


def test_no_results_is_honest_and_suggests(conn):
    r = search.search(conn, "Viola Desmund")
    assert r["total"] == 0
    assert "does not mean the material doesn't exist" in r["message"]
    assert any("desmond" in s.lower() for s in r["suggestions"])


def test_weird_characters_do_not_crash(conn):
    search.search(conn, 'AND OR "(* ^')


def test_connected_records(conn):
    rec = search.get_record(conn, "BIO-001")
    assert rec["connected"][0]["id"] == "BOOK-001"
    assert any(s["name"] == "Viola Desmond" for s in rec["connected"][0]["shared"])


def test_entity_page(conn):
    e = search.get_entity(conn, "community:africville")
    assert e["record_count"] == 3
    assert e["institution_count"] == 2


def test_facets(conn):
    f = search.search(conn, "")["facets"]
    assert sum(x["count"] for x in f["resource_type"]) == 27
    assert any(d["value"] == "undated" for d in f["decade"])
