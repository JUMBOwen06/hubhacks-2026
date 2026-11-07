"""Owen's v2 dataset (data/seed, table-shaped) loads as it is and the API works on it."""
import pytest

from app import build, config, db, search


@pytest.fixture(scope="module")
def v2(tmp_path_factory):
    db_file = tmp_path_factory.mktemp("v2") / "v2.db"
    summary = build.build_database(db_file=db_file, dataset=config._DEFAULT_DATASET)
    conn = db.connect(db_file)
    yield summary, conn
    conn.close()


def test_loads_every_row_without_warnings(v2):
    summary, _ = v2
    src = summary["sources"][0]
    assert src["format"] == "tables" and src["warnings"] == []
    assert (src["record_rows"], summary["institutions"], summary["entities"]) == (41, 21, 191)


def test_same_resource_kept_separate_and_linked(v2):
    _, conn = v2
    rec = search.get_record(conn, "SRC-001a")
    assert [x["record_id"] for x in rec["also_available_from"]] == ["SRC-001b"]


def test_organizations_are_browsable_and_faceted(v2):
    _, conn = v2
    orgs = search.list_entities(conn, "organization", None, 100)
    assert any(o["name_preferred"] == "African Baptist Association of Nova Scotia" for o in orgs)
    assert "organization" in search.search(conn, "baptist")["facets"]


def test_search_and_connections(v2):
    _, conn = v2
    assert search.search(conn, "africville")["total"] >= 4
    connected = search.get_record(conn, "SRC-019")["connected"]
    assert connected and all(c["summary"] for c in connected)
