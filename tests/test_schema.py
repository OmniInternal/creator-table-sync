from creator_sync.schema import (
    DEST_COLUMNS, missing_columns, add_properties_payload, ensure_schema,
)


def test_dest_columns_cover_spec():
    assert DEST_COLUMNS["Name"] == "title"
    assert DEST_COLUMNS["Status"] == "select"
    assert DEST_COLUMNS["Creator Assigned"] == "multi_select"
    assert DEST_COLUMNS["Scriptwriter"] == "multi_select"
    assert DEST_COLUMNS["Ready for Creator Date"] == "date"
    assert DEST_COLUMNS["Creator URL"] == "url"
    assert DEST_COLUMNS["Source ID"] == "rich_text"


def test_missing_columns_ignores_existing_and_name():
    db = {"properties": {"Name": {"type": "title"}, "Status": {"type": "select"}}}
    missing = missing_columns(db)
    assert "Name" not in missing
    assert "Status" not in missing
    assert "Creator Assigned" in missing
    assert "Source ID" in missing


def test_add_payload_builds_correct_configs():
    payload = add_properties_payload({"Status": "select", "Creator URL": "url",
                                      "Source ID": "rich_text", "Copied At": "date",
                                      "Creator Assigned": "multi_select"})
    assert payload["Status"] == {"select": {}}
    assert payload["Creator URL"] == {"url": {}}
    assert payload["Source ID"] == {"rich_text": {}}
    assert payload["Copied At"] == {"date": {}}
    assert payload["Creator Assigned"] == {"multi_select": {}}


class FakeClient:
    def __init__(self, db):
        self._db = db
        self.patched = None

    def retrieve_database(self, db_id):
        return self._db

    def update_database(self, db_id, properties):
        self.patched = properties
        return {"ok": True}


def test_ensure_schema_patches_only_missing():
    db = {"properties": {"Name": {"type": "title"}, "Status": {"type": "select"}}}
    client = FakeClient(db)
    added = ensure_schema(client, "dest")
    assert "Status" not in added
    assert "Creator Assigned" in added
    assert client.patched is not None
    assert "Creator Assigned" in client.patched


def test_ensure_schema_noop_when_complete():
    props = {name: {"type": t} for name, t in DEST_COLUMNS.items()}
    client = FakeClient({"properties": props})
    added = ensure_schema(client, "dest")
    assert added == []
    assert client.patched is None
