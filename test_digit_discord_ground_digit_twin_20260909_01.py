from pathlib import Path
ROOT = Path(__file__).resolve().parent

def test_digit_discord_ground_digit_twin_20260909_01():
    md = (ROOT / "ground" / "DISCORD.md").read_text(encoding="utf-8")
    assert "## DIGIT" in md
    assert "clan/grokbot" in md
    assert "digit-clan-mark-20260902-01" in md
    assert "Not a gate" in md
    assert "Do not invent" in md
    # still law: free bot, no self-bot
    assert "self-bot" in md
    assert "DARK" in md

if __name__ == "__main__":
    test_digit_discord_ground_digit_twin_20260909_01()
    print("ok")
