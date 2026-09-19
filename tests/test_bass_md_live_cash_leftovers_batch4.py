from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CLAIM = "bass-md-live-cash-20260916-04"
FILES = [
    ".agents/skills/commons-worker/PURPOSE.md",
    ".agents/skills/experience-compiler/PURPOSE.md",
    ".agents/skills/gpt-grok-ship-loop/references/collision.md",
    ".agents/skills/gpt-grok-ship-loop/references/prompt-template.md",
    ".agents/skills/grok-web-commons/references/connector-contract.md",
    ".agents/skills/outbound-send/SKILL.md",
    ".wire/NO-ASK-BRYCE.md",
    ".wire/NO-ASK-PERMANENT.md",
]


class T(unittest.TestCase):
    def test_exact_live_cash_batch(self):
        self.assertEqual(len(FILES), 8)
        for rel in FILES:
            with self.subTest(rel=rel):
                data = (ROOT / rel).read_bytes()
                text = data.decode("utf-8")
                prefix = "../" * rel.count("/")
                self.assertEqual(text.count("## Live cash"), 1)
                self.assertIn("Verified product pages only — no invented Stripe links.", text)
                for page in (
                    "dealer-service-lead-rescue.html",
                    "referral-intake-completeness.html",
                    "repair-booking-preflight.html",
                    "plant-downtime-handoff.html",
                ):
                    self.assertIn(f"{prefix}{page}", text)
                self.assertNotIn("buy.stripe.com", text)
                self.assertNotIn("\x00", text)
        self.assertTrue(CLAIM)


if __name__ == "__main__":
    unittest.main()
