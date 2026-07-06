from creator_sync.config import SourceConfig
from creator_sync.mapper import build_properties, plain_text

ACTOR = SourceConfig(
    key="actor_testing", label="Actor Testing", db_id="act", status_kind="select",
    field_map={
        "Creative Name": "Name", "Status": "Status",
        "Creator Assigned": "Creator Assigned", "Scriptwriter": "Scriptwriter",
        "Content Link": "Content Link", "Product": "Product",
        "Language": "Language", "Ready for Creator Date": "Ready for Creator Date",
        "Creator URL": "Creator URL",
    },
)
INFLUENCER = SourceConfig(
    key="influencer", label="Influencer", db_id="inf", status_kind="status",
    field_map={
        "Creative Name": "Name", "Status": "Status",
        "Creator @": "Creator Assigned", "Writer": "Scriptwriter",
        "Content Link": "Content Link", "Product": "Product", "Brief Link": "Brief Link",
    },
)
SPANISH = SourceConfig(
    key="spanish", label="Spanish", db_id="sp", status_kind="select",
    field_map={
        "Creative Name": "Name", "Status": "Status",
        "Creator Assigned": "Creator Assigned", "Content Link": "Content Link",
        "Product": "Product", "Ready for Creator Date": "Ready for Creator Date",
        "Creator URL": "Creator URL",
    },
    language_default="Spanish",
)


def rt(text):
    return [{"type": "text", "text": {"content": text}, "plain_text": text}]


def test_plain_text_joins():
    assert plain_text(rt("hello")) == "hello"
    assert plain_text([]) == ""


def test_actor_row_maps_curated_columns():
    page = {
        "id": "page-abc",
        "properties": {
            "Creative Name": {"type": "title", "title": rt("Gummy Ad 1")},
            "Status": {"type": "select", "select": {"name": "Ready For Creator"}},
            "Creator Assigned": {"type": "multi_select",
                                 "multi_select": [{"name": "Caleb Wood"}]},
            "Scriptwriter": {"type": "select", "select": {"name": "Tim"}},
            "Content Link": {"type": "rich_text", "rich_text": rt("http://script")},
            "Product": {"type": "select", "select": {"name": "Creatine Gummies"}},
            "Language": {"type": "multi_select", "multi_select": [{"name": "English"}]},
            "Ready for Creator Date": {"type": "date", "date": {"start": "2026-07-01"}},
            "Creator URL": {"type": "url", "url": "http://tiktok/x"},
        },
    }
    page["url"] = "https://src.example/page-abc"
    props = build_properties(page, ACTOR, "2026-07-06")
    assert props["Script"]["url"] == "https://src.example/page-abc"
    assert props["Name"]["title"][0]["text"]["content"] == "Gummy Ad 1"
    assert props["Status"]["select"]["name"] == "Ready For Creator"
    assert props["Creator Assigned"]["multi_select"] == [{"name": "Caleb Wood"}]
    assert props["Scriptwriter"]["multi_select"] == [{"name": "Tim"}]
    assert props["Content Link"]["rich_text"][0]["text"]["content"] == "http://script"
    assert props["Product"]["select"]["name"] == "Creatine Gummies"
    assert props["Language"]["multi_select"] == [{"name": "English"}]
    assert props["Ready for Creator Date"]["date"]["start"] == "2026-07-01"
    assert props["Creator URL"]["url"] == "http://tiktok/x"
    assert props["Source Tracker"]["select"]["name"] == "Actor Testing"
    assert props["Copied At"]["date"]["start"] == "2026-07-06"
    assert props["Source ID"]["rich_text"][0]["text"]["content"] == "page-abc"


def test_influencer_status_type_and_text_creator():
    page = {
        "id": "p2",
        "properties": {
            "Creative Name": {"type": "title", "title": rt("Inf Ad")},
            "Status": {"type": "status", "status": {"name": "Ready For Creator"}},
            "Creator @": {"type": "rich_text", "rich_text": rt("@somebody")},
            "Writer": {"type": "select", "select": {"name": "Axel"}},
            "Content Link": {"type": "rich_text", "rich_text": rt("link")},
            "Product": {"type": "select", "select": {"name": "Electrolytes"}},
            "Brief Link": {"type": "url", "url": "http://brief"},
        },
    }
    props = build_properties(page, INFLUENCER, "2026-07-06")
    assert props["Status"]["select"]["name"] == "Ready For Creator"
    assert props["Creator Assigned"]["multi_select"] == [{"name": "@somebody"}]
    assert props["Scriptwriter"]["multi_select"] == [{"name": "Axel"}]
    assert props["Brief Link"]["url"] == "http://brief"
    assert "Language" not in props
    assert "Ready for Creator Date" not in props


def test_spanish_language_default_applied():
    page = {
        "id": "p3",
        "properties": {
            "Creative Name": {"type": "title", "title": rt("Sp Ad")},
            "Status": {"type": "select", "select": {"name": "Ready For Creator"}},
            "Content Link": {"type": "rich_text", "rich_text": rt("link")},
            "Product": {"type": "select", "select": {"name": "Creatine Gummies"}},
        },
    }
    props = build_properties(page, SPANISH, "2026-07-06")
    assert props["Language"]["multi_select"] == [{"name": "Spanish"}]


def test_creator_free_text_with_comma_splits():
    page = {
        "id": "p5",
        "properties": {
            "Creative Name": {"type": "title", "title": rt("Inf Ad 2")},
            "Status": {"type": "status", "status": {"name": "Ready For Creator"}},
            "Creator @": {"type": "rich_text", "rich_text": rt("@john, @jane")},
            "Content Link": {"type": "rich_text", "rich_text": rt("link")},
            "Product": {"type": "select", "select": {"name": "Electrolytes"}},
        },
    }
    props = build_properties(page, INFLUENCER, "2026-07-06")
    assert props["Creator Assigned"]["multi_select"] == [{"name": "@john"}, {"name": "@jane"}]


def test_empty_values_are_omitted():
    page = {
        "id": "p4",
        "properties": {
            "Creative Name": {"type": "title", "title": []},
            "Status": {"type": "select", "select": None},
            "Content Link": {"type": "rich_text", "rich_text": []},
            "Product": {"type": "select", "select": None},
            "Creator URL": {"type": "url", "url": None},
        },
    }
    props = build_properties(page, SPANISH, "2026-07-06")
    # empties dropped, but always-present housekeeping remains
    assert "Status" not in props
    assert "Content Link" not in props
    assert "Creator URL" not in props
    assert props["Source ID"]["rich_text"][0]["text"]["content"] == "p4"
    assert props["Source Tracker"]["select"]["name"] == "Spanish"
    # Spanish default language still applied even when other fields empty
    assert props["Language"]["multi_select"] == [{"name": "Spanish"}]
