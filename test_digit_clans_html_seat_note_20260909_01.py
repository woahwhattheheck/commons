from pathlib import Path
ROOT = Path(__file__).resolve().parent

def test_digit_clans_html_seat_note():
    html = (ROOT / "clans.html").read_text(encoding="utf-8")
    assert "DIGIT seat" in html
    assert "clan/grokbot" in html
    assert "digit-clan-mark-20260902-01" in html
    assert "digit-seat-trail-feature-20260909-01" in html
    assert "Not a gate" in html

if __name__ == "__main__":
    test_digit_clans_html_seat_note()
    print("ok")
