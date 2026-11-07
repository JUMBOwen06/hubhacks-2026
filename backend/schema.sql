-- Black History Discovery Platform (HubHacks 2026) - SQLite schema
-- Matches docs: database_tables_and_columns.md
-- Dates are stored as text in YYYY-MM-DD form. Empty values mean unknown, never guessed.

PRAGMA foreign_keys = ON;

-- 1. institution -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS institution (
    id                TEXT PRIMARY KEY,                -- e.g. inst_lac
    name              TEXT NOT NULL,
    type              TEXT NOT NULL CHECK (type IN
                        ('archive','library','museum','university','government',
                         'publisher','community','other')),
    website_url       TEXT,
    catalogue_url     TEXT,
    location          TEXT,
    description       TEXT,
    rights_policy_url TEXT
);

-- 2. record: one row = one institution's description of something ------------
CREATE TABLE IF NOT EXISTS record (
    id                     TEXT PRIMARY KEY,
    title_original         TEXT NOT NULL,              -- exactly as the source wrote it
    description            TEXT,
    description_origin     TEXT CHECK (description_origin IN
                             ('source_transcribed','source_paraphrased','curator_written')),
    resource_type          TEXT NOT NULL CHECK (resource_type IN
                             ('archival_document','correspondence','register','map',
                              'photograph','person_profile','research_guide',
                              'journal_article','book','other')),
    language               TEXT,
    date_display           TEXT,                       -- date as the source wrote it
    content_note           TEXT,                       -- cautions, e.g. discriminatory historical language
    container_title        TEXT,                       -- journal or book series
    notes                  TEXT,
    record_source_id       TEXT NOT NULL REFERENCES institution(id),  -- who supplies the description
    holding_institution_id TEXT REFERENCES institution(id),           -- who holds the original
    holder_status          TEXT NOT NULL DEFAULT 'unknown' CHECK (holder_status IN
                             ('confirmed','unconfirmed','unknown','not_applicable')),
    holder_note            TEXT,
    source_url             TEXT NOT NULL,              -- authoritative record page
    source_reference       TEXT,                       -- call number or catalogue ID
    digital_url            TEXT,
    digitized              TEXT DEFAULT 'unknown' CHECK (digitized IN
                             ('yes','partial','no','unknown','not_applicable')),
    access_mode            TEXT DEFAULT 'unknown' CHECK (access_mode IN
                             ('online','in_person','on_request','mixed','unknown')),
    access_instructions    TEXT,
    access_restrictions    TEXT,
    rights_statement       TEXT,
    rights_url             TEXT,
    reuse_scope            TEXT NOT NULL DEFAULT 'metadata_and_link_only' CHECK (reuse_scope IN
                             ('metadata_and_link_only','description_ok','images_ok')),
    collection_method      TEXT NOT NULL CHECK (collection_method IN
                             ('manual','export','api','scrape')),
    imported_at            TEXT NOT NULL,
    added_by               TEXT,
    last_verified_at       TEXT,
    source_evidence        TEXT,                       -- what the checker looked at to verify this record
    verification_status   TEXT NOT NULL DEFAULT 'unverified' CHECK (verification_status IN
                             ('unverified','verified','needs_review','link_broken')),
    link_last_checked      TEXT,
    change_notes           TEXT
);
CREATE INDEX IF NOT EXISTS idx_record_source  ON record(record_source_id);
CREATE INDEX IF NOT EXISTS idx_record_holding ON record(holding_institution_id);
CREATE INDEX IF NOT EXISTS idx_record_type    ON record(resource_type);

