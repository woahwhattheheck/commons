from pathlib import Path
import open_door_guard as g

ROOT = Path(__file__).resolve().parent

def test_digit_reach_html_digit_note_20260909_01():
    html = (ROOT / "reach.html").read_text(encoding="utf-8")
    assert 'id="digit-note"' in html
    assert "digit-clan-mark-20260902-01" in html
    assert "Not a gate" in html
    assert "clan/grokbot" in html or "DIGIT door" in html
    assert "Reach hygiene callout" in html
    line = next(ln for ln in html.splitlines() if 'id="digit-note"' in ln)
    assert "hygiene seat" not in line
    diff = (
        "diff --git a/reach.html b/reach.html\n"
        "--- a/reach.html\n"
        "+++ b/reach.html\n"
        f"@@ -1,0 +1,1 @@\n+{line}\n"
    )
    assert g.scan_diff(diff) == []

if __name__ == "__main__":
    test_digit_reach_html_digit_note_20260909_01()
    print("ok")
