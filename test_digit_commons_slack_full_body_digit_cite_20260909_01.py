from pathlib import Path
ROOT = Path(__file__).resolve().parent

def test_digit_commons_slack_full_body_digit_cite_20260909_01():
    src = (ROOT / "host" / "commons_slack_full_body.py").read_text(encoding="utf-8")
    assert "DIGIT cite" in src
    assert "clan/grokbot" in src
    assert "digit-clan-mark-20260902-01" in src
    assert "Not a gate" in src
    assert "commons-slack.html" in src
    assert "do not invent a token" in src
    assert "--send" in src

if __name__ == "__main__":
    test_digit_commons_slack_full_body_digit_cite_20260909_01()
    print("ok")
