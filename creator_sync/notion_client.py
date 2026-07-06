from __future__ import annotations

import time
from typing import Iterator, Optional

API = "https://api.notion.com/v1"
MAX_RETRIES = 5


class NotionClient:
    def __init__(self, token: str, version: str, session=None, sleep=time.sleep):
        if session is None:
            import requests
            session = requests.Session()
        self._session = session
        self._sleep = sleep
        self.last_headers = {
            "Authorization": f"Bearer {token}",
            "Notion-Version": version,
            "Content-Type": "application/json",
        }

    def _request(self, method: str, path: str, json: Optional[dict] = None) -> dict:
        url = f"{API}{path}"
        for attempt in range(MAX_RETRIES):
            resp = self._session.request(method, url, headers=self.last_headers, json=json)
            if resp.status_code == 429 or resp.status_code >= 500:
                wait = float(resp.headers.get("Retry-After", "1"))
                self._sleep(wait)
                continue
            data = resp.json()
            if resp.status_code >= 400:
                raise RuntimeError(f"Notion API {resp.status_code}: {data}")
            return data
        raise RuntimeError(f"Notion API retries exhausted for {method} {path}")

    def retrieve_database(self, db_id: str) -> dict:
        return self._request("GET", f"/databases/{db_id}")

    def update_database(self, db_id: str, properties: dict) -> dict:
        return self._request("PATCH", f"/databases/{db_id}", json={"properties": properties})

    def query_database(self, db_id: str, payload: dict) -> dict:
        return self._request("POST", f"/databases/{db_id}/query", json=payload)

    def iter_query(self, db_id: str, filter: Optional[dict]) -> Iterator[dict]:
        cursor = None
        while True:
            payload: dict = {}
            if filter:
                payload["filter"] = filter
            if cursor:
                payload["start_cursor"] = cursor
            data = self.query_database(db_id, payload)
            for page in data.get("results", []):
                yield page
            if not data.get("has_more"):
                return
            cursor = data.get("next_cursor")

    def create_page(self, parent_db_id: str, properties: dict) -> dict:
        return self._request(
            "POST", "/pages",
            json={"parent": {"database_id": parent_db_id}, "properties": properties},
        )
