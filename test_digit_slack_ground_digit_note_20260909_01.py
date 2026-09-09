from pathlib import Path
ROOT = Path(__file__).resolve().parent

def test_digit_slack_ground_digit_note_20260909_01():
    md = (ROOT / "ground" / "SLACK.md").read_text(encoding="utf-8")
    assert "## DIGIT" in md
    assert "clan/grokbot" in md
    assert "digit-clan-mark-20260902-01" in md
    assert "Not a gate" in md
    assert "C0BU51F1PL3" in md or "Hands" in md

if __name__ == "__main__":
    test_digit_slack_ground_digit_note_20260909_01()
    print("ok")
