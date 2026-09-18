"""writing.html must not carry ritual 337 NO (not Bryce law)."""
from pathlib import Path

HTML = (Path(__file__).resolve().parent / "writing.html").read_text(encoding="utf-8")


def test_writing_html_no_ritual_337():
    assert "337 NO" not in HTML
    assert "337" not in HTML
