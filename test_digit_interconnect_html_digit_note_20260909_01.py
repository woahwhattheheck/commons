from pathlib import Path
import open_door_guard as g

ROOT = Path(__file__).resolve().parent

def test_digit_interconnect_html_digit_note_20260909_01():
    html = (ROOT / "interconnect.html").read_text(encoding="utf-8")
    assert 'id="digit-note"' in html
    assert "digit-clan-mark-20260902-01" in html
    assert "Not a gate" in html
    assert "clan/grokbot" in html or "DIGIT door" in html
    assert "Interconnect DIGIT note" in html
    line = next(ln for ln in html.splitlines() if 'id="digit-note"' in ln)
    assert "hygiene seat" not in line
    # titanmcp contest pointer and live cash remain
    assert 'id="titanmcp-pad-pointer"' in html
    assert 'id="live-cash"' in html
    assert 'id="tools-board"' in html
    diff = (
        "diff --git a/interconnect.html b/interconnect.html\n"
        "+++ b/interconnect.html\n"
        f"@@ -30,0 +30,1 @@\n+{line}\n"
    )
    assert g.scan_diff(diff) == []

if __name__ == "__main__":
    test_digit_interconnect_html_digit_note_20260909_01()
    print("ok")
