from scripts.check_no_secrets import find_violations

def fake_reader(mapping):
    return lambda p: mapping[p]

def test_flags_token():
    reader = fake_reader({"a.py": 'x = "ntn_' + "a" * 40 + '"'})
    v = find_violations(["a.py"], reader)
    assert v and v[0][0] == "a.py"

def test_ignores_short_dummy_token():
    reader = fake_reader({"a.py": 'NotionClient("ntn_x")'})
    assert find_violations(["a.py"], reader) == []

def test_flags_notion_page_url():
    reader = fake_reader({"b.md": "https://app.notion.com/p/x"})
    assert find_violations(["b.md"], reader)

def test_ignores_api_host():
    reader = fake_reader({"b.py": 'API = "https://api.notion.com/v1"'})
    assert find_violations(["b.py"], reader) == []

def test_flags_bare_32_hex_id():
    reader = fake_reader({"c.py": "id = 0123456789abcdef0123456789abcdef"})
    assert find_violations(["c.py"], reader)

def test_clean_file_passes():
    reader = fake_reader({"d.py": 'token = os.environ["NOTION_TOKEN"]'})
    assert find_violations(["d.py"], reader) == []

def test_allowlist_is_exact_not_suffix():
    reader = fake_reader({"evil/tests/test_secret_guard.py": 'x = "ntn_' + "a" * 40 + '"'})
    v = find_violations(["evil/tests/test_secret_guard.py"], reader)
    assert v
