"""boards.html must not treat 337 as law (void ritual)."""
from pathlib import Path

HTML = (Path(__file__).resolve().parent / "boards.html").read_text(encoding="utf-8")


def test_boards_html_no_fire_337_ritual():
    assert "fire 337" not in HTML
    assert "Do not fire 337" not in HTML
    assert "Do not smash commons.mno" in HTML
