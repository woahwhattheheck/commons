"""ground/LAND.md verify step must name Contents how-to (no head.html remint)."""
from pathlib import Path

TEXT = (Path(__file__).resolve().parent / "ground/LAND.md").read_text(encoding="utf-8")


def test_land_md_contents_verify_how():
    assert "api.github.com/repos/woahwhattheheck/commons/contents/p/" in TEXT
    assert "CURL.md" in TEXT
    assert "failed.html" in TEXT
    assert "head.html" not in TEXT
    assert "ntfy 200" in TEXT
