from creator_sync.dedup import existing_source_ids, is_new


class FakeClient:
    def __init__(self, rows):
        self._rows = rows

    def iter_query(self, db_id, filter):
        assert filter is None  # dedup scans all rows
        return iter(self._rows)


def row(source_id):
    return {
        "properties": {
            "Source ID": {"type": "rich_text",
                          "rich_text": [{"plain_text": source_id,
                                         "text": {"content": source_id}}]}
        }
    }


def test_collects_source_ids():
    client = FakeClient([row("a"), row("b"), row("")])
    ids = existing_source_ids(client, "dest")
    assert ids == {"a", "b"}  # empty string skipped


def test_is_new():
    existing = {"a", "b"}
    assert is_new("c", existing) is True
    assert is_new("a", existing) is False
