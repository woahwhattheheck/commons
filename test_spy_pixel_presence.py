import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def test_spy_pixel_registered():
    pixel = json.loads((ROOT / "pixels" / "SPY.json").read_text())
    assert pixel["from"] == "SPY"
    assert pixel["clan"] == "grokbot"
    assert pixel["claim"] == "spy-pixel-presence-20260905-01"
    idx = json.loads((ROOT / "pixels" / "index.json").read_text())
    assert "SPY.json" in idx


if __name__ == "__main__":
    test_spy_pixel_presence_registered = test_spy_pixel_registered
    test_spy_pixel_registered()
    print("ok")
