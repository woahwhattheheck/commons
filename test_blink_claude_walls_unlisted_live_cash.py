"""Hermetic: blink-claude-walls-unlisted-live-cash-20260909-01."""
from pathlib import Path
ROOT = Path(__file__).resolve().parent
TARGETS = [
  "ground/CLAUDE_TESTER.md",
  "ground/CLAUDE_PASTE.md",
  "ground/CLAUDE_PARK.md",
  "ground/WALLS_PLAIN.md",
  "ground/UNLISTED.md",
  "ground/WATCHDOG_CANARY.md",
  "ground/board-as-surface.md",
]
MARKERS = ["## Live cash", "agent-rescue.html", "tools-cash.html"]

def test_live_cash_shelves():
  for rel in TARGETS:
    text = (ROOT / rel).read_text(encoding="utf-8")
    for m in MARKERS:
      assert m in text, f"{rel} missing {m}"

if __name__ == "__main__":
  test_live_cash_shelves()
  print("ok")
