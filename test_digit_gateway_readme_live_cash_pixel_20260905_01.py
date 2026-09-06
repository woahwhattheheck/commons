from pathlib import Path
import json
ROOT = Path(__file__).resolve().parent

def test_gateway_live_cash():
    md = (ROOT / "docs/commons-gateway/README.md").read_text(encoding="utf-8")
    assert "Live cash doors" in md and "agent-rescue.html" in md

def test_pixel_staylive():
    data = json.loads((ROOT / "pixels/DIGIT.json").read_text(encoding="utf-8"))
    assert data["from"] == "DIGIT"
    assert "digit-pixel-staylive-20260905-03" == data["claim"]
