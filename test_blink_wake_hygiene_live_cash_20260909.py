"""Hermetic: blink-wake-hygiene-live-cash-20260909-01."""
from pathlib import Path
ROOT = Path(__file__).resolve().parent
TARGETS = [
  "ground/wake-meta.md",
  "ground/wake-gpt.md",
  "ground/wake-github.md",
  "ground/debug-is-file-edits.md",
  "ground/GROK_CLAUDE_HYGIENE.md",
  "ground/TJLABS_PACK_TERMS.md",
  "ground/CLAUDE_OVER_REFUSAL_LOCAL.md",
  "ground/wake-universal-all-harness.md",
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
