import pytest
from creator_sync.config import load_config

BASE_ENV = {
    "NOTION_TOKEN": "ntn_test",
    "DEST_DB_ID": "dest123",
    "SRC_INFLUENCER_DB_ID": "inf",
    "SRC_ACTOR_TESTING_DB_ID": "act",
    "SRC_DR_UGC_DB_ID": "dr",
    "SRC_SPANISH_DB_ID": "sp",
    "SRC_MICRO_DB_ID": "mic",
}


def test_load_config_reads_token_and_dest():
    cfg = load_config(BASE_ENV)
    assert cfg.token == "ntn_test"
    assert cfg.dest_db_id == "dest123"
    assert cfg.notion_version == "2022-06-28"
    assert cfg.trigger_status == "Ready For Creator"


def test_trigger_status_override():
    cfg = load_config({**BASE_ENV, "TRIGGER_STATUS": "Ready For X"})
    assert cfg.trigger_status == "Ready For X"


def test_sources_wired_with_ids_and_kinds():
    cfg = load_config(BASE_ENV)
    by_key = {s.key: s for s in cfg.sources}
    assert set(by_key) == {"influencer", "actor_testing", "dr_ugc", "spanish", "micro"}
    assert by_key["influencer"].db_id == "inf"
    assert by_key["influencer"].status_kind == "status"
    assert by_key["actor_testing"].status_kind == "select"
    assert by_key["spanish"].language_default == "Spanish"
    assert by_key["influencer"].language_default is None


def test_influencer_field_map_uses_creator_at_and_writer():
    cfg = load_config(BASE_ENV)
    inf = next(s for s in cfg.sources if s.key == "influencer")
    assert inf.field_map["Creative Name"] == "Name"
    assert inf.field_map["Creator @"] == "Creator Assigned"
    assert inf.field_map["Writer"] == "Scriptwriter"
    assert inf.field_map["Brief Link"] == "Brief Link"
    assert "Ready for Creator Date" not in inf.field_map


def test_actor_field_map_uses_creator_assigned_and_scriptwriter():
    cfg = load_config(BASE_ENV)
    act = next(s for s in cfg.sources if s.key == "actor_testing")
    assert act.field_map["Creator Assigned"] == "Creator Assigned"
    assert act.field_map["Scriptwriter"] == "Scriptwriter"
    assert act.field_map["Ready for Creator Date"] == "Ready for Creator Date"
    assert act.field_map["Creator URL"] == "Creator URL"


def test_missing_required_env_raises():
    with pytest.raises(KeyError):
        load_config({"DEST_DB_ID": "x"})
