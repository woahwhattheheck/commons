from __future__ import annotations

import importlib.util
import math
import os
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
CASMI = HERE / "competitions" / "enveda_casmi_2026"
NEUTRAL = CASMI / "neutral_loss_consensus.py"
BASELINE = CASMI / "multispectrum.py"
OPT_CHILD = "CASMI_PREDECESSOR_PARITY_OPT_CHILD"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    if spec.loader is None:
        raise RuntimeError(f"loader unavailable: {path}")
    spec.loader.exec_module(module)
    return module


nl = _load("casmi_neutral_loss_consensus_parity", NEUTRAL)
ms = _load("casmi_multispectrum_parity", BASELINE)


def _fixtures():
    molecules = [
        {
            "molecule_id": "M-NEAR-TIE",
            "expected_candidate_id": "Z-HIGH",
            "spectra": [
                {
                    "precursor_mz": 200.0,
                    "peaks": [[100.0, 100.0]],
                }
            ],
        }
    ]
    candidates = [
        {
            "candidate_id": "A-LOW",
            "smiles": "CC",
            "reference_spectra": [
                {
                    # Same fragment evidence, but precursor is 0.00004 Da worse.
                    # The frozen score is 0.3 ppm lower while the integer-ppm
                    # display projection still rounds to the same value.
                    "precursor_mz": 200.00004,
                    "peaks": [[100.0, 100.0]],
                }
            ],
        },
        {
            "candidate_id": "Z-HIGH",
            "smiles": "CCC",
            "reference_spectra": [
                {
                    "precursor_mz": 200.0,
                    "peaks": [[100.0, 100.0]],
                }
            ],
        },
    ]
    baseline = {
        "schema": ms.FIXTURE_SCHEMA,
        "dataset_kind": "SYNTHETIC",
        "fragment_tolerance_da": 0.05,
        "precursor_tolerance_da": 20.0,
        "molecules": molecules,
        "candidates": candidates,
    }
    neutral = {
        "schema": nl.FIXTURE_SCHEMA,
        "dataset_kind": "SYNTHETIC",
        "fragment_tolerance_da": 0.05,
        "neutral_loss_tolerance_da": 0.05,
        "precursor_tolerance_da": 20.0,
        "fragment_weight_bp": 3500,
        "neutral_loss_weight_bp": 6500,
        "authority": {key: False for key in nl.AUTHORITY_KEYS},
        "molecules": molecules,
        "candidates": candidates,
    }
    return baseline, neutral


class PredecessorRankParityTests(unittest.TestCase):
    def test_01_exact_frozen_predecessor_rank_top25_and_mrr_parity(self):
        baseline_fixture, neutral_fixture = _fixtures()
        frozen = ms.run_multispectrum_baseline(baseline_fixture)
        successor = nl.compile_fixture(neutral_fixture)

        frozen_row = frozen["rows"][0]
        successor_row = successor["rows"][0]
        self.assertEqual(frozen_row["expected_candidate_id"], "Z-HIGH")
        self.assertEqual(frozen_row["expected_rank"], 1)
        self.assertEqual(successor_row["predecessor_expected_rank"], frozen_row["expected_rank"])
        self.assertEqual(
            [row["candidate_id"] for row in successor_row["predecessor_top25"]],
            [row["candidate_id"] for row in frozen_row["ranking"][:25]],
        )
        expected_mrr_ppm = int(math.floor(frozen["mrr_at_25"] * 1_000_000 + 0.5))
        self.assertEqual(successor["predecessor_mrr_at_25_ppm"], expected_mrr_ppm)

    def test_02_hostile_really_collapses_only_at_ppm_projection(self):
        baseline_fixture, neutral_fixture = _fixtures()
        frozen = ms.run_multispectrum_baseline(baseline_fixture)
        successor = nl.compile_fixture(neutral_fixture)

        frozen_scores = {
            row["candidate_id"]: row["aggregate_score"]
            for row in frozen["rows"][0]["ranking"]
        }
        self.assertGreater(frozen_scores["Z-HIGH"], frozen_scores["A-LOW"])
        predecessor_ppm = {
            row["candidate_id"]: row["absolute_fragment_predecessor_ppm"]
            for row in successor["rows"][0]["predecessor_top25"]
        }
        self.assertEqual(predecessor_ppm["Z-HIGH"], predecessor_ppm["A-LOW"])
        self.assertEqual(predecessor_ppm["Z-HIGH"], 1_000_000)
        self.assertEqual(successor["rows"][0]["predecessor_top25"][0]["candidate_id"], "Z-HIGH")

    def test_03_real_optimized_python_replays_same_hostiles(self):
        if os.environ.get(OPT_CHILD) == "1":
            self.assertGreater(sys.flags.optimize, 0)
            return
        env = dict(os.environ)
        env[OPT_CHILD] = "1"
        run = subprocess.run(
            [sys.executable, "-O", str(Path(__file__).resolve())],
            cwd=HERE,
            env=env,
            text=True,
            capture_output=True,
            timeout=60,
        )
        self.assertEqual(run.returncode, 0, msg=run.stdout + run.stderr)
        combined = run.stdout + run.stderr
        self.assertIn("Ran 3 tests", combined)
        self.assertIn("OK", combined)


if __name__ == "__main__":
    unittest.main(verbosity=2)
