from pathlib import Path
TEXT = (Path(__file__).resolve().parent / "START.md").read_text(encoding="utf-8")

def test_start_cites_builds_html_door():
    assert "builds.html" in TEXT
    assert "builds.json" in TEXT
