from pathlib import Path
TEXT = (Path(__file__).resolve().parent / "wire.html").read_text(encoding="utf-8")

def test_wire_nav_cites_builds():
    assert 'href="./builds.html"' in TEXT
    nav = next(line for line in TEXT.splitlines() if 'class="nav"' in line)
    assert 'href="./builds.html"' in nav
