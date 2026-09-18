from pathlib import Path
ROOT = Path(__file__).resolve().parent

def test_digit_features_md_digit_note_20260909_01():
    md = (ROOT / "ground" / "FEATURES.md").read_text(encoding="utf-8")
    assert "## DIGIT" in md
    assert "clan/grokbot" in md
    assert "digit-clan-mark-20260902-01" in md
    assert "Not a gate" in md
    assert "features.html" in md
    assert "Lane FEATURES welcome" in md

if __name__ == "__main__":
    test_digit_features_md_digit_note_20260909_01()
    print("ok")
