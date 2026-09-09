from pathlib import Path
TEXT = (Path(__file__).resolve().parent / "wire.html").read_text(encoding="utf-8")

def test_wire_nav_cites_builds():
    assert 'href="./builds.html"' in TEXT
