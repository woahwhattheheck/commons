"""WRITING.md must link human write doors writing / WRITE-NOW / builds."""
from pathlib import Path

TEXT = (Path(__file__).resolve().parent / "WRITING.md").read_text(encoding="utf-8")


def test_writing_md_human_write_doors():
    assert "writing.html" in TEXT
    assert "WRITE-NOW.md" in TEXT
    assert "builds.html" in TEXT
    assert "failed.html" not in TEXT
