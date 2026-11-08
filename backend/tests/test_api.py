def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["records"] == 27


def test_search_endpoint(client):
    r = client.get("/search", params={"q": "Africville", "resource_type": ["journal_article"]})
    assert r.status_code == 200
    assert {x["id"] for x in r.json()["results"]} == {"JRN-007", "JRN-008"}


def test_record_endpoint(client):
    r = client.get("/records/SRC-001-nsa").json()
    assert r["holding_institution"]["id"] == "inst_tna_uk"
    assert r["relations"][0]["record"]["id"] == "SRC-001-lac"
    assert r["content_note"]
    assert client.get("/records/NOPE").status_code == 404


def test_record_provenance_shows_evidence(client):
    provenance = client.get("/records/JRN-011").json()["provenance"]
    assert provenance["source_evidence"] == "Official article landing page with author, abstract, DOI and citation details."
    assert provenance["last_verified_at"] == "2026-11-06"


def test_entities_and_institutions(client):
    people = client.get("/entities", params={"type": "person"}).json()
    assert any(p["name_preferred"] == "Viola Desmond" and p["record_count"] == 2 for p in people)
    assert client.get("/entities/person:viola-desmond").json()["record_count"] == 2
    insts = client.get("/institutions").json()
    assert {i["id"] for i in insts} >= {"inst_nsa", "inst_lac", "inst_parks"}
    assert client.get("/institutions/inst_nsa").json()["records_supplied"] == 4


def test_suggest_stats_vocab(client):
    assert client.get("/suggest", params={"q": "Afr"}).json()[0]["label"] == "Africville"
    assert client.get("/stats").json()["records"] == 27
    assert client.get("/vocab").json()["status"].startswith("draft")


def test_labels_endpoint(client):
    labels = client.get("/labels").json()
    assert labels["resource_type"]["journal_article"] == "Journal article"
    assert labels["collection_method"]["manual"] == "Entered by hand"
    assert "/labels" in client.get("/").json()["endpoints"]


def test_search_highlights_and_undated_filter(client):
    r = client.get("/search", params={"q": "Africville"}).json()
    assert all("<mark>" in x["highlight"]["title"] + (x["highlight"]["description"] or "")
               for x in r["results"])
    undated = client.get("/search", params={"undated_only": "true", "limit": 100}).json()
    assert undated["total"] == 7


def test_frontend_pages_and_their_data_file_are_served(client):
    # The pages at /app/ load the seed dataset as ../data/seed/..., i.e. /data/seed/...
    assert client.get("/app/results.html").status_code == 200
    r = client.get("/data/seed/black_history_dataset_v2_2026-11-06.json")
    assert r.status_code == 200 and len(r.json()["record"]) == 41
