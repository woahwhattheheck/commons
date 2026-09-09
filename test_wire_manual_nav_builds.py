from pathlib import Path
TEXT = (Path(__file__).resolve().parent / "manual.html").read_text(encoding="utf-8")

def test_manual_nav_cites_builds():
    assert 'href="./builds.html"' in TEXT
    assert 'href="./wire.html"' in TEXT
