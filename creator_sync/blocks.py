"""Deep-copy a Notion page body (block tree) into another page.

The scripts the coordinator hands to creators live in each source row's page
BODY, not in a property. This module fetches that block tree and reproduces it
under a destination page, faithfully for text-bearing blocks and gracefully for
the rest (images/unsupported become a small placeholder — the `Script` link
column always points back to the source row as a fallback).
"""

from __future__ import annotations

# Text-bearing blocks we reproduce faithfully (rich_text + nested children).
TEXT_BLOCKS = {
    "paragraph", "heading_1", "heading_2", "heading_3",
    "bulleted_list_item", "numbered_list_item", "to_do", "quote",
    "callout", "toggle",
}

# Of those, the subset that can actually HOLD children via the API. Headings
# cannot (unless toggleable), so their children are flattened to siblings.
CHILD_SUPPORTING = {
    "paragraph", "bulleted_list_item", "numbered_list_item",
    "to_do", "quote", "callout", "toggle",
}

IMAGE_PLACEHOLDER = "🖼 image — see linked source row"


TEXT_LIMIT = 2000  # Notion rejects a single text run longer than 2000 chars.


def _emit(out: list, content: str, link=None, ann=None) -> None:
    """Append text, splitting into <=2000-char runs (Notion's per-run limit)."""
    if content == "":
        item = {"type": "text", "text": {"content": ""}}
        if link:
            item["text"]["link"] = link
        if ann:
            item["annotations"] = ann
        out.append(item)
        return
    for i in range(0, len(content), TEXT_LIMIT):
        item = {"type": "text", "text": {"content": content[i:i + TEXT_LIMIT]}}
        if link:
            item["text"]["link"] = link
        if ann:
            item["annotations"] = ann
        out.append(item)


def _clean_rich_text(rich: list) -> list:
    """Reduce a source rich_text array to a create-safe form (text + link +
    annotations); mentions/equations fall back to their plain text; long runs
    are split to stay under Notion's 2000-char-per-run limit."""
    out: list = []
    for r in rich or []:
        if r.get("type") == "text" and r.get("text"):
            _emit(out, r["text"].get("content", ""), r["text"].get("link"), r.get("annotations"))
        else:
            txt = r.get("plain_text", "")
            if txt:
                _emit(out, txt)
    return out


def _url_of(block: dict, t: str):
    obj = block.get(t, {}) or {}
    if isinstance(obj, dict):
        if obj.get("url"):
            return obj["url"]
        for host in ("external", "file"):
            sub = obj.get(host)
            if isinstance(sub, dict) and sub.get("url"):
                return sub["url"]
    return None


def _paragraph(text: str, link: str | None = None) -> dict:
    rt = {"type": "text", "text": {"content": text}}
    if link:
        rt["text"]["link"] = {"url": link}
    return {"type": "paragraph", "paragraph": {"rich_text": [rt]}}


def sanitize_block(block: dict) -> list:
    """Turn one source block into zero or more create-ready nodes.

    Returns a list because some blocks expand (column_list flattens to its
    inner blocks) or collapse (unsupported blocks may drop to nothing). Each
    node is `{"payload": <create block>, "children": [<node>...]}`; children are
    appended recursively so nesting of any depth is preserved.
    """
    t = block.get("type")
    kids = block.get("_children", [])

    if t in TEXT_BLOCKS:
        obj = block.get(t, {}) or {}
        payload_obj = {"rich_text": _clean_rich_text(obj.get("rich_text"))}
        if "color" in obj:
            payload_obj["color"] = obj["color"]
        if t == "to_do":
            payload_obj["checked"] = bool(obj.get("checked"))
        if t == "callout" and obj.get("icon"):
            payload_obj["icon"] = obj["icon"]
        child_nodes = []
        for c in kids:
            child_nodes += sanitize_block(c)
        node = {"payload": {"type": t, t: payload_obj}, "children": []}
        if t in CHILD_SUPPORTING:
            node["children"] = child_nodes
            return [node]
        # Block type can't hold children (e.g. a heading) — emit it, then its
        # former children as following siblings so no content is lost.
        return [node] + child_nodes

    if t == "code":
        obj = block.get("code", {}) or {}
        return [{"payload": {"type": "code", "code": {
            "rich_text": _clean_rich_text(obj.get("rich_text")),
            "language": obj.get("language", "plain text"),
        }}, "children": []}]

    if t == "divider":
        return [{"payload": {"type": "divider", "divider": {}}, "children": []}]

    if t in ("column_list", "column"):
        # Flatten layout columns: emit the inner blocks inline as siblings.
        out = []
        for child in kids:
            out += sanitize_block(child)
        return out

    if t == "image":
        return [{"payload": _paragraph(IMAGE_PLACEHOLDER), "children": []}]

    # Any other block that carries a URL (bookmark/embed/video/file/pdf/
    # link_preview) becomes a clickable paragraph so the link survives.
    url = _url_of(block, t)
    if url:
        return [{"payload": _paragraph(url, link=url), "children": []}]

    # Truly unsupported/unknown blocks are skipped (source link covers them).
    return []


def sanitize_tree(nodes: list) -> list:
    out = []
    for b in nodes:
        out += sanitize_block(b)
    return out


def fetch_block_tree(client, block_id: str) -> list:
    """Recursively fetch a block's children, stashing nested children under
    `_children` so `sanitize_tree` can reproduce the structure."""
    nodes = []
    for b in client.iter_block_children(block_id):
        if b.get("has_children"):
            b["_children"] = fetch_block_tree(client, b["id"])
        nodes.append(b)
    return nodes


def append_tree(client, parent_id: str, nodes: list) -> int:
    """Append sanitized nodes under parent_id, batching at Notion's 100-child
    limit and recursing to preserve nesting. Returns count of blocks created."""
    if not nodes:
        return 0
    created_blocks = []
    for i in range(0, len(nodes), 100):
        batch = nodes[i:i + 100]
        resp = client.append_block_children(parent_id, [n["payload"] for n in batch])
        created_blocks += resp.get("results", [])
    count = len(created_blocks)
    for node, created in zip(nodes, created_blocks):
        if node["children"]:
            count += append_tree(client, created["id"], node["children"])
    return count


def copy_page_body(client, source_page_id: str, dest_page_id: str) -> int:
    """Fetch the source page body and reproduce it under the destination page.
    Returns the number of blocks created."""
    tree = fetch_block_tree(client, source_page_id)
    return append_tree(client, dest_page_id, sanitize_tree(tree))
