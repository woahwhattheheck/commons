"""DROP.md builds/** refuse row must link builds.html."""
from pathlib import Path

TEXT = (Path(__file__).resolve().parent / "DROP.md").read_text(encoding="utf-8")


def test_drop_md_builds_row_links_builds_html():
    assert "builds.html" in TEXT
    assert "`builds/**`" in TEXT
    assert "failed.html" not in TEXT
