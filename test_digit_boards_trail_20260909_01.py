from pathlib import Path
ROOT = Path(__file__).resolve().parent

def test_digit_boards_trail():
    html = (ROOT / "boards.html").read_text(encoding="utf-8")
    assert "DIGIT seat" in html
    assert "digit-names-mark-20260909-01" in html
    assert "DIGIT BUILD" in html
