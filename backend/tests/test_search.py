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


def test_interpreted_terms_are_what_the_user_typed(conn):
    assert search.search(conn, "Ontario")["interpreted"]["terms"] == ["ontario"]
    r = search.search(conn, "Escaped Slave Ontario")
    assert r["interpreted"]["terms"] == ["escaped slave", "ontario"]
    assert [g["searched"] for g in r["interpreted"]["related_terms"]] == ["escaped slave", "ontario"]
    assert search.search(conn, "the Black Loyalists")["interpreted"]["terms"] == ["black", "loyalists"]


def test_connected_records_label_a_shared_author_as_author(conn):
    rec = search.get_record(conn, "JRN-007")
    jrn8 = next(c for c in rec["connected"] if c["id"] == "JRN-008")
    shared = {s["name"]: s for s in jrn8["shared"]}
    loo = shared["Tina Loo"]
    assert (loo["link"], loo["label"], loo["roles_here"], loo["roles_there"]) == (
        "same_author", "Same author", ["author"], ["author"])
    assert shared["Africville"]["label"] == "Shares a subject"
    assert shared["Halifax"]["label"] == "Shares a place"
    # Africville 3 + displacement 1.5 + urban renewal 1.5 + two places at 1 + same author 1
    assert jrn8["score"] == 9.0
    assert jrn8["summary"] == ("Shares a subject: Africville, displacement, urban renewal; "
                               "Shares a place: Halifax, Nova Scotia; Same author: Tina Loo")


def test_connected_records_never_call_an_author_a_shared_subject(conn):
    made_by = search.MADE_BY_ROLES
    for (rid,) in conn.execute("SELECT id FROM record").fetchall():
        for other in search.connected_records(conn, rid, limit=100):
            for s in other["shared"]:
                here, there = set(s["roles_here"]), set(s["roles_there"])
                if s["link"] in ("shared_subject", "shared_place"):
                    assert here - made_by and there - made_by, (rid, other["id"], s)
                elif s["link"] == "same_author":
                    assert here & made_by and there & made_by, (rid, other["id"], s)


def test_appears_with_says_how_records_are_shared(conn):
    def by_name(entity_id):
        return {a["name"]: a for a in search.get_entity(conn, entity_id)["appears_with"]}

    loo = by_name("person:tina-loo")
    assert loo["Gordon Stephenson"]["relation"] == "named_in_work_by"
    assert loo["Gordon Stephenson"]["label"] == "Named in 1 record by Tina Loo"
    viola = by_name("person:viola-desmond")
    assert viola["Graham Reynolds"]["label"] == "Author of 1 record naming Viola Desmond"
    assert viola["Wanda Robson"]["label"] == "Contributor to 1 record naming Viola Desmond"
    assert (viola["civil rights"]["relation"], viola["civil rights"]["label"]) == (
        "named_together", "In 2 of the same records")
    assert by_name("person:graham-reynolds")["Wanda Robson"]["relation"] == "co_credited"
    # Lord Dalhousie wrote the 1816 letter and is also discussed in it, so he counts as named in it.
    dalhousie = by_name("person:earl-bathurst")["Lord Dalhousie"]
    assert (dalhousie["relation"], dalhousie["roles"]) == ("named_together", ["creator", "subject"])


def test_facets_carry_labels_roles_and_year_ranges(conn):
    f = search.search(conn, "Africville")["facets"]
    assert {x["value"]: x["label"] for x in f["resource_type"]} == {
        "journal_article": "Journal article", "book": "Book"}
    people = {x["label"]: x["roles"] for x in f["person"]}
    assert people["Tina Loo"] == ["author"] and people["Gordon Stephenson"] == ["subject"]
    decades = {x["value"]: (x["label"], x["year_from"], x["year_to"]) for x in f["decade"]}
    assert decades["1960s"] == ("1960s", 1960, 1969)
    assert decades["undated"] == ("Undated", None, None)


def test_entity_lists_show_roles(conn):
    people = {p["name_preferred"]: p["roles"] for p in search.list_entities(conn, "person")}
    assert people["Tina Loo"] == ["author"]
    assert people["Viola Desmond"] == ["subject"]
    assert people["Lord Dalhousie"] == ["creator", "subject"]


def test_each_synonym_counts_once(conn):
    # "freedom seekers" and "freedom seeker" are the same words to the index, so only
    # one is searched; the records found stay the same.
    pq = search.parse_query("freedom seekers")
    assert search.fts_match(conn, pq) == (
        '("freedom seekers" OR "self-emancipated" OR "fugitive slaves" OR "escaped slaves")')
    # "mary ann shadd cary" contains "mary ann shadd", so it can't add a match.
    assert search.fts_match(conn, search.parse_query("Mary Ann Shadd Cary")) == '("mary ann shadd")'
    r = search.search(conn, "freedom seekers")
    assert ids(r) == {"JRN-011", "BIO-005"}
    weights = f"0.0, {search.TITLE_W}, {search.DESC_W}, {search.ENT_W}"
    by_hand = dict(conn.execute(
        f"SELECT record_id, -bm25(record_search, {weights}) FROM record_search WHERE record_search MATCH "
        "'(\"freedom seeker\" OR \"self emancipated\" OR \"fugitive slave\" OR \"escaped slave\")'"))
    assert {x["id"]: x["score"] for x in r["results"]} == {k: round(v, 4) for k, v in by_hand.items()}


