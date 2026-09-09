from pathlib import Path
ROOT = Path(__file__).resolve().parent

def test_digit_discord_mirror_digit_cite_20260909_01():
    src = (ROOT / "host" / "discord_mirror.py").read_text(encoding="utf-8")
    assert "DIGIT cite" in src
    assert "clan/grokbot" in src
    assert "digit-clan-mark-20260902-01" in src
    assert "Not a gate" in src
    # still DARK without token — do not invent
    assert "DARK" in src
    assert "Do not invent a token" in src or "Do not invent" in src

if __name__ == "__main__":
    test_digit_discord_mirror_digit_cite_20260909_01()
    print("ok")
