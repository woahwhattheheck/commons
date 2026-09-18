"""builds.html must door vanished BUILD receipts to failed.html."""
from pathlib import Path

HTML = (Path(__file__).resolve().parent / "builds.html").read_text(encoding="utf-8")


def test_builds_html_points_failed_visibility():
    assert "failed.html" in HTML
    assert "WINDOW_MISS" in HTML or "durable gaps" in HTML
    assert "BUILD_RECEIPT" in HTML
    # stay off saturated Contents-verify / head.html remint class
    assert "head.html" not in HTML
    assert "contents/p/" not in HTML
