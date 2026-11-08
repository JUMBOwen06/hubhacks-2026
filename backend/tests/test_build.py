"""The verified dataset loads into the schema without losing or inventing anything."""


def test_counts(built_db):
    src = built_db["sources"][0]
    assert src["records_in_file"] == 26
    assert src["record_rows"] == 27          # Book of Negroes: one row per access point
    assert src["relations"] == 1
    assert src["warnings"] == []
    assert built_db["institutions"] == 7      # 6 record sources + The National Archives (UK) as holder


def test_same_resource_kept_separate_and_linked(conn):
    rows = conn.execute("SELECT id, record_source_id FROM record WHERE id LIKE 'SRC-001%' ORDER BY id").fetchall()
    assert [tuple(r) for r in rows] == [("SRC-001-lac", "inst_lac"), ("SRC-001-nsa", "inst_nsa")]
    rel = conn.execute("SELECT relation_type, basis, status FROM record_relation").fetchone()
    assert tuple(rel) == ("describes_same_resource", "curator_judgement", "confirmed")


def test_single_name_person_not_merged(conn):
    e = conn.execute("SELECT id, disambiguator FROM entity WHERE name_preferred = 'Hannah'").fetchone()
    assert e["id"] == "person:hannah--src-002"
    assert e["disambiguator"]


def test_different_shadds_are_different_people(conn):
    ids = {r[0] for r in conn.execute("SELECT id FROM entity WHERE name_preferred LIKE '%Shadd%'")}
    assert ids == {"person:mary-ann-shadd", "person:adrienne-shadd"}


def test_roles(conn):
    roles = {(r[0], r[1]) for r in conn.execute(
        "SELECT entity_id, role FROM record_entity WHERE record_id = 'SRC-004'")}
    assert ("person:lord-dalhousie", "creator") in roles
    assert ("person:earl-bathurst", "recipient") in roles
    assert ("person:tina-loo", "author") in {(r[0], r[1]) for r in conn.execute(
        "SELECT entity_id, role FROM record_entity WHERE record_id = 'JRN-007'")}


def test_derived_dates_are_marked(conn):
    d = conn.execute("SELECT start_year, end_year, approximate, origin FROM record_date "
                     "WHERE record_id = 'JRN-007' AND kind <> 'publication'").fetchone()
    assert tuple(d) == (1960, 1969, 1, "platform_generated")


def test_source_evidence_kept(conn):
    # Every verified row keeps the research team's own wording, including both Book of Negroes rows.
    assert conn.execute("SELECT COUNT(*) FROM record WHERE source_evidence IS NULL").fetchone()[0] == 0
    evidence = dict(conn.execute("SELECT id, source_evidence FROM record").fetchall())
    assert evidence["BOOK-001"] == "Publisher catalogue listing only; book not read or mined."
    assert evidence["SRC-001-nsa"] == evidence["SRC-001-lac"]


def test_no_unknown_values_invented(conn):
    # Journals and books never get a holding institution, and nothing is marked confirmed.
    assert conn.execute("SELECT COUNT(*) FROM record WHERE holder_status = 'confirmed'").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM record WHERE resource_type IN ('journal_article','book') "
                        "AND holding_institution_id IS NOT NULL").fetchone()[0] == 0
