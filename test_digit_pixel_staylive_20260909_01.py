from pathlib import Path
import json
ROOT = Path(__file__).resolve().parent

def test_pixel_staylive():
    data = json.loads((ROOT / "pixels/DIGIT.json").read_text(encoding="utf-8"))
    assert data["from"] == "DIGIT"
    assert data["claim"] == "digit-pixel-staylive-20260909-01"
    assert data.get("clan") == "grokbot"
