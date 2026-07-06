from scripts.check_no_secrets import find_violations

def fake_reader(mapping):
    return lambda p: mapping[p]

def test_flags_token():
    reader = fake_reader({"a.py": 'x = "ntn_ABC123"'})
    v = find_violations(["a.py"], reader)
    assert v and v[0][0] == "a.py"

def test_flags_notion_url():
    reader = fake_reader({"b.md": "see https://app.notion.com/p/x"})
    assert find_violations(["b.md"], reader)

def test_flags_bare_32_hex_id():
    reader = fake_reader({"c.py": "id = 2cbb4ad216d0801d883cdd6af11ea2fc"})
    assert find_violations(["c.py"], reader)

def test_clean_file_passes():
    reader = fake_reader({"d.py": 'token = os.environ["NOTION_TOKEN"]'})
    assert find_violations(["d.py"], reader) == []
