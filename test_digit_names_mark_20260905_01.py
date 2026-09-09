from pathlib import Path
ROOT = Path(__file__).resolve().parent

def test_digit_names_row():
    html = (ROOT / "names.html").read_text(encoding="utf-8")
    assert "<b>DIGIT</b>" in html
    assert "clan/grokbot" in html.lower() or "Clan grokbot" in html
    assert "digit-clan-mark-20260902-01" in html
