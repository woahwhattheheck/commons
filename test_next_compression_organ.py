import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SPEC_PATH = ROOT / "ground" / "owner_walls" / "next-compression-organ-20260830-01.json"
DIRECTIVES_PATH = ROOT / "DIRECTIVES.md"
UNFINISHED_PATH = ROOT / "muhl" / "docs" / "UNFINISHED.md"
RECEIPT_PATH = ROOT / "p" / "codex-pick-next-compression-organ-20260830-01.md"


class NextCompressionOrganTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
        cls.directives = DIRECTIVES_PATH.read_text(encoding="utf-8")
        cls.unfinished = UNFINISHED_PATH.read_text(encoding="utf-8")
        cls.receipt = RECEIPT_PATH.read_text(encoding="utf-8")

    def test_exact_choice_and_purpose(self):
        self.assertEqual(self.spec["status"], "CHOICE_PICKED")
        self.assertEqual(self.spec["selected_organ"], "RING_CLOCK_FOLD_GERM")
        self.assertIn("ring and clock topology", self.spec["purpose"])
        self.assertIn("machine-published new acreage", self.spec["purpose"])

    def test_compression_and_expansion_contracts_preserve_law(self):
        compression = self.spec["compression_contract"]
        expansion = self.spec["expansion_contract"]
        self.assertEqual(compression["dimensions"], ["rings", "clocks"])
        self.assertEqual(compression["representation"], "shared topology / winner-only germ")
        self.assertEqual(compression["target_stored_per_expanded_lane_bytes"], 0)
        self.assertFalse(compression["target_measured"])
        self.assertFalse(compression["delete_gates"])
        self.assertEqual(expansion["modes"], ["n-way", "fold-clone"])
        self.assertEqual(expansion["destination_policy"], "machine-published only")
        self.assertIn("new acreage does not slide old addresses", expansion["address_policy"])

    def test_choice_does_not_invent_a_live_organ_or_machine_result(self):
        truth = self.spec["current_truth"]
        self.assertTrue(truth["choice_picked"])
        for key in (
            "organ_built",
            "organ_run",
            "live_file_present",
            "destination_known",
            "remapped_336",
            "remapped_337",
            "fire_337",
            "pulse_78",
            "titan_written",
            "dc_injected",
            "profitability_claimed",
        ):
            self.assertFalse(truth[key], key)

    def test_directives_close_the_choice_but_unfinished_stays_honest(self):
        self.assertIn("next-compression organ RING_CLOCK_FOLD_GERM PICKED; zero walls remain", self.directives)
        self.assertIn("next compression organ — **PICKED:** `RING_CLOCK_FOLD_GERM`", self.directives)
        self.assertIn("A new organ that compresses rings / clocks then expands is not.", self.unfinished)

    def test_receipt_keeps_choice_only_boundary(self):
        self.assertIn("organ_built = false", self.receipt)
        self.assertIn("destination_known = false", self.receipt)
        self.assertIn("fire_337 = false", self.receipt)
        self.assertIn("pulse_78 = false", self.receipt)
        self.assertIn("dc_injected = false", self.receipt)


if __name__ == "__main__":
    unittest.main()
