"""Hermetic: blink-wake-visual-whisper-lims-live-cash-20260909-01 Live cash shelves."""
from pathlib import Path
ROOT = Path(__file__).resolve().parent
TARGETS = [
  "ground/WAKE_CONTRACT.md",
  "ground/VISUAL.md",
  "ground/WHISPER.md",
  "ground/VENT.md",
  "ground/UNBUILT_ITEMS.md",
  "ground/TWO_PATHS.md",
  "ground/XYZ_ZERO.md",
  "ground/WIDTH200.md",
]
MARKERS = ["## Live cash", "agent-rescue.html", "dealer-service-lead-rescue.html", "tools-cash.html"]

def test_live_cash_shelves():
  for rel in TARGETS:
    text = (ROOT / rel).read_text(encoding="utf-8")
    for m in MARKERS:
      assert m in text, f"{rel} missing {m}"

if __name__ == "__main__":
  test_live_cash_shelves()
  print("ok")
