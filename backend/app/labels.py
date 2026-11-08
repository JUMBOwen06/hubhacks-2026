"""Display labels for the codes the API returns.

The database stores short codes (``journal_article``, ``not_applicable``). The
frontend shows these labels instead, fetched once from ``/labels``. Every value
allowed by a CHECK constraint in ``schema.sql`` has a label here, and
``tests/test_labels.py`` fails if one is missing.
"""
from __future__ import annotations

LABELS: dict[str, dict[str, str]] = {
    # record
    "resource_type": {
        "archival_document": "Archival document",
        "correspondence": "Letter or correspondence",
        "register": "Register",
        "map": "Map",
        "photograph": "Photograph",
        "person_profile": "Person profile",
        "research_guide": "Research guide",
        "journal_article": "Journal article",
        "book": "Book",
        "other": "Other",
    },
    "digitized": {
        "yes": "Digitized",
        "partial": "Partly digitized",
        "no": "Not digitized",
        "unknown": "Not known if digitized",
        "not_applicable": "Not applicable",
    },
    "access_mode": {
        "online": "Online",
        "in_person": "In person",
        "on_request": "On request",
        "mixed": "Online and in person",
        "unknown": "Access not known",
    },
    "holder_status": {
        "confirmed": "Confirmed",
        "unconfirmed": "Not yet confirmed",
        "unknown": "Unknown",
        "not_applicable": "Not applicable",
    },
    "description_origin": {
        "source_transcribed": "Copied from the source",
        "source_paraphrased": "Paraphrased from the source",
        "curator_written": "Written by our research team",
    },
    "reuse_scope": {
        "metadata_and_link_only": "Details and link only",
        "description_ok": "Description may be reused",
        "images_ok": "Images may be reused",
    },
    "collection_method": {
        "manual": "Entered by hand",
        "export": "Imported from a catalogue export",
        "api": "Imported through an API",
        "scrape": "Collected from web pages",
    },
    "verification_status": {
        "verified": "Verified",
        "unverified": "Not yet verified",
        "needs_review": "Needs review",
        "link_broken": "Link broken",
    },
    # institution
    "institution_type": {
        "archive": "Archive",
        "library": "Library",
        "museum": "Museum",
        "university": "University",
        "government": "Government",
        "publisher": "Publisher",
        "community": "Community organization",
        "other": "Other",
    },
    # entity and record_entity
    "entity_type": {
        "person": "Person",
        "place": "Place",
        "community": "Community",
        "subject": "Subject",
        "event": "Event",
        "organization": "Organization",
    },
    "role": {
        "subject": "Subject",
        "author": "Author",
        "contributor": "Contributor",
        "creator": "Creator",
        "recipient": "Recipient",
        "location": "Place",
        "mentioned": "Mentioned",
    },
    # record_entity.origin and record_date.origin
    "origin": {
        "source_stated": "Stated by the source",
        "curator_added": "Added by our research team",
        "platform_generated": "Worked out by the platform",
    },
    # record_date.kind (not constrained in the schema; these are the values in use)
    "date_kind": {
        "life": "Lifetime",
        "event": "Event",
        "document": "Date of the document",
        "period_discussed": "Period discussed",
        "publication": "Published",
        "designation": "Designated",
    },
    # record_relation
    "relation_type": {
        "describes_same_resource": "Same resource, described by another institution",
        "part_of": "Part of",
        "same_series": "Same series",
        "related_context": "Related context",
    },
    "relation_basis": {
        "source_states": "Stated by the source",
        "curator_judgement": "Research team's judgement",
        "auto_suggested": "Suggested automatically",
    },
    "relation_status": {
        "proposed": "Proposed",
        "confirmed": "Confirmed",
        "rejected": "Rejected",
    },
    # Connected records on a record page: how a shared entity links two records.
    # Never phrase these as people being related or having met.
    "connection_link": {
        "shared_subject": "Shares a subject",
        "shared_place": "Shares a place",
        "same_author": "Same author, creator or contributor",
        "named_in_both": "Named in both records",
    },
    # "appears_with" on a connection page: how another entity shares records with this one.
    "appears_with_relation": {
        "named_together": "In the same records",
        "made_record_naming": "Made a record naming this entity",
        "named_in_work_by": "Named in a record this person made",
        "co_credited": "Credited on the same records",
    },
}


def label(field: str, value: str | None) -> str | None:
    """Label for a code, or the code itself if it has none (never raises)."""
    if value is None:
        return None
    return LABELS.get(field, {}).get(value, value)