def test_highlights_mark_the_matched_words(conn):
    book = next(x for x in search.search(conn, "Africville")["results"] if x["id"] == "BOOK-002")
    assert book["highlight"]["title"] == "A Love Letter to <mark>Africville</mark>"
    assert "<mark>Africville</mark>" in book["highlight"]["description"]
    brown = next(x for x in search.search(conn, "escaped slave")["results"] if x["id"] == "JRN-011")
    assert brown["highlight"]["title"] == "The case of Isaac Brown: <mark>fugitive slave</mark>"
    # Tina Loo matches as an author only, so there is nothing to excerpt from the description.
    assert all(x["highlight"]["description"] is None for x in search.search(conn, "Tina Loo")["results"])
    assert "highlight" not in search.search(conn, "")["results"][0]


def test_highlight_html_is_escaped():
    o, c = search.HL_OPEN, search.HL_CLOSE
    assert search.highlight_title(f"Fish & <b>{o}Chips{c}</b>") == (
        "Fish &amp; &lt;b&gt;<mark>Chips</mark>&lt;/b&gt;")


def test_description_excerpt_is_a_window_around_the_first_match():
    o, c = search.HL_OPEN, search.HL_CLOSE
    words = [f"w{i}" for i in range(60)]
    description = " ".join(words)
    words[20] = f"{o}w20{c}"
    marked = " ".join(words) + " Acadiensis"  # the index adds the journal name after the description
    shown = [f"w{i}" for i in range(12, 42)]
    shown[8] = "<mark>w20</mark>"
    assert search.description_excerpt(marked, description) == "… " + " ".join(shown) + " …"
    # A match only in the journal name is not in the description.
    assert search.description_excerpt(f"Some text {o}Acadiensis{c}", "Some text") is None


def test_undated_only_filter_matches_the_undated_facet(conn):
    undated = next(d for d in search.search(conn, "")["facets"]["decade"] if d["value"] == "undated")
    assert undated["undated_only"] is True
    r = search.search(conn, "", Filters(undated_only=True), limit=100)
    assert r["total"] == undated["count"] == 7
    assert [d["value"] for d in r["facets"]["decade"]] == ["undated"]
    for x in r["results"]:
        dates = search.get_record(conn, x["id"])["dates"]
        assert not [d for d in dates if d["kind"] != "publication" and d["start_year"] is not None]


def test_connections_made_only_of_broad_places_are_hidden(conn):
    broad = search.broad_places(conn)
    assert broad == {"place:nova-scotia", "place:halifax"}
    assert [x["id"] for x in search.get_record(conn, "JRN-007")["connected"]] == ["JRN-008", "BOOK-002"]
    # A shared subject is no longer pushed out by records that share only Halifax.
    assert [x["id"] for x in search.get_record(conn, "BIO-001")["connected"]] == ["BOOK-001", "JRN-012"]
    # A specific place still connects two records on its own.
    jrn10 = search.get_record(conn, "JRN-010")["connected"]
    assert jrn10[0]["summary"] == "Shares a place: Ontario, Upper Canada"
    for (rid,) in conn.execute("SELECT id FROM record").fetchall():
        for other in search.connected_records(conn, rid, limit=100):
            assert not all(s["link"] == "shared_place" and s["id"] in broad for s in other["shared"])


def test_queries_of_only_filler_words_browse_everything(conn):
    for q in ("and or", "the", 'AND OR "(* ^'):
        r = search.search(conn, q)
        assert r["total"] == 27 and r["interpreted"]["terms"] == [], q
        assert "why" not in r["results"][0]
    assert search.search(conn, "and or")["interpreted"]["ignored"] == ["and", "or"]
    assert search.search(conn, "the Black Loyalists of Birchtown")["interpreted"]["ignored"] == ["the", "of"]


def test_pages_line_up(conn):
    for q, sort in (("", "title"), ("Black Loyalists", "relevance"), ("Nova Scotia", "date")):
        full = search.search(conn, q, sort=sort, limit=100)
        paged = []
        for offset in range(0, full["total"], 4):
            page = search.search(conn, q, sort=sort, limit=4, offset=offset)
            assert page["total"] == full["total"] and page["facets"] == full["facets"]
            paged += [x["id"] for x in page["results"]]
        assert paged == [x["id"] for x in full["results"]], (q, sort)
