from pathlib import Path
TEXT = (Path(__file__).resolve().parent / "books.html").read_text(encoding="utf-8")

def test_books_nav_cites_wire_and_builds():
    assert 'href="./wire.html"' in TEXT
    assert 'href="./builds.html"' in TEXT
