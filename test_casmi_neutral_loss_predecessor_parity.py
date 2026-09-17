from __future__ import annotations

import importlib.util
import math
import os
from pathlib import Path
import subprocess
import sys
import unittest

HERE = Path(__file__).resolve().parent
NL_PATH = HERE / "competitions" / "enveda_casmi_2026" / "neutral_loss_consensus.py"
MS_PATH = HERE / "competitions" / "enveda_casmi_2026" / "multispectrum.py"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


nl = _load("casmi_neutral_loss_consensus_parity", NL_PATH)
ms = _load("casmi_multispectrum_frozen_parity", MS_PATH)


def _fixtures():
    spectrum = {"precursor_mz": 100.0, "peaks": [[50.0, 1.0]]}
    candidates = [
        {
            "candidate_id": "A-LOW",
            "smiles": "CC",
            "reference_spectra": [
                {"precursor_mz": 100.00002, "peaks": [[50.0, 1.0]]}
            ],
        },
        {
            "candidate_id": "Z-HIGH",
            "smiles": "CN",
            "reference_spectra": [
                {"precursor_mz": 100.0, "peaks": [[50.0, 1.0]]}
            ],
        },
    ]
    molecules = [
        {
            "molecule_id": "M-SUB-PPM",
            "expected_candidate_id": "Z-HIGH",
            "spectra": [spectrum],
        }
    ]
    successor = {
        "schema": nl.FIXTURE_SCHEMA,
        "dataset_kind": "SYNTHETIC",
        "fragment_tolerance_da": 0.01,
        "neutral_loss_tolerance_da": 0.01,
        "precursor_tolerance_da": 10.0,
        "fragment_weight_bp": 5000,
        "neutral_loss_weight_bp": 5000,
        "authority": {key: False for key in nl.AUTHORITY_KEYS},
        "molecules": molecules,
        "candidates": candidates,
    }
    frozen = {
        "schema": ms.FIXTURE_SCHEMA,
        "dataset_kind": "SYNTHETIC",
        "fragment_tolerance_da": 0.01,
        "precursor_tolerance_da": 10.0,
        "molecules": molecules,
        "candidates": candidates,
    }
    return successor, frozen


class FrozenPredecessorParityTests(unittest.TestCase):
    def test_sub_ppm_rank_order_and_mrr_match_frozen_baseline(self):
        successor_fixture, frozen_fixture = _fixtures()
        successor = nl.compile_fixture(successor_fixture)
        frozen = ms.run_multispectrum_baseline(frozen_fixture)

        srow = successor["rows"][0]
        frow = frozen["rows"][0]
        frozen_ids = [row["candidate_id"] for row in frow["ranking"][:25]]
        successor_ids = [row["candidate_id"] for row in srow["predecessor_top25"]]

        # The exact hostile: scores differ by 0.3 ppm, so both display as the
        # same integer ppm even though the frozen 12-decimal baseline ranks
        # Z-HIGH first. Ranking on ppm would therefore incorrectly choose A-LOW
        # via candidate-id tie break.
        displayed = {
            row["candidate_id"]: row["absolute_fragment_predecessor_ppm"]
            for row in srow["predecessor_top25"]
        }
        self.assertEqual(displayed["A-LOW"], displayed["Z-HIGH"])
        self.assertEqual(displayed["A-LOW"], nl.SCORE_SCALE)
        self.assertEqual(frow["expected_rank"], 1)
        self.assertEqual(frozen_ids[0], "Z-HIGH")

        self.assertEqual(srow["predecessor_expected_rank"], frow["expected_rank"])
        self.assertEqual(successor_ids, frozen_ids)
        expected_mrr_ppm = int(math.floor(frozen["mrr_at_25"] * nl.SCORE_SCALE + 0.5))
        self.assertEqual(successor["predecessor_mrr_at_25_ppm"], expected_mrr_ppm)

    def test_same_predecessor_runs_under_real_python_optimized_mode(self):
        if os.environ.get("CASMI_PARITY_OPT_CHILD") == "1":
            return
        env = dict(os.environ)
        env["CASMI_PARITY_OPT_CHILD"] = "1"
        subprocess.run(
            [
                sys.executable,
                "-O",
                "-m",
                "unittest",
                "-v",
                Path(__file__).stem,
            ],
            cwd=HERE,
            env=env,
            check=True,
            text=True,
            capture_output=True,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
