from __future__ import annotations

from .blocks import copy_page_body
from .config import Config, SourceConfig
from .dedup import existing_source_ids, is_new
from .mapper import build_properties
from .schema import ensure_schema


def status_filter(source: SourceConfig, trigger: str) -> dict:
    kind = "status" if source.status_kind == "status" else "select"
    return {"property": "Status", kind: {"equals": trigger}}


def sync(config: Config, client, copied_at_iso: str, logger=print) -> dict:
    added = ensure_schema(client, config.dest_db_id)
    if added:
        logger(f"created destination columns: {added}")

    existing = existing_source_ids(client, config.dest_db_id)
    logger(f"destination already has {len(existing)} copied rows")

    created = 0
    skipped = 0
    errors = 0
    per_source: dict = {}

    for source in config.sources:
        src_created = 0
        flt = status_filter(source, config.trigger_status)
        for page in client.iter_query(source.db_id, flt):
            pid = page["id"]
            if not is_new(pid, existing):
                skipped += 1
                continue
            try:
                props = build_properties(page, source, copied_at_iso)
                new_page = client.create_page(config.dest_db_id, props)
            except Exception as exc:
                errors += 1
                logger(f"ERROR copying {source.key} page {pid}: {exc}")
                continue
            # Best-effort copy of the page body (the actual script). A failure
            # here does not fail the row — the Script link column still points
            # to the source page.
            try:
                copy_page_body(client, pid, new_page["id"])
            except Exception as exc:
                logger(f"WARN body copy failed for {source.key} page {pid}: {exc}")
            existing.add(pid)
            created += 1
            src_created += 1
        per_source[source.key] = src_created
        logger(f"{source.key}: created {src_created}")

    return {"created": created, "skipped": skipped, "errors": errors, "per_source": per_source}
