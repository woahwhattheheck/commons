from pathlib import Path
TEXT = (Path(__file__).resolve().parent / "boards.html").read_text(encoding="utf-8")

def test_boards_lists_wire_html():
    assert 'href="./wire.html"' in TEXT

def test_boards_lists_post_http_restored():
    assert 'href="./post-http.html"' in TEXT
