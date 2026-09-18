from pathlib import Path
ROOT = Path(__file__).resolve().parent

def test_digit_grounding_card():
    html = (ROOT / "grounding.html").read_text(encoding="utf-8")
    assert "DIGIT seat" in html
    assert "digit-boards-trail-20260909-01" in html
    assert "digit-names-mark-20260909-01" in html
