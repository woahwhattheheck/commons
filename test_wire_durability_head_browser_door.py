"""ground/DURABILITY.md must land Pages-lag readers on head.html."""
from pathlib import Path

TEXT = (Path(__file__).resolve().parent / "ground/DURABILITY.md").read_text(encoding="utf-8")


def test_durability_points_at_head_html_browser_door():
    assert "contents API" in TEXT or "Contents API" in TEXT or "contents API" in TEXT.lower()
    assert "head.html" in TEXT
    assert "head.html?path=" in TEXT
    assert "HEAD.md" in TEXT
