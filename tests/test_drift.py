"""Renamed source columns (DR-UGC 2026-10: Creative Name → Title, Creator Assigned →
Style/Creator; Spanish: Creator / Style) used to be skipped SILENTLY, so a copy
arrived with no name or creator. These pin the aliases, the nameless-row guard,
and that a source which can no longer fill a core column is skipped LOUDLY."""
import pytest

from creator_sync.config import Config, SourceConfig, _COMMON_FIELD_MAP
from creator_sync.mapper import build_properties
from creator_sync.sync import DriftError, source_drift, sync

DR = SourceConfig("dr_ugc", "DR-UGC", "dr", "select", dict(_COMMON_FIELD_MAP))


def rt(t):
    return [{"plain_text": t, "text": {"content": t}}]


def dr_row(pid, title="Gummy Ad 9", creator="Caleb Wood"):
    return {"id": pid, "url": f"https://src/{pid}", "properties": {
        "Title": {"type": "title", "title": rt(title)},
        "Style/Creator": {"type": "multi_select", "multi_select": [{"name": creator}]},
        "Status": {"type": "select", "select": {"name": "Ready For Creator"}},
    }}


def test_renamed_title_and_creator_still_map():
    props = build_properties(dr_row("p1"), DR, "2026-10-28")
    assert props["Name"]["title"][0]["text"]["content"] == "Gummy Ad 9"
    assert props["Creator Assigned"] == {"multi_select": [{"name": "Caleb Wood"}]}


def test_spanish_creator_slash_style_maps():
    page = {"id": "s1", "properties": {
        "Creative Name": {"type": "title", "title": rt("ES ad")},
        "Creator / Style": {"type": "multi_select", "multi_select": [{"name": "Lupita"}]},
    }}
    props = build_properties(page, DR, "2026-10-28")
    assert props["Creator Assigned"] == {"multi_select": [{"name": "Lupita"}]}


def test_drift_names_a_core_column_the_schema_cannot_fill():
    assert source_drift(DR, dr_row("x")["properties"]) == []
    no_creator = {"Title": {"type": "title"}, "Status": {"type": "select"}}
    assert source_drift(DR, no_creator) == ["Creator Assigned (from Creator Assigned)"]


class Fake:
    def __init__(self, schema, rows):
        self.schema, self.rows, self.created = schema, rows, []

    def retrieve_database(self, db_id):
        if db_id == "dest":
            return {"properties": {"Name": {"type": "title"}, "Source ID": {"type": "rich_text"}}}
        return {"properties": self.schema}

    def update_database(self, db_id, properties):
        return {}

    def iter_query(self, db_id, flt):
        return iter([] if flt is None else self.rows)

    def create_page(self, parent, props):
        self.created.append(props)
        return {"id": "new"}

    def iter_block_children(self, block_id):
        return iter([])

    def append_block_children(self, block_id, children):
        return {}


def test_a_drifted_source_is_skipped_and_the_run_fails_loudly():
    fake = Fake({"Title": {"type": "title"}}, [dr_row("p1")])
    with pytest.raises(DriftError, match="dr_ugc"):
        sync(Config("t", "v", "dest", "Ready For Creator", [DR]), fake, "2026-10-28", logger=lambda *_: None)
    assert fake.created == []


def test_a_nameless_row_is_never_created():
    fake = Fake(dr_row("x")["properties"], [dr_row("p1", title=""), dr_row("p2")])
    out = sync(Config("t", "v", "dest", "Ready For Creator", [DR]), fake, "2026-10-28", logger=lambda *_: None)
    assert len(fake.created) == 1 and out["errors"] == 1
