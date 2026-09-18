"""boards.html must list builds.html attribution ledger."""
from pathlib import Path

HTML = (Path(__file__).resolve().parent / "boards.html").read_text(encoding="utf-8")


def test_boards_lists_builds_html():
    assert 'href="./builds.html"' in HTML
    assert "attribution" in HTML.lower() or "BUILD_RECEIPT" in HTML or "BUILD_REQUEST" in HTML
