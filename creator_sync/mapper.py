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
        if isinstance(value, list):
            names = value
        elif isinstance(value, str):
            names = [v.strip() for v in value.split(",")]
        elif value:
            names = [value]
        else:
            names = []
        names = [n for n in names if n]
        return {"multi_select": [{"name": n} for n in names]} if names else None
    if col in TEXT_COLS or col == "Source ID":
        return {"rich_text": [{"text": {"content": value}}]} if value else None
    if col in URL_COLS:
        return {"url": value} if value else None
    if col in DATE_COLS or col == "Copied At":
        return {"date": {"start": value}} if value else None
    return None


# Source columns get RENAMED in Notion (DR-UGC 2026-10: `Creative Name` → `Title`,
# `Creator Assigned` → `Creator` → `Style/Creator`; Spanish: `Creator / Style`).
# A renamed column used to be skipped SILENTLY — the copy arrived with no name or
# creator. Each configured source column now also answers to its known aliases,
# and the destination `Name` always falls back to the page's TITLE property,
# whatever it is called (every Notion database has exactly one).
SOURCE_ALIASES = {
    "Creator Assigned": ["Style/Creator", "Creator / Style", "Creator"],
}


def resolve_source_column(props: dict, src_name: str, dest_col: str) -> Optional[str]:
    """The source property that holds `src_name` today, or None."""
    for name in [src_name, *SOURCE_ALIASES.get(src_name, [])]:
        if name in props:
            return name
    if dest_col == "Name":
        for name, prop in props.items():
            if prop.get("type") == "title":
                return name
    return None


def build_properties(page: dict, source: SourceConfig, copied_at_iso: str) -> dict:
    props = page.get("properties", {})
    out: dict = {}

    for src_name, dest_col in source.field_map.items():
        col = resolve_source_column(props, src_name, dest_col)
        if col is None:
            continue
        value = _read_source_value(props[col])
        shape = _write_shape(dest_col, value)
        if shape is not None:
            out[dest_col] = shape

    # Spanish (or any source) language default
    if source.language_default and "Language" not in out:
        out["Language"] = {"multi_select": [{"name": source.language_default}]}

    # Clickable link back to the original source row (the full script lives in
    # its page body). This is a plain URL bookmark, not a live Notion relation,
    # so the destination stays disconnected.
    if page.get("url"):
        out["Script"] = {"url": page["url"]}

    # Always-present housekeeping
    out["Source Tracker"] = {"select": {"name": source.label}}
    out["Copied At"] = {"date": {"start": copied_at_iso}}
    out["Source ID"] = {"rich_text": [{"text": {"content": page["id"]}}]}
    return out
