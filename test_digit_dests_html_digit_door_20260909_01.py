from pathlib import Path
ROOT = Path(__file__).resolve().parent

def test_digit_dests_html_digit_door():
    html = (ROOT / "dests.html").read_text(encoding="utf-8")
    assert 'id="digit-door"' in html
    assert "by/DIGIT.html" in html
    assert "to/DIGIT.html" in html
    assert "digit-clan-mark-20260902-01" in html
    assert "Not a gate" in html

if __name__ == "__main__":
    test_digit_dests_html_digit_door()
    print("ok")
