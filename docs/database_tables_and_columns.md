# Database Tables and Columns

Black History Discovery Platform (HubHacks 2026). Matches `schema.sql` (SQLite).

**PK** = primary key. **FK** = foreign key (points to another table). **Req** = value cannot be empty. Dates are stored as text in `YYYY-MM-DD` form. Empty values mean unknown, never guessed.

## 1. `institution`

| Column | Type | Req | Notes |
|---|---|---|---|
| `id` | text | PK | e.g. `inst_lac` |
| `name` | text | Req | |
| `type` | text | Req | archive, library, museum, university, government, publisher, community, other |
| `website_url` | text | | |
| `catalogue_url` | text | | |
| `location` | text | | |
| `description` | text | | |
| `rights_policy_url` | text | | |

## 2. `record`

One row = one institution's description of something (not the historical item itself).

| Column | Type | Req | Notes |
|---|---|---|---|
| `id` | text | PK | |
| `title_original` | text | Req | Exactly as the source wrote it |
| `description` | text | | |
| `description_origin` | text | | source_transcribed, source_paraphrased, curator_written |
| `resource_type` | text | Req | archival_document, correspondence, register, map, photograph, person_profile, research_guide, journal_article, book, other |
| `language` | text | | |
| `date_display` | text | | Date as the source wrote it |
| `content_note` | text | | Cautions, e.g. discriminatory historical language |
| `container_title` | text | | Journal or book series |
| `notes` | text | | General notes |
| `record_source_id` | text | Req, FK → institution | Who supplies the description |
| `holding_institution_id` | text | FK → institution | Who holds the original |
| `holder_status` | text | Req, default `unknown` | confirmed, unconfirmed, unknown, not_applicable |
| `holder_note` | text | | |
| `source_url` | text | Req | Authoritative record page |
| `source_reference` | text | | Call number or catalogue ID |
| `digital_url` | text | | |
| `digitized` | text | default `unknown` | yes, partial, no, unknown, not_applicable |
| `access_mode` | text | default `unknown` | online, in_person, on_request, mixed, unknown |
| `access_instructions` | text | | |
| `access_restrictions` | text | | |
| `rights_statement` | text | | |
| `rights_url` | text | | |
| `reuse_scope` | text | Req, default `metadata_and_link_only` | metadata_and_link_only, description_ok, images_ok |
| `collection_method` | text | Req | manual, export, api, scrape |
| `imported_at` | text | Req | |
| `added_by` | text | | |
| `last_verified_at` | text | | |
| `source_evidence` | text | | What the checker looked at to verify the record |
| `verification_status` | text | Req, default `unverified` | unverified, verified, needs_review, link_broken |
| `link_last_checked` | text | | |
| `change_notes` | text | | |

## 3. `record_date`

| Column | Type | Req | Notes |
|---|---|---|---|
| `id` | integer | PK | Auto-numbered |
| `record_id` | text | Req, FK → record | |
| `kind` | text | Req | life, event, document, period_discussed, publication… |
| `label` | text | Req | As the source wrote it |
| `start_year` | integer | | Empty if unknown |
| `end_year` | integer | | |
| `approximate` | integer | Req, default 0 | 0 or 1 |
| `origin` | text | Req, default `source_stated` | |

## 4. `entity`

People, places, communities, subjects and events in one table.

| Column | Type | Req | Notes |
|---|---|---|---|
| `id` | text | PK | |
| `entity_type` | text | Req | person, place, community, subject, event |
| `name_preferred` | text | Req | |
| `disambiguator` | text | | Tells apart people with the same name |
| `description` | text | | |
| `external_id` | text | | Wikidata or GeoNames, optional |

## 5. `record_entity`

Links a record to an entity. The primary key is the combination of record, entity and role, so the same person can appear on one record as both author and subject.

| Column | Type | Req | Notes |
|---|---|---|---|
| `record_id` | text | PK, FK → record | |
| `entity_id` | text | PK, FK → entity | |
| `role` | text | PK | subject, author, contributor, creator, recipient, location, mentioned |
| `name_as_written` | text | | The source's own string |
| `origin` | text | Req | source_stated, curator_added, platform_generated |
| `link_basis` | text | | Why this link was made |

## 6. `record_relation`

Curated links between records. Related records that simply share an entity are found by query and are not stored here.

| Column | Type | Req | Notes |
|---|---|---|---|
| `id` | integer | PK | Auto-numbered |
| `record_a_id` | text | Req, FK → record | |
| `record_b_id` | text | Req, FK → record | |
| `relation_type` | text | Req | describes_same_resource, part_of, same_series, related_context |
| `basis` | text | Req | source_states, curator_judgement, auto_suggested |
| `evidence_note` | text | | |
| `evidence_url` | text | | |
| `status` | text | Req, default `proposed` | proposed, confirmed, rejected |
| `created_by` | text | | |
| `created_at` | text | | |

## 7. `record_search` (full-text index)

Columns: `record_id` (stored, not searched), `title`, `description`, `entity_names`. Filled from the other tables; not a source of truth.

## Relationships

- `institution` 1 to many `record`, through two foreign keys: `record_source_id` (required) and `holding_institution_id` (optional)
- `record` 1 to many `record_date`
- `record` many to many `entity`, through `record_entity`
- `record` many to many `record`, through `record_relation`

## Not in the file yet (commented out for later)

- `entity_alias`: `entity_id`, `alias`, `note`
- `enrichment`: `id`, `record_id`, `kind`, `content`, `origin`, `model`, `supporting_record_ids`, `status`, `created_at`
