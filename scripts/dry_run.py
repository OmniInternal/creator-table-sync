from __future__ import annotations

import os
import sys

# Allow running as `python scripts/dry_run.py` from the repo root: ensure the
# project root (this file's parent's parent) is importable so `creator_sync`
# resolves without needing PYTHONPATH set.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from creator_sync.config import load_config
from creator_sync.mapper import build_properties
from creator_sync.notion_client import NotionClient
from creator_sync.sync import status_filter


def main() -> int:
    config = load_config(os.environ)
    client = NotionClient(config.token, config.notion_version)
    for source in config.sources:
        flt = status_filter(source, config.trigger_status)
        rows = list(client.iter_query(source.db_id, flt))
        print(f"{source.key}: {len(rows)} row(s) at '{config.trigger_status}'")
        if rows:
            sample = build_properties(rows[0], source, "DRY-RUN")
            print(f"  sample columns: {sorted(sample.keys())}")
    print("DRY RUN complete — no writes performed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
