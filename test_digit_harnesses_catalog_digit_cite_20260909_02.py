import json
from pathlib import Path
ROOT = Path(__file__).resolve().parent
CAT = ROOT / "harnesses" / "catalog.json"

def test_digit_harnesses_catalog_digit_cite_20260909_02():
    text = CAT.read_text(encoding="utf-8")
    cat = json.loads(text)
    assert "DIGIT" in text
    cite = cat.get("digit_cite") or ""
    assert "clan/grokbot" in cite
    assert "digit-clan-mark-20260902-01" in cite
    assert "Not a gate" in cite
    grokbot = next(h for h in cat["harnesses"] if h.get("id") == "grokbot")
    assert "DIGIT cite" in (grokbot.get("note") or "")
    assert "Coil door: TOOLS" in (grokbot.get("note") or "")
    assert grokbot.get("tools_road") == "tools-board"

if __name__ == "__main__":
    test_digit_harnesses_catalog_digit_cite_20260909_02()
    print("ok")
