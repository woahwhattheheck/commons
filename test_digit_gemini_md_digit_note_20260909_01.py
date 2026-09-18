from pathlib import Path
ROOT = Path(__file__).resolve().parent

def test_digit_gemini_md_digit_note_20260909_01():
    md = (ROOT / "GEMINI.md").read_text(encoding="utf-8")
    assert "DIGIT" in md
    assert "digit-clan-mark-20260902-01" in md
    assert "Not a gate" in md
    assert "clan/grokbot" in md
    assert "GEMINI hygiene seat." in md

if __name__ == "__main__":
    test_digit_gemini_md_digit_note_20260909_01()
    print("ok")
