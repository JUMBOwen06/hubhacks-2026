"""Terminology bridge: search terms that should also find each other.

DRAFT - for review by BCCNS and community members before any public use.

Why it exists: older catalogue records and titles often use historical or harmful
terms, so people searching with current, respectful terms can miss them. Each group
lists terms searched together. Historical terms are listed only so that records
using them can be found; the platform displays current terms in its own text.

Also holds aliases for one person or place (e.g. historical place names).
"""
from __future__ import annotations

import re

GROUPS: list[dict] = [
    {
        "id": "freedom-seekers",
        "terms": ["freedom seekers", "freedom seeker", "self-emancipated", "self emancipated",
                  "fugitive slaves", "fugitive slave", "escaped slaves", "escaped slave"],
        "note": "'Freedom seeker' and 'self-emancipated' are current terms; "
                "'fugitive slave' appears in historical records and older titles.",
    },
    {
        "id": "enslaved-people",
        "terms": ["enslaved people", "enslaved person", "enslaved", "enslavement", "slavery",
                  "slaves", "slave"],
        "note": "'Enslaved person' is the current term; historical records use 'slave'.",
    },
    {
        "id": "black-canadians",
        "terms": ["black canadians", "black canadian", "african canadians", "african canadian"],
        "note": "Both terms are in current use.",
    },
    {
        "id": "african-nova-scotians",
        "terms": ["african nova scotians", "african nova scotian", "black nova scotians",
                  "black nova scotian"],
        "note": "Both terms are in current use.",
    },
    {
        "id": "ontario-historical-names",
        "terms": ["upper canada", "canada west", "ontario"],
        "note": "Historical names for parts of present-day Ontario.",
    },
    {
        "id": "maroon-hill",
        "terms": ["maroon hill", "boydville"],
        "note": "Two names for one Nova Scotia settlement, as given in the 1829 map record.",
    },
    {
        "id": "hammonds-plains",
        "terms": ["upper hammonds plains", "hammonds plains", "hammond's plains"],
        "note": "Spelling variants.",
    },
    {
        "id": "mary-ann-shadd",
        "terms": ["mary ann shadd cary", "mary ann shadd"],
        "note": "One person. Adrienne Shadd, a historian and descendant, is a different person.",
    },
]

_TERM_TO_GROUP = {t: g for g in GROUPS for t in g["terms"]}
_TERMS_LONGEST_FIRST = sorted(_TERM_TO_GROUP, key=len, reverse=True)
_TOKEN = re.compile(r"[\w'-]+", re.UNICODE)


def normalize(text: str) -> str:
    text = text.lower().replace("’", "'").replace("‘", "'")
    return " ".join(text.split())


def segment(query: str) -> list[dict]:
    """Split a query into terminology-group matches and plain tokens, in order.

    "freedom seekers africville" ->
      [{"kind": "group", "text": "freedom seekers", ...}, {"kind": "token", "text": "africville"}]
    """
    text = normalize(query)
    taken = [False] * len(text)
    found = []
    for term in _TERMS_LONGEST_FIRST:
        for m in re.finditer(r"(?<![\w'-])" + re.escape(term) + r"(?![\w'-])", text):
            if any(taken[m.start():m.end()]):
                continue
            for i in range(m.start(), m.end()):
                taken[i] = True
            g = _TERM_TO_GROUP[term]
            found.append((m.start(), {"kind": "group", "text": term, "group": g["id"],
                                      "terms": g["terms"], "note": g["note"]}))
    for m in _TOKEN.finditer(text):
        if not any(taken[m.start():m.end()]):
            tok = m.group().strip("'-")
            if tok:
                found.append((m.start(), {"kind": "token", "text": tok}))
    return [seg for _, seg in sorted(found, key=lambda x: x[0])]


def aliases_for(name: str) -> list[str]:
    g = _TERM_TO_GROUP.get(normalize(name))
    return [t for t in g["terms"] if t != normalize(name)] if g else []
