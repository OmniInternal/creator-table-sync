from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional

NOTION_VERSION = "2022-06-28"
DEFAULT_TRIGGER = "Ready For Creator"

# Common field map shared by the four "select"-status trackers.
_COMMON_FIELD_MAP = {
    "Creative Name": "Name",
    "Status": "Status",
    "Creator Assigned": "Creator Assigned",
    "Scriptwriter": "Scriptwriter",
    "Content Link": "Content Link",
    "Product": "Product",
    "Language": "Language",
    "Ready for Creator Date": "Ready for Creator Date",
    "Creator URL": "Creator URL",
}


@dataclass(frozen=True)
class SourceConfig:
    key: str
    label: str
    db_id: str
    status_kind: str  # "status" or "select"
    field_map: dict
    language_default: Optional[str] = None


@dataclass(frozen=True)
class Config:
    token: str
    notion_version: str
    dest_db_id: str
    trigger_status: str
    sources: list


def _spanish_field_map() -> dict:
    # Spanish tracker has no Scriptwriter and no Language property.
    fm = dict(_COMMON_FIELD_MAP)
    fm.pop("Scriptwriter", None)
    fm.pop("Language", None)
    return fm


def load_config(env: Mapping[str, str]) -> Config:
    token = env["NOTION_TOKEN"]
    dest = env["DEST_DB_ID"]
    trigger = env.get("TRIGGER_STATUS", DEFAULT_TRIGGER)

    sources = [
        SourceConfig("actor_testing", "Actor Testing", env["SRC_ACTOR_TESTING_DB_ID"],
                     "select", dict(_COMMON_FIELD_MAP)),
        SourceConfig("dr_ugc", "DR-UGC", env["SRC_DR_UGC_DB_ID"],
                     "select", dict(_COMMON_FIELD_MAP)),
        SourceConfig("spanish", "Spanish", env["SRC_SPANISH_DB_ID"],
                     "select", _spanish_field_map(), language_default="Spanish"),
        SourceConfig("micro", "Micro-Influencer", env["SRC_MICRO_DB_ID"],
                     "select", dict(_COMMON_FIELD_MAP)),
    ]
    return Config(token, NOTION_VERSION, dest, trigger, sources)
