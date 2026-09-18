from pathlib import Path
TEXT = (Path(__file__).resolve().parent / "ground/PICK.md").read_text(encoding="utf-8")

def test_pick_md_cites_curl_md():
    assert "CURL.md" in TEXT
    assert "curl to ntfy" in TEXT
