from pathlib import Path
import open_door_guard as g

ROOT = Path(__file__).resolve().parent

def test_digit_offer_html_digit_note_20260909_01():
    html = (ROOT / "offer.html").read_text(encoding="utf-8")
    assert 'id="digit-note"' in html
    assert "digit-clan-mark-20260902-01" in html
    assert "Not a gate" in html
    assert "clan/grokbot" in html or "DIGIT door" in html
    line = next(ln for ln in html.splitlines() if 'id="digit-note"' in ln)
    assert "hygiene seat" not in line
    diff = (
        "diff --git a/offer.html b/offer.html\n"
        "+++ b/offer.html\n"
        f"@@ -19,0 +19,1 @@\n+{line}\n"
    )
    assert g.scan_diff(diff) == []

if __name__ == "__main__":
    test_digit_offer_html_digit_note_20260909_01()
    print("ok")
