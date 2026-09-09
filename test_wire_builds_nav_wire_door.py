from pathlib import Path
TEXT = (Path(__file__).resolve().parent / "builds.html").read_text(encoding="utf-8")

def test_builds_nav_cites_wire():
    assert 'href="./wire.html"' in TEXT
