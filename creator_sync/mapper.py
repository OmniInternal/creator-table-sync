from __future__ import annotations

from typing import Optional

from .config import SourceConfig

# canonical destination column -> write type
SELECT_COLS = {"Status", "Product"}
MULTI_COLS = {"Creator Assigned", "Scriptwriter", "Language"}
URL_COLS = {"Creator URL", "Brief Link"}
DATE_COLS = {"Ready for Creator Date"}
TEXT_COLS = {"Content Link"}


def plain_text(rich: list) -> str:
    return "".join(r.get("plain_text", r.get("text", {}).get("content", "")) for r in (rich or []))


def _read_source_value(prop: dict):
    """Return a normalized python value from any source property dict."""
    t = prop.get("type")
    if t == "title":
        return plain_text(prop.get("title", []))
    if t == "rich_text":
        return plain_text(prop.get("rich_text", []))
    if t == "select":
        sel = prop.get("select")
        return sel["name"] if sel else None
    if t == "status":
        st = prop.get("status")
        return st["name"] if st else None
    if t == "multi_select":
        return [o["name"] for o in prop.get("multi_select", [])]
    if t == "url":
        return prop.get("url")
    if t == "date":
        d = prop.get("date")
        return d.get("start") if d else None
    return None


def _write_shape(col: str, value) -> Optional[dict]:
    """Build the destination write payload for one curated column, or None if empty."""
    if col == "Name":
        return {"title": [{"text": {"content": value}}]} if value else None
    if col in SELECT_COLS or col == "Source Tracker":
        return {"select": {"name": value}} if value else None
    if col in MULTI_COLS:
        names = value if isinstance(value, list) else ([value] if value else [])
        names = [n for n in names if n]
        return {"multi_select": [{"name": n} for n in names]} if names else None
    if col in TEXT_COLS or col == "Source ID":
        return {"rich_text": [{"text": {"content": value}}]} if value else None
    if col in URL_COLS:
        return {"url": value} if value else None
    if col in DATE_COLS or col == "Copied At":
        return {"date": {"start": value}} if value else None
    return None


def build_properties(page: dict, source: SourceConfig, copied_at_iso: str) -> dict:
    props = page.get("properties", {})
    out: dict = {}

    for src_name, dest_col in source.field_map.items():
        if src_name not in props:
            continue
        value = _read_source_value(props[src_name])
        shape = _write_shape(dest_col, value)
        if shape is not None:
            out[dest_col] = shape

    # Spanish (or any source) language default
    if source.language_default and "Language" not in out:
        out["Language"] = {"multi_select": [{"name": source.language_default}]}

    # Always-present housekeeping
    out["Source Tracker"] = {"select": {"name": source.label}}
    out["Copied At"] = {"date": {"start": copied_at_iso}}
    out["Source ID"] = {"rich_text": [{"text": {"content": page["id"]}}]}
    return out
