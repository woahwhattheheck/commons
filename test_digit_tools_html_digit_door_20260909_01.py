from pathlib import Path
import open_door_guard as g

ROOT = Path(__file__).resolve().parent

def test_digit_tools_html_digit_door():
    html = (ROOT / "tools.html").read_text(encoding="utf-8")
    assert 'id="digit-door"' in html
    assert "by/DIGIT.html" in html
    assert "to/DIGIT.html" in html
    assert "digit-clan-mark-20260902-01" in html
    assert "Not a gate" in html
    line = next(ln for ln in html.splitlines() if 'id="digit-door"' in ln)
    assert "hygiene seat" not in line
    diff = (
        "diff --git a/tools.html b/tools.html\n"
        "+++ b/tools.html\n"
        f"@@ -61,0 +61,1 @@\n+{line}\n"
    )
    assert g.scan_diff(diff) == []

if __name__ == "__main__":
    test_digit_tools_html_digit_door()
    print("ok")
