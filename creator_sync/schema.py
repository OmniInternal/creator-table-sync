from __future__ import annotations

DEST_COLUMNS = {
    "Name": "title",
    "Status": "select",
    "Creator Assigned": "multi_select",
    "Scriptwriter": "multi_select",
    "Content Link": "rich_text",
    "Product": "select",
    "Language": "multi_select",
    "Ready for Creator Date": "date",
    "Creator URL": "url",
    "Brief Link": "url",
    "Source Tracker": "select",
    "Copied At": "date",
    "Source ID": "rich_text",
}


def missing_columns(db: dict) -> dict:
    existing = set(db.get("properties", {}).keys())
    return {
        name: t for name, t in DEST_COLUMNS.items()
        if t != "title" and name not in existing
    }


def add_properties_payload(missing: dict) -> dict:
    return {name: {t: {}} for name, t in missing.items()}


def ensure_schema(client, dest_db_id: str) -> list:
    db = client.retrieve_database(dest_db_id)
    missing = missing_columns(db)
    if not missing:
        return []
    client.update_database(dest_db_id, add_properties_payload(missing))
    return sorted(missing.keys())
