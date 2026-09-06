"""ground/CURL.md must teach CLI Contents GET verify (not browser head.html)."""
from pathlib import Path

TEXT = (Path(__file__).resolve().parent / "ground/CURL.md").read_text(encoding="utf-8")


def test_curl_md_has_cli_contents_verify_not_head_html():
    assert "api.github.com/repos/woahwhattheheck/commons/contents/p/" in TEXT
    assert "git ls-remote" in TEXT
    assert "head.html" not in TEXT
    assert "ntfy 200 is mail" in TEXT or "ntfy 200 is mail" in TEXT.lower() or "ntfy 200" in TEXT
