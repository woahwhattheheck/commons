"""arbitrage.html does not sell Survival via agent-rescue buyer page."""
from pathlib import Path
import json
import unittest

ROOT = Path(__file__).resolve().parent
HTML = ROOT / "arbitrage.html"
RECORD = ROOT / "revenue/arbitrage/kimi-agent-survival-proof-20260830-01.json"


class QuillArbitrageAutopsyBuyerPageTests(unittest.TestCase):
    def test_survival_card_not_on_agent_rescue(self):
        text = HTML.read_text(encoding="utf-8")
        # Survival card must not use agent-rescue as buyer page.
        survival = text.split('data-opportunity-id="kimi-agent-survival-proof-20260830-01"', 1)[1]
        survival = survival.split("<article", 1)[0]
        self.assertIn("revenue/production_survival/README.md", survival)
        self.assertNotIn('href="./agent-rescue.html"', survival)

    def test_autopsy_card_uses_agent_rescue(self):
        text = HTML.read_text(encoding="utf-8")
        self.assertIn('data-opportunity-id="agent-failure-autopsy-29"', text)
        autopsy = text.split('data-opportunity-id="agent-failure-autopsy-29"', 1)[1]
        autopsy = autopsy.split("<article", 1)[0]
        self.assertIn('href="./agent-rescue.html"', autopsy)

    def test_machine_record_buyer_evidence_off_agent_rescue(self):
        data = json.loads(RECORD.read_text(encoding="utf-8"))
        buyer_urls = [
            row["public_url"]
            for row in data["evidence"]
            if row.get("side") == "BUYER"
        ]
        self.assertTrue(
            any("production_survival/README.md" in url for url in buyer_urls)
        )
        self.assertFalse(
            any("agent-rescue.html" in url for url in buyer_urls)
        )


if __name__ == "__main__":
    unittest.main()
