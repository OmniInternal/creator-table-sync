# creator-table-sync

Copies rows that reach `Status = "Ready For Creator"` from several Notion
tracker databases into one freely-editable destination table. One-way,
copy-once: a source row is copied a single time and never touched again, so the
destination can be edited freely and extra columns added without interference.

## Configuration

All configuration is via environment variables (never commit real values):

| Variable | Meaning |
|---|---|
| `NOTION_TOKEN` | Notion internal integration token |
| `DEST_DB_ID` | Destination database id |
| `SRC_*_DB_ID` | Each source database id |
| `TRIGGER_STATUS` | Status value that triggers a copy (default `Ready For Creator`) |

Copy `.env.example` to `.env` for local runs. The integration must be connected
to every source database and the destination.

## Run

```bash
pip install -r requirements-dev.txt
python -m pytest            # tests
python -m creator_sync.main # one sync pass (needs env vars)
```

Scheduled every 20 minutes via GitHub Actions (`.github/workflows/sync.yml`).
