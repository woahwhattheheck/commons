#!/usr/bin/env python3
"""Fail-closed tests for proof-spiral-succinct-argument-20260901-01.

Binary PASS only if honest prove+verify accepts, a cheating prover is
rejected, a million-step single-error needle is missed by naive sampling
AND caught after PCP amplification. HTML is not the proof.
"""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

import proof_spiral_succinct_argument as psa

ROOT = Path(__file__).resolve().parent
RUNNER = ROOT / "proof_spiral_succinct_argument.py"
DOOR = ROOT / "proof-spiral-succinct-argument.html"
RECEIPT = ROOT / "p" / "proof-spiral-succinct-argument-20260901-01.md"


class ProofSpiralSuccinctArgumentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.acceptance = psa.run_acceptance()

    def test_leftover_id_is_exact(self) -> None:
        self.assertEqual(psa.LEFTOVER_ID, "proof-spiral-succinct-argument-20260901-01")
        self.assertEqual(self.acceptance["id"], psa.LEFTOVER_ID)
        self.assertTrue(RECEIPT.exists(), "receipt must be minted as p/{id}.md")
        text = RECEIPT.read_text(encoding="utf-8")
        self.assertIn("id: proof-spiral-succinct-argument-20260901-01", text)
        self.assertNotIn("id: proof-spiral-succinct-argument-20260901-02", text)

    def test_pi_digit_program_is_real(self) -> None:
        rows = psa.execute_program(200_000)
        self.assertEqual(rows[0], (0, 0, 1))
        self.assertTrue(psa.valid_adjacent(rows[0], rows[1]))
        self.assertTrue(psa.valid_adjacent(rows[100], rows[101]))
        prefix = psa.pi_prefix(rows[-1][1], 6)
        self.assertEqual(prefix, 314159)
        million_prefix = self.acceptance["pi_prefix"]
        self.assertEqual(million_prefix, 314159)
        # Modular walk actually moves.
        mods = {row[2] for row in rows[:32]}
        self.assertGreater(len(mods), 8)

    def test_honest_prove_verify_accepts(self) -> None:
        result = psa.honest_prove_verify()
        self.assertTrue(result["ok"])
        self.assertEqual(result["accepted"], result["queries"])
        self.assertEqual(result["queries"], psa.MERKLE_QUERIES)
        self.assertEqual(len(result["root"]), 64)
        self.assertTrue(self.acceptance["pass_bits"]["honest_prove_verify_accepts"])

    def test_merkle_path_reconstructs_root(self) -> None:
        rows = psa.execute_program(17)
        tree = psa.commit_trace(rows)
        root = tree.root.hex()
        for i in range(len(rows)):
            self.assertTrue(psa.verify_merkle_path(psa.row_bytes(rows[i]), tree.path(i), root))
        tampered = psa.row_bytes((rows[3][0], rows[3][1] + 1, rows[3][2]))
        self.assertFalse(psa.verify_merkle_path(tampered, tree.path(3), root))

    def test_adaptive_fake_answers_fail_commitment(self) -> None:
        cheat = psa.cheating_prover_rejected()
        self.assertTrue(cheat["fake_transition_internally_valid"])
        self.assertFalse(cheat["accepted"])
        self.assertTrue(cheat["rejected"])
        self.assertIn(cheat["reason"], ("left-commitment", "right-commitment"))

    def test_naive_million_step_needle_is_missed(self) -> None:
        spiral = self.acceptance["spiral"]
        self.assertEqual(spiral["n"], 1_000_000)
        self.assertEqual(spiral["needle_index"], 424_242)
        self.assertEqual(spiral["bad_adjacent_pairs"], 2)
        self.assertEqual(spiral["k"], 64)
        self.assertTrue(spiral["first_trial_missed"])
        self.assertEqual(spiral["first_trial_hits"], 0)
        self.assertGreaterEqual(spiral["theoretical_miss_probability"], 0.99)
        self.assertGreaterEqual(spiral["trials_that_missed"], 190)
        self.assertTrue(self.acceptance["pass_bits"]["naive_first_trial_missed"])

    def test_pcp_true_zero_false_constant_fraction(self) -> None:
        pcp = self.acceptance["pcp"]
        self.assertEqual(pcp["true_bad_edges"], 0)
        self.assertEqual(pcp["true_fraction"], 0.0)
        self.assertGreaterEqual(pcp["false_fraction"], 0.05)
        self.assertGreaterEqual(pcp["false_bad_edges"], int(0.05 * pcp["false_total_edges"]))
        self.assertGreaterEqual(pcp["error_count"], 1)

    def test_needle_caught_after_amplification(self) -> None:
        pcp = self.acceptance["pcp"]
        self.assertEqual(pcp["checks"], 1000)
        self.assertGreater(pcp["sampled_bad_hits"], 0)
        self.assertTrue(pcp["caught_after_amplification"])
        self.assertTrue(self.acceptance["pass_bits"]["needle_caught_after_amplification"])

    def test_binary_pass_contract(self) -> None:
        bits = self.acceptance["pass_bits"]
        self.assertEqual(self.acceptance["status"], "PASS")
        self.assertEqual(self.acceptance["cash_usd"], 0)
        self.assertEqual(self.acceptance["outreach"], 0)
        required = (
            "honest_prove_verify_accepts",
            "cheating_prover_rejected",
            "naive_first_trial_missed",
            "pcp_true_zero_bad",
            "pcp_false_constant_fraction",
            "needle_caught_after_amplification",
            "pi_prefix_real",
        )
        for key in required:
            self.assertTrue(bits[key], key)
        self.assertTrue(all(bits.values()))

    def test_cli_exits_zero_on_pass(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(RUNNER), "--json"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["status"], "PASS")
        self.assertEqual(payload["named_counts"]["cash_usd"], 0)
        self.assertEqual(payload["named_counts"]["million_steps"], 1_000_000)
        self.assertEqual(payload["named_counts"]["naive_first_trial_hits"], 0)
        self.assertGreater(payload["named_counts"]["pcp_sampled_bad_hits"], 0)

    def test_door_is_open_and_not_the_proof(self) -> None:
        text = DOOR.read_text(encoding="utf-8")
        lowered = text.lower()
        self.assertIn("HOLD / BUILD-AND-VERIFY", text)
        self.assertIn("cash_usd=0", text)
        self.assertIn("proof_spiral_succinct_argument.py", text)
        self.assertIn("HTML is not the proof", text)
        self.assertIn("youtu.be/jVHeHmufZhk", text)
        self.assertIn("No login", text)
        self.assertNotIn("password", lowered)
        self.assertNotIn("signup", lowered)
        self.assertNotIn("api-key", lowered)
        self.assertNotIn("oauth", lowered)
        self.assertNotIn("<form", lowered)
        self.assertNotIn("login required", lowered)
        self.assertNotIn("please log in", lowered)


if __name__ == "__main__":
    unittest.main()
