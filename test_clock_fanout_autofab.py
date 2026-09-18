import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RECEIPT_ID = "codex-dir20-clock-fanout-autofab-done-20260830-01"


class ClockFanoutAutofabDecisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.packet = json.loads(
            (ROOT / "ground" / "CLOCK_FANOUT_AUTOFAB.json").read_text(encoding="utf-8")
        )

    def test_n_is_the_measured_clock_count(self):
        evidence = self.packet["evidence"]
        self.assertEqual(self.packet["autofab_n"], 24)
        self.assertEqual(evidence["clocks"], 24)
        self.assertEqual(sum(evidence["clock_fanout_per_ring"]), 24)
        self.assertEqual(len(evidence["clock_fanout_per_ring"]), evidence["rings"])

    def test_evidence_is_pinned_and_non_actuating(self):
        self.assertEqual(
            self.packet["evidence"]["commit"],
            "35e3861fa7eef4242c04f9545043fac5fb30c383",
        )
        self.assertEqual(
            self.packet["evidence"]["snapshot_sha256"],
            "1cf1a9f3c1649b82d19fc78440d468483d5d4bd3bff49a3da1cc0179a3f4911d",
        )
        self.assertEqual(
            self.packet["destination_source"], "FROM_FILE_AT_FUTURE_ACTUATION"
        )
        self.assertTrue(all(value is False for value in self.packet["actuation"].values()))

    def test_owner_wall_and_unfinished_card_name_the_receipt(self):
        directives = (ROOT / "DIRECTIVES.md").read_text(encoding="utf-8")
        unfinished = (ROOT / "muhl" / "docs" / "UNFINISHED.md").read_text(encoding="utf-8")
        self.assertIn(RECEIPT_ID, directives)
        self.assertIn(RECEIPT_ID, unfinished)
        section = unfinished.split(
            "### 14. Clock fanout / autofab N / germ dock", 1
        )[1].split("### 15.", 1)[0]
        self.assertIn("N=24 proposed residents", section)
        self.assertNotIn("Do not pick N", section)


if __name__ == "__main__":
    unittest.main()
