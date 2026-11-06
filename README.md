# African Canadian History Discovery Platform

A planned discovery platform intended to help people find information about African Canadian history across different Canadian institutions from one place.

The project is being developed as a proof of concept for the **Black Cultural Centre for Nova Scotia (BCCNS)**. Rather than replacing institutional archives or hosting entire collections, the platform aims to organize selected record information, make it searchable, and direct users to the institutions that provide or hold the original materials.

> **Project status:** Planning and prototyping. The features and pages below describe the proposed scope; they should not be interpreted as already implemented.

## Project goals

- Make it easier to discover relevant historical records across multiple institutions.
- Bring records from different sources into a consistent, searchable format.
- Clearly identify where original material is held and which institution supplies the record description or contextual information.
- Help users understand how to access the original material.
- Preserve source attribution and respect copyright and institutional access restrictions.

## Core functionality

The proposed platform will prioritize the following functions:

1. **Unified search** — Search records from multiple institutions through one search interface. Search terms may include people, places, subjects, titles, dates, and institutions.
2. **Filtering and sorting** — Narrow results by institution, date or date range, resource type, person, place, and subject. Sort results where useful, such as by date or relevance.
3. **Standardized search results** — Display records from different institutions in a consistent format so users can understand and compare them.
4. **Record details and provenance** — Show information about an individual resource, including its title, description, dates, people, places, resource type, source, and provenance.
5. **Direct links and access information** — Link to the authoritative institutional record and explain how the original material can be accessed, where that information is available.
6. **Related records** *(recommended enhancement)* — Help users discover records connected by a person, place, community, event, or subject when those connections are supported by the source information.
7. **AI-assisted or natural-language search** *(stretch goal)* — Allow users to search in everyday language. Any generated answers must be grounded in indexed records and provide links or citations to their sources.

### Important metadata distinction

Each record should distinguish between:

- **Holding institution:** The institution that holds the original material.
- **Record source:** The institution that provides the description, database entry, or contextual information displayed by the platform.

These may be different institutions. The platform should not imply that the record source necessarily holds the original material.

## Planned website pages

### 1. Home / Search

The main page and primary entry point to the platform.

- Prominent search bar.
- Brief explanation of the platform.
- Search filters for people, places, subjects, dates, resource types, and institutions.
- Consistent search-result cards.
- Links from results to individual record pages.
- Featured records or collections.

### 2. Record Details

Opened when a user selects a search result.

- Original title and description.
- Relevant dates, people, places, and subjects.
- Resource type.
- Holding institution and record source.
- Provenance and relevant rights information.
- Access instructions and a direct link to the institutional record.
- Related records, when supported by verified information.

### 3. Sources / Institutions

Explains which institutions and collections are represented in the platform.

- Institution name and description.
- Types of records represented.
- Number of indexed records, if known.
- Link to the institution's website or catalogue.
- Last verified or updated date, where available.

### 4. About / How It Works

Explains the purpose and approach of the project.

- The problem the platform is intended to address.
- Its connection to BCCNS.
- Who the platform is intended to serve.
- How records are collected, organized, and searched.
- How attribution, provenance, copyright, and access restrictions are handled.
- Current coverage and limitations.

### Possible future pages

These are outside the initial page scope unless time and project needs allow:

- **Browse / Explore** — Explore records by community, location, time period, or subject without entering a search query.
- **Saved Records** — Save records for later reference; would likely require user accounts or local browser storage.
- **Admin / Data Management** — Add, edit, verify, and remove records.

## Suggested workstreams

The work can be divided into five areas. Team members may cover more than one area depending on team size.

1. **Research and data collection** — Identify useful source records, collect relevant metadata, verify links and access details, and review reuse restrictions.
2. **Metadata and system architecture** — Define the shared metadata structure, map source fields into it, and plan how records will be stored and connected.
3. **Backend and search development** — Set up data storage and implement search, filtering, sorting, and the interface used by the frontend to retrieve records.
4. **Frontend and user experience** — Design and build the search page, results, record details, sources page, and About page.
5. **Product direction, testing, and presentation** — Define the MVP, coordinate the work, test realistic searches and links, and prepare the demonstration.

## Initial prototype target

A realistic first version should demonstrate this user journey:

1. A user searches for a historical person, place, or subject.
2. The platform returns relevant records from at least two institutions.
3. The user filters the results.
4. The user opens a record and sees consistent metadata, provenance, the holding institution, and the record source.
5. The user follows a link or access instructions to find the original institutional resource.

A small, accurate, manually verified dataset (for example, approximately 10–20 records) is a reasonable starting target. The final number should depend on the time available and the quality of the records.

## Data, attribution, and accuracy principles

- Prefer information that is permitted to be reused; public availability does not automatically grant permission to copy descriptions, images, or full documents.
- Do not copy entire collections or conduct bulk harvesting without confirming permission and applicable terms.
- Keep institutional titles and source information identifiable; use independently written descriptions where appropriate.
- Link back to the authoritative institutional record whenever possible.
- Keep separate records separate, even when they relate to the same person or event. Connections should be evidence-based.
- Track where information came from and when it was added or last verified.
- Be transparent about which collections are included and what the platform does not cover.
- If information cannot be verified, do not present it as fact.

## Technology

**Technology stack: To be determined.**

## Current next steps

- Confirm the intended users and MVP scope with the mentor.
- Select a small set of records from two or more institutions and verify their source links and access details.
- Agree on the common metadata structure.
- Sketch the search and record-details interfaces.
- Build the basic search-to-record user journey before attempting stretch features such as related records