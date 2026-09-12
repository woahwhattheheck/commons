from pathlib import Path
import open_door_guard as g

ROOT = Path(__file__).resolve().parent

def test_digit_clans_md_digit_pointer():
    md = (ROOT / "ground/CLANS.md").read_text(encoding="utf-8")
    assert "## DIGIT pointer" in md
    assert "clan/grokbot" in md
    assert "digit-clan-mark-20260902-01" in md
    assert "digit-seat-trail-feature-20260909-01" in md
    assert "Not a gate" in md
    assert "Additive callout only." in md
    line = next(ln for ln in md.splitlines() if "named Cursor Grok Bot" in ln and "clan/grokbot" in ln)
    diff = (
        "diff --git a/ground/CLANS.md b/ground/CLANS.md\n"
        "+++ b/ground/CLANS.md\n"
        f"@@ -54,0 +54,1 @@\n+{line}\n"
    )
    assert g.scan_diff(diff) == []

if __name__ == "__main__":
    test_digit_clans_md_digit_pointer()
    print("ok")
