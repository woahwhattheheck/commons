from pathlib import Path
HTML = (Path(__file__).resolve().parent / "boards.html").read_text(encoding="utf-8")

def test_boards_lists_post_http():
    assert 'href="./post-http.html"' in HTML
