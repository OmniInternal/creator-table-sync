from creator_sync.config import Config, SourceConfig
from creator_sync.sync import status_filter, sync


def test_status_filter_select_vs_status():
    sel = SourceConfig("k", "L", "db", "select", {})
    st = SourceConfig("k", "L", "db", "status", {})
    assert status_filter(sel, "Ready For Creator") == {
        "property": "Status", "select": {"equals": "Ready For Creator"}}
    assert status_filter(st, "Ready For Creator") == {
        "property": "Status", "status": {"equals": "Ready For Creator"}}


def rt(t):
    return [{"plain_text": t, "text": {"content": t}}]


def src_row(pid, name):
    return {"id": pid, "properties": {
        "Creative Name": {"type": "title", "title": rt(name)},
        "Status": {"type": "select", "select": {"name": "Ready For Creator"}},
        "Content Link": {"type": "rich_text", "rich_text": rt("link")},
    }}


class FakeClient:
    def __init__(self, dest_rows, source_rows_by_db):
        self.dest_rows = dest_rows
        self.source_rows_by_db = source_rows_by_db
        self.created = []
        self.ensured = False

    def retrieve_database(self, db_id):
        return {"properties": {"Name": {"type": "title"}, "Source ID": {"type": "rich_text"}}}

    def update_database(self, db_id, properties):
        return {}

    def iter_query(self, db_id, filter):
        if filter is None:
            return iter(self.dest_rows)
        return iter(self.source_rows_by_db.get(db_id, []))

    def create_page(self, parent_db_id, properties):
        self.created.append(properties)
        return {"id": "new"}


def make_config():
    src = SourceConfig("actor_testing", "Actor Testing", "act", "select", {
        "Creative Name": "Name", "Status": "Status", "Content Link": "Content Link"})
    return Config("ntn", "2022-06-28", "dest", "Ready For Creator", [src])


def test_sync_creates_only_new_rows():
    dest = [{"properties": {"Source ID": {"type": "rich_text", "rich_text": rt("existing1")}}}]
    client = FakeClient(dest, {"act": [src_row("existing1", "Old"), src_row("fresh2", "New")]})
    summary = sync(make_config(), client, "2026-07-06")
    assert summary["created"] == 1
    assert summary["skipped"] == 1
    assert client.created[0]["Source ID"]["rich_text"][0]["text"]["content"] == "fresh2"


def test_sync_dedups_within_a_single_run():
    dest = []
    # same page id appears twice in the source query results
    client = FakeClient(dest, {"act": [src_row("dup", "A"), src_row("dup", "A")]})
    summary = sync(make_config(), client, "2026-07-06")
    assert summary["created"] == 1
