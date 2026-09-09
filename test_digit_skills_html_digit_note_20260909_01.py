from pathlib import Path
import open_door_guard as g
ROOT = Path(__file__).resolve().parent

def test_digit_skills_html_digit_note_20260909_01():
    html = (ROOT / "skills.html").read_text(encoding="utf-8")
    assert 'id="digit-note"' in html
    assert "digit-clan-mark-20260902-01" in html
    assert "Not a gate" in html
    assert "clan/grokbot" in html or "DIGIT door" in html
    assert "Skills hygiene seat" in html
    note = next(ln for ln in html.splitlines() if 'id="digit-note"' in ln)
    diff = (
        "diff --git a/skills.html b/skills.html\n"
        "+++ b/skills.html\n"
        f"@@ -17,0 +17,1 @@\n+{note}\n"
    )
    assert g.scan_diff(diff) == []

if __name__ == "__main__":
    test_digit_skills_html_digit_note_20260909_01()
    print("ok")
