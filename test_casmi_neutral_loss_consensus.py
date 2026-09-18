from __future__ import annotations

import copy
import importlib.util
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODULE = HERE / "competitions" / "enveda_casmi_2026" / "neutral_loss_consensus.py"
FIXTURE = HERE / "competitions" / "enveda_casmi_2026" / "synthetic_neutral_loss_fixture.json"

spec = importlib.util.spec_from_file_location("casmi_neutral_loss_consensus", MODULE)
nl = importlib.util.module_from_spec(spec)
if spec.loader is None:
    raise RuntimeError("neutral-loss module loader unavailable")
spec.loader.exec_module(nl)


def load_fixture():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


class NeutralLossConsensusTests(unittest.TestCase):
    def test_01_hostile_adduct_shift_recovers_expected_candidate(self):
        packet = nl.compile_fixture(load_fixture())
        row = next(x for x in packet["rows"] if x["molecule_id"] == "M-ADDUCT-SHIFT")
        self.assertEqual(row["predecessor_top25"][0]["candidate_id"], "C-FRAGMENT-DECOY")
        self.assertGreater(row["predecessor_expected_rank"], 1)
        self.assertEqual(row["successor_expected_rank"], 1)
        self.assertEqual(row["successor_top25"][0]["candidate_id"], "C-TRUE-LOSS")
        self.assertGreater(packet["successor_mrr_at_25_ppm"], packet["predecessor_mrr_at_25_ppm"])

    def test_02_stable_case_remains_rank_one(self):
        packet = nl.compile_fixture(load_fixture())
        row = next(x for x in packet["rows"] if x["molecule_id"] == "M-STABLE")
        self.assertEqual(row["predecessor_expected_rank"], 1)
        self.assertEqual(row["successor_expected_rank"], 1)

    def test_03_non_synthetic_rejected(self):
        d = load_fixture()
        d["dataset_kind"] = "PUBLIC_OPEN"
        with self.assertRaisesRegex(nl.NeutralLossError, "only SYNTHETIC"):
            nl.compile_fixture(d)

    def test_04_authority_escalation_rejected(self):
        d = load_fixture()
        d["authority"]["submission_authorized"] = True
        with self.assertRaisesRegex(nl.NeutralLossError, "authority ceiling"):
            nl.compile_fixture(d)

    def test_05_bool_numeric_alias_rejected(self):
        d = load_fixture()
        d["fragment_tolerance_da"] = True
        with self.assertRaisesRegex(nl.NeutralLossError, "numeric value required"):
            nl.compile_fixture(d)

    def test_06_nonfinite_numeric_rejected(self):
        d = load_fixture()
        d["neutral_loss_tolerance_da"] = math.inf
        with self.assertRaisesRegex(nl.NeutralLossError, "finite positive"):
            nl.compile_fixture(d)

    def test_07_invalid_weight_sum_rejected(self):
        d = load_fixture()
        d["fragment_weight_bp"] = 5000
        with self.assertRaisesRegex(nl.NeutralLossError, "sum to 10000"):
            nl.compile_fixture(d)

    def test_08_zero_weight_rejected(self):
        d = load_fixture()
        d["fragment_weight_bp"] = 0
        d["neutral_loss_weight_bp"] = 10000
        with self.assertRaisesRegex(nl.NeutralLossError, "both be positive"):
            nl.compile_fixture(d)

    def test_09_fragment_at_precursor_rejected(self):
        d = load_fixture()
        spectrum = d["molecules"][0]["spectra"][0]
        spectrum["peaks"][-1][0] = spectrum["precursor_mz"]
        with self.assertRaisesRegex(nl.NeutralLossError, "below precursor"):
            nl.compile_fixture(d)

    def test_10_unsorted_peaks_rejected(self):
        d = load_fixture()
        d["molecules"][0]["spectra"][0]["peaks"] = [[140.0, 1], [100.0, 1]]
        with self.assertRaisesRegex(nl.NeutralLossError, "strictly increasing"):
            nl.compile_fixture(d)

    def test_11_empty_peak_list_rejected(self):
        d = load_fixture()
        d["molecules"][0]["spectra"][0]["peaks"] = []
        with self.assertRaisesRegex(nl.NeutralLossError, "non-empty bounded"):
            nl.compile_fixture(d)

    def test_12_duplicate_molecule_id_rejected(self):
        d = load_fixture()
        clone = copy.deepcopy(d["molecules"][0])
        clone["expected_candidate_id"] = "C-STABLE"
        d["molecules"].append(clone)
        with self.assertRaisesRegex(nl.NeutralLossError, "duplicate molecule_id"):
            nl.compile_fixture(d)

    def test_13_duplicate_candidate_id_rejected(self):
        d = load_fixture()
        d["candidates"].append(copy.deepcopy(d["candidates"][0]))
        with self.assertRaisesRegex(nl.NeutralLossError, "duplicate candidate_id"):
            nl.compile_fixture(d)

    def test_14_missing_expected_candidate_rejected(self):
        d = load_fixture()
        d["molecules"][0]["expected_candidate_id"] = "C-ABSENT"
        with self.assertRaisesRegex(nl.NeutralLossError, "expected_candidate_id"):
            nl.compile_fixture(d)

    def test_15_smiles_separator_rejected(self):
        d = load_fixture()
        d["candidates"][0]["smiles"] += ";BAD"
        with self.assertRaisesRegex(nl.NeutralLossError, "separator"):
            nl.compile_fixture(d)

    def test_16_smiles_newline_rejected(self):
        d = load_fixture()
        d["candidates"][0]["smiles"] += "\nBAD"
        with self.assertRaises(nl.NeutralLossError):
            nl.compile_fixture(d)

    def test_17_duplicate_json_key_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "dup.json"
            path.write_text('{"schema":"x","schema":"y"}', encoding="utf-8")
            with self.assertRaisesRegex(nl.NeutralLossError, "duplicate JSON key"):
                nl.read_json(path)

    def test_18_nonregular_input_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(nl.NeutralLossError):
                nl.read_json(Path(td))

    def test_19_result_tamper_rejected(self):
        d = load_fixture()
        packet = nl.compile_fixture(d)
        packet["successor_mrr_at_25_ppm"] -= 1
        with self.assertRaisesRegex(nl.NeutralLossError, "receipt mismatch"):
            nl.verify_result(packet, d)

    def test_20_rehashed_semantic_forgery_rejected(self):
        d = load_fixture()
        packet = nl.compile_fixture(d)
        packet["method"] = "FORGED"
        body = dict(packet)
        body.pop("result_sha256")
        packet["result_sha256"] = nl.digest(body)
        with self.assertRaisesRegex(nl.NeutralLossError, "semantic exact-recompile"):
            nl.verify_result(packet, d)

    def test_21_candidate_and_molecule_order_do_not_change_rank_semantics(self):
        a = load_fixture()
        b = load_fixture()
        b["molecules"].reverse()
        b["candidates"].reverse()
        pa = nl.compile_fixture(a)
        pb = nl.compile_fixture(b)
        for packet in (pa, pb):
            packet.pop("fixture_sha256")
            packet.pop("result_sha256")
        self.assertEqual(pa, pb)

    def test_22_top25_is_bounded(self):
        d = load_fixture()
        template = copy.deepcopy(d["candidates"][-1])
        for i in range(30):
            row = copy.deepcopy(template)
            row["candidate_id"] = f"C-EXTRA-{i:02d}"
            row["smiles"] = f"C{'C' * (i % 5 + 1)}N"
            row["reference_spectra"][0]["precursor_mz"] += 50 + i
            d["candidates"].append(row)
        packet = nl.compile_fixture(d)
        self.assertTrue(all(len(row["successor_top25"]) == 25 for row in packet["rows"]))
        self.assertTrue(all(len(row["predecessor_top25"]) == 25 for row in packet["rows"]))

    def test_23_create_exclusive_output(self):
        packet = nl.compile_fixture(load_fixture())
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "packet.json"
            nl.write_create_exclusive(out, packet)
            self.assertTrue(out.is_file())
            with self.assertRaisesRegex(nl.NeutralLossError, "create-exclusive"):
                nl.write_create_exclusive(out, packet)

    def test_24_cli_compile_and_verify(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "packet.json"
            compiled = subprocess.run(
                [sys.executable, str(MODULE), "compile", str(FIXTURE), str(out)],
                cwd=HERE, text=True, capture_output=True, check=True,
            )
            packet = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(compiled.stdout.strip(), packet["result_sha256"])
            verified = subprocess.run(
                [sys.executable, str(MODULE), "verify", str(FIXTURE), str(out)],
                cwd=HERE, text=True, capture_output=True, check=True,
            )
            self.assertEqual(verified.stdout.strip(), packet["result_sha256"])

    def test_25_all_authority_remains_false(self):
        packet = nl.compile_fixture(load_fixture())
        self.assertTrue(packet["authority"])
        self.assertTrue(all(value is False for value in packet["authority"].values()))
        self.assertFalse(packet["competition_score_claimed"])
        self.assertFalse(packet["submission_used"])
        self.assertFalse(packet["prize_or_revenue_claimed"])

    def test_26_receipt_and_compilation_are_deterministic(self):
        d = load_fixture()
        a = nl.compile_fixture(d)
        b = nl.compile_fixture(copy.deepcopy(d))
        self.assertEqual(nl.canonical(a), nl.canonical(b))
        self.assertTrue(nl.verify_result(a, d))

    def test_27_committed_experiment_receipt_is_exact(self):
        d = load_fixture()
        receipt_path = HERE / "competitions" / "enveda_casmi_2026" / "synthetic_neutral_loss_experiment_receipt.json"
        committed = json.loads(receipt_path.read_text(encoding="utf-8"))
        expected = nl.compile_fixture(d)
        self.assertEqual(nl.canonical(committed), nl.canonical(expected))
        self.assertTrue(nl.verify_result(committed, d))


if __name__ == "__main__":
    unittest.main(verbosity=2)
