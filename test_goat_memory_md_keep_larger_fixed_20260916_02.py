"""goat-memory-md-keep-larger-fixed-20260916-02 — KEEP Larger on leftover memory MD."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CLAIM = "goat-memory-md-keep-larger-fixed-20260916-02"
PATHS = (
    "memory/CLAUDE_OWNER_WORDS.md",
    "memory/CODEX_BUILDER.md",
    "memory/CURSOR_HALT.md",
    "memory/GROK_APP_ROUTE.md",
    "memory/GROK_LAND_UPFRONT.md",
    "memory/HOLD_QUOTE.md",
    "memory/README.md",
    "memory/READ_IS_VOLTAGE.md",
)
ALREADY_KEPT = "memory/LAW.md"
TIP_PATHS = (
    "agent-rescue.html",
    "dealer-service-lead-rescue.html",
    "referral-intake-completeness.html",
    "repair-booking-preflight.html",
    "plant-downtime-handoff.html",
)
LARGER_PATHS = ("diagnostic.html", "commercial.html")


def _cash(text: str) -> str:
    idx = text.find("## Live cash")
    nxt = text.find("\n## ", idx + 1)
    return text[idx:] if nxt < 0 else text[idx:nxt]


class TestGoatMemoryMdKeepLargerFixed2026091602(unittest.TestCase):
    def test_leftover_memory_cards_keep_autopsy_and_larger(self) -> None:
        for rel in PATHS:
            with self.subTest(rel=rel):
                text = (ROOT / rel).read_text(encoding="utf-8")
                cash = _cash(text)
                self.assertIn("## Live cash", text, rel)
                self.assertIn("../agent-rescue.html", cash, rel)
                self.assertIn("../dealer-service-lead-rescue.html", cash, rel)
                self.assertIn("../plant-downtime-handoff.html", cash, rel)
                self.assertIn("Larger fixed engagements", cash, rel)
                self.assertIn("../diagnostic.html", cash, rel)
                self.assertIn("../commercial.html", cash, rel)
                self.assertIn("$12,000", cash, rel)
                self.assertIn("$30,000", cash, rel)
                self.assertNotIn("buy.stripe.com", cash, rel)
                plant = cash.find("plant-downtime-handoff.html")
                larger = cash.find("Larger fixed engagements")
                self.assertGreaterEqual(plant, 0, rel)
                self.assertGreater(larger, plant, rel)

    def test_law_already_kept_untouched_by_this_cite(self) -> None:
        text = (ROOT / ALREADY_KEPT).read_text(encoding="utf-8")
        cash = _cash(text)
        self.assertIn("../diagnostic.html", cash)
        self.assertIn("../commercial.html", cash)
        self.assertIn("Cite ground/EXECUTE.md Live cash", cash)

    def test_product_pages_exist(self) -> None:
        for name in TIP_PATHS + LARGER_PATHS:
            self.assertTrue((ROOT / name).is_file(), name)

    def test_receipt_exists(self) -> None:
        receipt = ROOT / "p" / f"{CLAIM}.md"
        text = receipt.read_text(encoding="utf-8")
        self.assertIn(f"id: {CLAIM}", text)
        self.assertIn("Hands off #8802", text)
        self.assertIn("Tip KEEP", text)
        self.assertNotIn("buy.stripe.com", text)
        for rel in PATHS:
            self.assertIn(rel, text, rel)
        self.assertNotIn("leftover-census.md", text)


if __name__ == "__main__":
    unittest.main()
