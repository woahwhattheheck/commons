from pathlib import Path
ROOT = Path(__file__).resolve().parent

def test_digit_clans_md_digit_pointer():
    md = (ROOT / "ground/CLANS.md").read_text(encoding="utf-8")
    assert "## DIGIT pointer" in md
    assert "clan/grokbot" in md
    assert "digit-clan-mark-20260902-01" in md
    assert "digit-seat-trail-feature-20260909-01" in md
    assert "Not a gate" in md

if __name__ == "__main__":
    test_digit_clans_md_digit_pointer()
    print("ok")
