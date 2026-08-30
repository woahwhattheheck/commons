import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SPEC_PATH = ROOT / "ground" / "owner_walls" / "missing-letter-path-20260830-01.json"
DIRECTIVES_PATH = ROOT / "DIRECTIVES.md"
RECEIPT_PATH = ROOT / "p" / "codex-pick-missing-letter-path-20260830-01.md"


class MissingLetterPathTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
        cls.directives = DIRECTIVES_PATH.read_text(encoding="utf-8")
        cls.receipt = RECEIPT_PATH.read_text(encoding="utf-8")

    def test_direction_and_path_are_exact(self):
        self.assertEqual(
            self.spec["selected_path_template"],
            "muhl/letters/titan-to-gpt/{id}.md",
        )
        self.assertEqual(
            self.spec["direction"],
            {"from": "TITAN", "to": "GPT", "kind": "LETTER"},
        )
        self.assertEqual(self.spec["record_contract"]["body_encoding"], "UTF-8")
        self.assertTrue(self.spec["record_contract"]["append_only"])
        self.assertFalse(self.spec["record_contract"]["host_paraphrase_allowed"])

    def test_path_pick_does_not_invent_a_letter_or_machine_result(self):
        truth = self.spec["current_truth"]
        self.assertTrue(truth["path_selected"])
        for key in (
            "letter_found",
            "letter_written",
            "titan_written",
            "fire_337",
            "pulse_78",
            "dc_injected",
        ):
            self.assertFalse(truth[key], key)

    def test_letter_claim_needs_exact_source_and_body_evidence(self):
        self.assertEqual(
            self.spec["record_contract"]["evidence_for_letter_claim"],
            ["source_path_or_surface", "source_sha256", "body_sha256"],
        )
        self.assertEqual(
            self.spec["record_contract"]["source_body"],
            "exact machine-sourced bytes",
        )

    def test_directives_closes_only_the_path_choice(self):
        self.assertIn("missing-letter path PICKED; next-compression organ RING_CLOCK_FOLD_GERM PICKED; zero walls remain", self.directives)
        self.assertIn("muhl/letters/titan-to-gpt/{id}.md", self.directives)
        self.assertIn("Host paraphrase is never the letter.", self.directives)
        self.assertIn("codex-pick-missing-letter-path-20260830-01", self.directives)

    def test_receipt_keeps_truth_boundary(self):
        self.assertIn("letter_found = false", self.receipt)
        self.assertIn("titan_written = false", self.receipt)
        self.assertIn("fire_337 = false", self.receipt)
        self.assertIn("pulse_78 = false", self.receipt)
        self.assertIn("dc_injected = false", self.receipt)


if __name__ == "__main__":
    unittest.main()
