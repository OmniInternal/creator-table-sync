from __future__ import annotations

import os
from datetime import datetime, timezone

from .config import load_config
from .notion_client import NotionClient
from .sync import sync


def main() -> int:
    config = load_config(os.environ)
    client = NotionClient(config.token, config.notion_version)
    copied_at = datetime.now(timezone.utc).date().isoformat()
    summary = sync(config, client, copied_at)
    print(f"SUMMARY: {summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
