"""ground/WRITE-NOW.md must list builds.html + reply.html doors."""
from pathlib import Path

TEXT = (Path(__file__).resolve().parent / "ground/WRITE-NOW.md").read_text(encoding="utf-8")


def test_write_now_lists_builds_and_reply():
    assert "builds.html" in TEXT
    assert "reply.html" in TEXT
    assert "failed.html" not in TEXT  # stay off →failed remint class
