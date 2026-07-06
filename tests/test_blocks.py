from creator_sync.blocks import (
    sanitize_block, sanitize_tree, fetch_block_tree, append_tree, IMAGE_PLACEHOLDER,
)


def rt(text, link=None):
    item = {"type": "text", "text": {"content": text}, "plain_text": text}
    if link:
        item["text"]["link"] = {"url": link}
        item["href"] = link
    return [item]


def test_paragraph_preserves_text_and_link():
    block = {"type": "paragraph", "paragraph": {"rich_text": rt("hi", link="http://x"), "color": "default"}}
    nodes = sanitize_block(block)
    assert len(nodes) == 1
    p = nodes[0]["payload"]
    assert p["type"] == "paragraph"
    assert p["paragraph"]["rich_text"][0]["text"]["content"] == "hi"
    assert p["paragraph"]["rich_text"][0]["text"]["link"] == {"url": "http://x"}
    assert p["paragraph"]["color"] == "default"


def test_heading_and_todo_and_callout():
    assert sanitize_block({"type": "heading_2", "heading_2": {"rich_text": rt("H")}})[0]["payload"]["type"] == "heading_2"
    todo = sanitize_block({"type": "to_do", "to_do": {"rich_text": rt("x"), "checked": True}})[0]["payload"]
    assert todo["to_do"]["checked"] is True
    callout = sanitize_block({"type": "callout", "callout": {"rich_text": rt("c"), "icon": {"type": "emoji", "emoji": "💡"}}})[0]["payload"]
    assert callout["callout"]["icon"] == {"type": "emoji", "emoji": "💡"}


def test_nested_children_preserved():
    block = {"type": "toggle", "toggle": {"rich_text": rt("parent")},
             "_children": [{"type": "paragraph", "paragraph": {"rich_text": rt("child")}}]}
    node = sanitize_block(block)[0]
    assert node["payload"]["type"] == "toggle"
    assert len(node["children"]) == 1
    assert node["children"][0]["payload"]["paragraph"]["rich_text"][0]["text"]["content"] == "child"


def test_divider():
    assert sanitize_block({"type": "divider", "divider": {}})[0]["payload"] == {"type": "divider", "divider": {}}


def test_column_list_flattens_to_inner_blocks():
    block = {"type": "column_list", "column_list": {}, "_children": [
        {"type": "column", "column": {}, "_children": [
            {"type": "paragraph", "paragraph": {"rich_text": rt("A")}}]},
        {"type": "column", "column": {}, "_children": [
            {"type": "paragraph", "paragraph": {"rich_text": rt("B")}}]},
    ]}
    nodes = sanitize_block(block)
    assert [n["payload"]["paragraph"]["rich_text"][0]["text"]["content"] for n in nodes] == ["A", "B"]


def test_image_becomes_placeholder_paragraph():
    node = sanitize_block({"type": "image", "image": {"type": "file", "file": {"url": "http://tmp"}}})[0]
    assert node["payload"]["paragraph"]["rich_text"][0]["text"]["content"] == IMAGE_PLACEHOLDER


def test_url_bearing_block_becomes_link_paragraph():
    node = sanitize_block({"type": "bookmark", "bookmark": {"url": "http://b"}})[0]
    rtxt = node["payload"]["paragraph"]["rich_text"][0]
    assert rtxt["text"]["link"] == {"url": "http://b"}


def test_unsupported_block_skipped():
    assert sanitize_block({"type": "unsupported", "unsupported": {}}) == []
    assert sanitize_block({"type": "table_of_contents", "table_of_contents": {}}) == []


def test_mention_falls_back_to_plain_text():
    block = {"type": "paragraph", "paragraph": {"rich_text": [
        {"type": "mention", "mention": {}, "plain_text": "@Someone"}]}}
    rtxt = sanitize_block(block)[0]["payload"]["paragraph"]["rich_text"]
    assert rtxt[0]["text"]["content"] == "@Someone"


# ---- tree fetch + append against a fake client ----

class FakeClient:
    def __init__(self, children_by_id):
        self.children_by_id = children_by_id
        self.appends = []
        self._counter = 0

    def iter_block_children(self, block_id):
        return iter(self.children_by_id.get(block_id, []))

    def append_block_children(self, block_id, children):
        results = []
        for _ in children:
            self._counter += 1
            results.append({"id": f"new{self._counter}"})
        self.appends.append((block_id, children))
        return {"results": results}


def test_fetch_block_tree_recurses():
    client = FakeClient({
        "root": [{"id": "b1", "type": "toggle", "toggle": {"rich_text": rt("t")}, "has_children": True}],
        "b1": [{"id": "b2", "type": "paragraph", "paragraph": {"rich_text": rt("c")}, "has_children": False}],
    })
    tree = fetch_block_tree(client, "root")
    assert tree[0]["_children"][0]["id"] == "b2"


def test_append_tree_batches_and_recurses():
    # 150 top-level nodes -> 2 batches (100 + 50); one has a child -> extra append
    nodes = [{"payload": {"type": "paragraph", "paragraph": {"rich_text": rt(str(i))}}, "children": []}
             for i in range(150)]
    nodes[0]["children"] = [{"payload": {"type": "paragraph", "paragraph": {"rich_text": rt("child")}}, "children": []}]
    client = FakeClient({})
    total = append_tree(client, "dest", nodes)
    assert total == 151
    # batch sizes: 100, 50 under "dest", then 1 under the first created child block
    assert [len(c) for _, c in client.appends] == [100, 50, 1]


def test_heading_with_children_flattens_to_siblings():
    block = {"type": "heading_3", "heading_3": {"rich_text": rt("H")},
             "_children": [{"type": "paragraph", "paragraph": {"rich_text": rt("under")}}]}
    nodes = sanitize_block(block)
    # heading can't hold children -> heading, then the child as a sibling
    assert [n["payload"]["type"] for n in nodes] == ["heading_3", "paragraph"]
    assert all(n["children"] == [] for n in nodes)


def test_long_text_run_is_split_under_2000():
    big = "x" * 4500
    block = {"type": "paragraph", "paragraph": {"rich_text": [
        {"type": "text", "text": {"content": big}, "plain_text": big}]}}
    runs = sanitize_block(block)[0]["payload"]["paragraph"]["rich_text"]
    assert [len(r["text"]["content"]) for r in runs] == [2000, 2000, 500]


def test_sanitize_tree_flattens_list():
    tree = [
        {"type": "paragraph", "paragraph": {"rich_text": rt("one")}},
        {"type": "image", "image": {"type": "external", "external": {"url": "u"}}},
    ]
    out = sanitize_tree(tree)
    assert len(out) == 2
    assert out[1]["payload"]["paragraph"]["rich_text"][0]["text"]["content"] == IMAGE_PLACEHOLDER
