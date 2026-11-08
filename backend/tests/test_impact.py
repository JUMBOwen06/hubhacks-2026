"""Anonymous Impact counts: what is stored, what is refused, and the summary."""
import datetime as dt

from app import impact


def test_stores_only_anonymous_fields(tmp_path, conn):
    ic = impact.connect(tmp_path / "i.db")
    day = dt.date(2026, 11, 8)
    assert impact.record_event(ic, {"kind": "visit", "ip": "1.2.3.4", "ua": "x"}, day)
    assert impact.record_event(ic, {"kind": "search", "query": "  AfricVille  ", "results": 4}, day)
    assert impact.record_event(ic, {"kind": "search", "query": "rosa parks", "results": 0}, day)
    assert impact.record_event(ic, {"kind": "source_click", "record_id": "JRN-007"}, day)
    assert impact.record_event(ic, {"kind": "page_view", "page": "record", "record_id": "JRN-007"}, day)
    # refused: unknown kind, empty search, click without a record, bad record id
    assert not impact.record_event(ic, {"kind": "track_me"}, day)
    assert not impact.record_event(ic, {"kind": "search", "query": "   "}, day)
    assert not impact.record_event(ic, {"kind": "source_click"}, day)
    assert not impact.record_event(ic, {"kind": "source_click", "record_id": "<script>"}, day)
    cols = [r[1] for r in ic.execute("PRAGMA table_info(event)")]
    assert cols == ["id", "day", "kind", "page", "query", "result_count", "record_id"]

    s = impact.summary(ic, conn, days=7, today=day)
    assert s["totals"] == {"visits": 1, "page_views": 1, "searches": 2, "searches_no_results": 1,
                           "source_clicks": 1, "institutions_reached": 1}
    assert s["searches_no_results"][0]["query"] == "rosa parks"
    assert s["top_searches"][0]["query"] in {"africville", "rosa parks"}
    assert s["sent_to_institutions"][0]["count"] == 1
    assert s["most_viewed_records"][0]["id"] == "JRN-007"
    assert len(s["daily"]) == 7 and s["daily"][-1]["searches"] == 2


def test_events_endpoint_and_summary(client):
    assert client.post("/events", content='{"kind":"search","query":"birchtown","results":3}',
                       headers={"Content-Type": "text/plain"}).status_code == 204
    assert client.post("/events", content="not json").status_code == 204
    s = client.get("/impact").json()
    assert s["totals"]["searches"] >= 1
    assert "No cookies" in s["privacy"]
