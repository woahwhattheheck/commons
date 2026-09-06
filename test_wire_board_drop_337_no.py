"""board.html closing note must not treat 337 as law."""
from pathlib import Path
import re

HTML = (Path(__file__).resolve().parent / "board.html").read_text(encoding="utf-8")


def test_board_html_closing_note_no_fire_337():
    m = re.search(r'<p class="note">from= is a claim\..*?</p>', HTML, re.S)
    assert m, "closing from= note missing"
    note = m.group(0)
    assert "Do not fire 337" not in note
    assert "Do not smash commons.mno" in note
