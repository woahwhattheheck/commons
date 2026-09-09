from pathlib import Path
TEXT = (Path(__file__).resolve().parent / "avatars.html").read_text(encoding="utf-8")

def test_avatars_nav_cites_wire_and_builds():
    assert 'href="./wire.html"' in TEXT
    assert 'href="./builds.html"' in TEXT
