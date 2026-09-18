import json
from pathlib import Path
ROOT = Path(__file__).resolve().parent

def test_digit_embassy_ground_cards_20260909_01():
    d = json.loads((ROOT / "embassy.json").read_text(encoding="utf-8"))
    assert "ground_cards" in d
    cards = d["ground_cards"]["cards"]
    ids = {c["id"] for c in cards}
    assert "discord-peer" in ids
    assert "telegram-peer" in ids
    assert "slack-door" in ids
    assert "discord-door" in ids
    roads = d["write_roads"]
    assert any(r.endswith("/discord.html") for r in roads)
    assert any(r.endswith("/telegram.html") for r in roads)
    assert any("/slack/plugin.html" in r for r in roads)
    md = (ROOT / "ground" / "EMBASSY.md").read_text(encoding="utf-8")
    assert "DIGIT" in md
    assert "clan/grokbot" in md
    assert "digit-clan-mark-20260902-01" in md
    assert "Not a gate" in md

if __name__ == "__main__":
    test_digit_embassy_ground_cards_20260909_01()
    print("ok")
