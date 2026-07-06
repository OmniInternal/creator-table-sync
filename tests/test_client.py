from creator_sync.notion_client import NotionClient


class FakeResp:
    def __init__(self, status, payload, headers=None):
        self.status_code = status
        self._payload = payload
        self.headers = headers or {}

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def request(self, method, url, headers=None, json=None):
        self.calls.append((method, url, json))
        return self.responses.pop(0)


def test_iter_query_paginates():
    pages = [
        FakeResp(200, {"results": [{"id": "1"}], "has_more": True, "next_cursor": "c"}),
        FakeResp(200, {"results": [{"id": "2"}], "has_more": False, "next_cursor": None}),
    ]
    sess = FakeSession(pages)
    client = NotionClient("ntn_x", "2022-06-28", session=sess, sleep=lambda s: None)
    ids = [p["id"] for p in client.iter_query("db1", {"property": "Status"})]
    assert ids == ["1", "2"]
    # second request must carry the cursor
    assert sess.calls[1][2]["start_cursor"] == "c"


def test_retry_on_429_then_success():
    responses = [
        FakeResp(429, {}, headers={"Retry-After": "0"}),
        FakeResp(200, {"id": "ok"}),
    ]
    sess = FakeSession(responses)
    slept = []
    client = NotionClient("ntn_x", "2022-06-28", session=sess, sleep=lambda s: slept.append(s))
    result = client.create_page("db1", {"Name": {"title": []}})
    assert result["id"] == "ok"
    assert slept  # it waited


def test_headers_include_version_and_auth():
    sess = FakeSession([FakeResp(200, {"ok": True})])
    client = NotionClient("ntn_secret", "2022-06-28", session=sess, sleep=lambda s: None)
    client.retrieve_database("db1")
    _, _, _ = sess.calls[0]
    # headers checked via a captured attribute
    assert client.last_headers["Authorization"] == "Bearer ntn_secret"
    assert client.last_headers["Notion-Version"] == "2022-06-28"
