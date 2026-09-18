from pathlib import Path
ROOT = Path(__file__).resolve().parent

def test_digit_commerce_html_digit_note_20260909_01():
    html = (ROOT / "commerce.html").read_text(encoding="utf-8")
    assert 'id="digit-note"' in html
    assert "digit-clan-mark-20260902-01" in html
    assert "Not a gate" in html
    assert "clan/grokbot" in html
    assert "Shared commerce DIGIT note." in html

if __name__ == "__main__":
    test_digit_commerce_html_digit_note_20260909_01()
    print("ok")
