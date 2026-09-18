from pathlib import Path
import open_door_guard as g

ROOT = Path(__file__).resolve().parent

def test_digit_clans_html_seat_note():
    html = (ROOT / "clans.html").read_text(encoding="utf-8")
    assert "DIGIT seat" in html
    assert "clan/grokbot" in html
    assert "digit-clan-mark-20260902-01" in html
    assert "digit-seat-trail-feature-20260909-01" in html
    assert "Not a gate" in html
    line = next(ln for ln in html.splitlines() if "DIGIT seat" in ln and "clan/grokbot" in ln)
    diff = (
        "diff --git a/clans.html b/clans.html\n"
        "+++ b/clans.html\n"
        f"@@ -88,0 +88,1 @@\n+{line}\n"
    )
    assert g.scan_diff(diff) == []

if __name__ == "__main__":
    test_digit_clans_html_seat_note()
    print("ok")
