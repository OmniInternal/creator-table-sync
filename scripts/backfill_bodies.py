"""One-time backfill for rows copied before the Script link + page-body feature.

For each existing destination row: set the `Script` URL (link to the source
row) if missing, and copy the source page body into the destination row IF the
destination row has no body yet. Idempotent — safe to re-run; a row that
already has a body is left untouched.

Usage (env vars same as the worker):
    python scripts/backfill_bodies.py [--limit N] [--dry-run]
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from creator_sync.blocks import copy_page_body
from creator_sync.config import load_config
from creator_sync.mapper import plain_text
from creator_sync.notion_client import NotionClient
from creator_sync.schema import ensure_schema


def _has_body(client, page_id: str) -> bool:
    return next(iter(client.iter_block_children(page_id)), None) is not None


def _script_url(props: dict):
    v = props.get("Script")
    return v.get("url") if v else None


def main() -> int:
    args = sys.argv[1:]
    dry = "--dry-run" in args
    limit = None
    if "--limit" in args:
        limit = int(args[args.index("--limit") + 1])

    config = load_config(os.environ)
    client = NotionClient(config.token, config.notion_version)

    # Ensure the Script column exists before we try to write it.
    added = ensure_schema(client, config.dest_db_id)
    if added:
        print(f"created destination columns: {added}")

    rows = list(client.iter_query(config.dest_db_id, None))
    if limit is not None:
        rows = rows[:limit]

    links_set = bodies_copied = skipped_body = errors = 0
    for row in rows:
        props = row["properties"]
        source_id = plain_text(props.get("Source ID", {}).get("rich_text", []))
        if not source_id:
            continue
        try:
            # 1) Script link (if the column is empty on this row)
            if not _script_url(props):
                src = client.retrieve_page(source_id)
                url = src.get("url")
                if url:
                    if not dry:
                        client.update_page(row["id"], {"Script": {"url": url}})
                    links_set += 1
            # 2) Body (only if the destination row has none yet)
            if _has_body(client, row["id"]):
                skipped_body += 1
            else:
                if dry:
                    bodies_copied += 1
                else:
                    n = copy_page_body(client, source_id, row["id"])
                    if n:
                        bodies_copied += 1
                    else:
                        skipped_body += 1
        except Exception as exc:  # noqa: BLE001 - report and continue
            errors += 1
            print(f"ERROR backfilling dest row {row['id']} (source {source_id}): {exc}")

    print(f"{'DRY-RUN ' if dry else ''}backfill complete: "
          f"links_set={links_set} bodies_copied={bodies_copied} "
          f"bodies_skipped(existing)={skipped_body} errors={errors} "
          f"over {len(rows)} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
