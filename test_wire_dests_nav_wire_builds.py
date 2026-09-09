from pathlib import Path
TEXT = (Path(__file__).resolve().parent / "dests.html").read_text(encoding="utf-8")

def test_dests_nav_cites_wire_and_builds():
    assert 'href="./wire.html"' in TEXT
    assert 'href="./builds.html"' in TEXT
