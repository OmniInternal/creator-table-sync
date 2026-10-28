from __future__ import annotations

import os
import sys

# Allow running as `python scripts/dry_run.py` from the repo root: ensure the
# project root (this file's parent's parent) is importable so `creator_sync`
# resolves without needing PYTHONPATH set.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from creator_sync.config import load_config
from creator_sync.dedup import existing_source_ids
from creator_sync.mapper import build_properties, plain_text
from creator_sync.notion_client import NotionClient
from creator_sync.schema import missing_columns
from creator_sync.sync import source_drift, status_filter

# READ-ONLY. Reports exactly what a real run would do — per source: schema drift,
# rows at the trigger status, how many are NEW (not yet copied), and a sample of
# the NEW rows as they would be written — plus whether the destination would need
# new columns or new `Creator Assigned` options (Notion caps a multi_select at 100).


def main() -> int:
    config = load_config(os.environ)
    client = NotionClient(config.token, config.notion_version)
    dest = client.retrieve_database(config.dest_db_id)
    print(f"destination: missing columns that a run would ADD: {sorted(missing_columns(dest))}")
    dest_creator = dest.get("properties", {}).get("Creator Assigned", {})
    have_opts = {o["name"] for o in (dest_creator.get("multi_select") or {}).get("options", [])}
    print(f"destination: Creator Assigned has {len(have_opts)} options (Notion cap 100)")
    existing = existing_source_ids(client, config.dest_db_id)
    print(f"destination: {len(existing)} rows already copied")
    new_creators: set = set()
    total_new = 0
    for source in config.sources:
        schema = client.retrieve_database(source.db_id).get("properties", {})
        drift = source_drift(source, schema)
        rows = list(client.iter_query(source.db_id, status_filter(source, config.trigger_status)))
        new = [r for r in rows if r["id"] not in existing]
        total_new += len(new)
        print(f"{source.key}: drift={drift or 'none'} at '{config.trigger_status}'={len(rows)} NEW={len(new)}")
        nameless = 0
        for r in new:
            p = build_properties(r, source, "DRY-RUN")
            if "Name" not in p:
                nameless += 1
            for o in p.get("Creator Assigned", {}).get("multi_select", []):
                if o["name"] not in have_opts:
                    new_creators.add(o["name"])
        if nameless:
            print(f"  {nameless} NEW row(s) have no title and would be refused")
        for r in new[:5]:
            p = build_properties(r, source, "DRY-RUN")
            name = plain_text(p.get("Name", {}).get("title", []))
            creators = [o["name"] for o in p.get("Creator Assigned", {}).get("multi_select", [])]
            print(f"  sample: {name[:70]!r} creator={creators} cols={sorted(p.keys())}")
    print(f"TOTAL NEW rows a real run would create: {total_new}")
    print(f"Creator Assigned options a real run would ADD: {len(new_creators)} → total {len(have_opts) + len(new_creators)} (cap 100)")
    print("DRY RUN complete — no writes performed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
