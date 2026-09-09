"""authorship.html must not carry ritual 337 NO."""
from pathlib import Path

HTML = (Path(__file__).resolve().parent / "authorship.html").read_text(encoding="utf-8")


def test_authorship_html_no_ritual_337():
    assert "337 NO" not in HTML
    assert "337" not in HTML
