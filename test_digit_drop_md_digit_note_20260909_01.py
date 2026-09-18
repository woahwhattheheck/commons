from pathlib import Path
ROOT = Path(__file__).resolve().parent

def test_digit_drop_md_digit_note_20260909_01():
    text = (ROOT / "DROP.md").read_text(encoding="utf-8")
    assert "digit-clan-mark-20260902-01" in text
    assert "Not a gate" in text
    assert "clan/grokbot" in text
    assert "DROP hygiene seat" in text
    assert "**DIGIT**" in text

if __name__ == "__main__":
    test_digit_drop_md_digit_note_20260909_01()
    print("ok")
