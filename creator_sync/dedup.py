from __future__ import annotations

from .mapper import plain_text


def existing_source_ids(client, dest_db_id: str) -> set:
    ids = set()
    for page in client.iter_query(dest_db_id, None):
        prop = page.get("properties", {}).get("Source ID", {})
        val = plain_text(prop.get("rich_text", []))
        if val:
            ids.add(val)
    return ids


def is_new(page_id: str, existing: set) -> bool:
    return page_id not in existing
