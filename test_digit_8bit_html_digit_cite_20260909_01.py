from pathlib import Path
ROOT = Path(__file__).resolve().parent

def test_digit_8bit_html_digit_cite():
    html = (ROOT / "8bit.html").read_text(encoding="utf-8")
    assert 'id="digit-cite"' in html
    assert "digit-8bit-20260819-01" in html
    assert "clan/grokbot" in html
    assert "not a gate" in html
    assert "goat-8bit-20260819-01" in html

if __name__ == "__main__":
    test_digit_8bit_html_digit_cite()
    print("ok")
