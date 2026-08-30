#!/usr/bin/env python3

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from host import muhlnickel_candidate_lab as labmod


ROOT = Path(__file__).resolve().parent


class MuhlnickelCandidateLabTests(unittest.TestCase):
    def setUp(self):
        self.lab = labmod.new_lab("sha256-leading-zero-bits-d8-fixture-a")

    def test_create_is_source_bound_and_duplicate_safe(self):
        row = labmod.create_candidate(
            self.lab, "muhlnickel-gate-a", "muhl-chain-gates", "titan/engines/muhl_chain.py"
        )
        self.assertEqual(row["state"], "CREATED")
        self.assertEqual(len(row["source_sha256"]), 64)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            labmod.create_candidate(
                self.lab, "muhlnickel-gate-a", "muhl-chain-gates", "titan/engines/muhl_chain.py"
            )

    def test_fastest_requires_comparable_solved_receipts(self):
        for candidate in ("gate-a", "gate-b"):
            labmod.create_candidate(
                self.lab, candidate, "muhl-chain-gates", "titan/engines/muhl_chain.py"
            )
        self.assertIsNone(labmod.fastest_candidate(self.lab))
        labmod.record_trial(self.lab, "gate-a", 100, 1_000_000_000, "00aa")
        labmod.record_trial(self.lab, "gate-b", 250, 1_000_000_000, "00bb")
        self.assertEqual(labmod.fastest_candidate(self.lab)["candidate_id"], "gate-b")
        winner = labmod.promote_fastest(self.lab)
        self.assertEqual(winner["state"], "PROMOTED")
        self.assertEqual(self.lab["claim_state"], "FASTEST_ON_NAMED_PUZZLE_RECEIPTS")
        self.assertEqual(labmod._candidate(self.lab, "gate-a")["state"], "FIRED")

    def test_owner_approved_fire_is_reversible_source_safe_state(self):
        labmod.create_candidate(
            self.lab, "gate-a", "muhl-chain-gates", "titan/engines/muhl_chain.py"
        )
        row = labmod.fire_candidate(self.lab, "gate-a", "superseded candidate topology")
        self.assertEqual(row["state"], "FIRED")
        self.assertTrue((ROOT / row["source"]).is_file())
        self.assertFalse(self.lab["boundaries"]["source_candidates_deleted_when_fired"])

    def test_unmeasured_fastest_claim_is_refused(self):
        labmod.create_candidate(
            self.lab, "gate-a", "muhl-chain-gates", "titan/engines/muhl_chain.py"
        )
        with self.assertRaisesRegex(ValueError, "no solved measured"):
            labmod.promote_fastest(self.lab)

    def test_cli_initializes_public_registry_without_network_or_money(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry = Path(tmp) / "candidates.json"
            subprocess.check_call(
                [sys.executable, "host/muhlnickel_candidate_lab.py", str(registry), "init", "fixture"],
                cwd=ROOT,
                stdout=subprocess.DEVNULL,
            )
            loaded = labmod._load(registry)
            self.assertEqual(loaded["commercial_disposition"], "PUBLIC_SALE_ALLOWED")
            self.assertFalse(loaded["boundaries"]["live_network_bound"])
            self.assertFalse(loaded["boundaries"]["money_moved"])


if __name__ == "__main__":
    unittest.main()
