"""post.html must teach Contents verify after issue file (no head.html remint)."""
from pathlib import Path

TEXT = (Path(__file__).resolve().parent / "post.html").read_text(encoding="utf-8")


def test_post_html_contents_verify_no_head_html():
    assert "api.github.com/repos/woahwhattheheck/commons/contents/p/" in TEXT
    assert "failed.html" in TEXT
    assert "ground/CURL.md" in TEXT or "./ground/CURL.md" in TEXT
    assert "head.html" not in TEXT
    assert "Issue filed" in TEXT or "durable board post" in TEXT
