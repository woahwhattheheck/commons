from pathlib import Path
TEXT = (Path(__file__).resolve().parent / "ENTRY.md").read_text(encoding="utf-8")

def test_entry_md_cites_curl_md():
    assert "CURL.md" in TEXT
    assert "curl is the same road" in TEXT