-- 3. record_date --------------------------------------------------------------
CREATE TABLE IF NOT EXISTS record_date (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id   TEXT NOT NULL REFERENCES record(id) ON DELETE CASCADE,
    kind        TEXT NOT NULL,                         -- life, event, document, period_discussed, publication...
    label       TEXT NOT NULL,                         -- as the source wrote it
    start_year  INTEGER,                               -- empty if unknown
    end_year    INTEGER,
    approximate INTEGER NOT NULL DEFAULT 0 CHECK (approximate IN (0,1)),
    origin      TEXT NOT NULL DEFAULT 'source_stated'
);
CREATE INDEX IF NOT EXISTS idx_date_record ON record_date(record_id);
CREATE INDEX IF NOT EXISTS idx_date_years  ON record_date(start_year, end_year);

-- 4. entity: people, places, communities, subjects and events ------------------
CREATE TABLE IF NOT EXISTS entity (
    id             TEXT PRIMARY KEY,
    entity_type    TEXT NOT NULL CHECK (entity_type IN
                     ('person','place','community','subject','event')),
    name_preferred TEXT NOT NULL,
    disambiguator  TEXT,                               -- tells apart people with the same name
    description    TEXT,
    external_id    TEXT                                -- Wikidata or GeoNames, optional
);

-- 5. record_entity -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS record_entity (
    record_id       TEXT NOT NULL REFERENCES record(id) ON DELETE CASCADE,
    entity_id       TEXT NOT NULL REFERENCES entity(id),
    role            TEXT NOT NULL CHECK (role IN
                      ('subject','author','contributor','creator','recipient','location','mentioned')),
    name_as_written TEXT,                              -- the source's own string
    origin          TEXT NOT NULL CHECK (origin IN
                      ('source_stated','curator_added','platform_generated')),
    link_basis      TEXT,                              -- why this link was made
    PRIMARY KEY (record_id, entity_id, role)
);
CREATE INDEX IF NOT EXISTS idx_re_entity ON record_entity(entity_id);

-- 6. record_relation: curated links between records ---------------------------
-- Related records that simply share an entity are found by query, not stored here.
CREATE TABLE IF NOT EXISTS record_relation (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    record_a_id   TEXT NOT NULL REFERENCES record(id) ON DELETE CASCADE,
    record_b_id   TEXT NOT NULL REFERENCES record(id) ON DELETE CASCADE,
    relation_type TEXT NOT NULL CHECK (relation_type IN
                    ('describes_same_resource','part_of','same_series','related_context')),
    basis         TEXT NOT NULL CHECK (basis IN
                    ('source_states','curator_judgement','auto_suggested')),
    evidence_note TEXT,
    evidence_url  TEXT,
    status        TEXT NOT NULL DEFAULT 'proposed' CHECK (status IN
                    ('proposed','confirmed','rejected')),
    created_by    TEXT,
    created_at    TEXT,
    CHECK (record_a_id <> record_b_id)
);

-- 7. record_search: full-text index, filled from the other tables -------------
-- Not a source of truth. If this Python's SQLite lacks FTS5, app/db.py swaps the
-- block below for a plain table and search falls back to simple text matching.
-- fts:begin
CREATE VIRTUAL TABLE IF NOT EXISTS record_search USING fts5(
    record_id UNINDEXED,
    title,
    description,
    entity_names,
    tokenize = 'porter unicode61 remove_diacritics 2'
);
-- fts:end

-- Not in use yet (for later) ----------------------------------------------------
-- CREATE TABLE entity_alias (
--     entity_id TEXT NOT NULL REFERENCES entity(id),
--     alias     TEXT NOT NULL,
--     note      TEXT,
--     PRIMARY KEY (entity_id, alias)
-- );
-- CREATE TABLE enrichment (
--     id                    INTEGER PRIMARY KEY AUTOINCREMENT,
--     record_id             TEXT NOT NULL REFERENCES record(id),
--     kind                  TEXT NOT NULL,
--     content               TEXT NOT NULL,
--     origin                TEXT NOT NULL,
--     model                 TEXT,
--     supporting_record_ids TEXT,
--     status                TEXT NOT NULL DEFAULT 'proposed',
--     created_at            TEXT
-- );
