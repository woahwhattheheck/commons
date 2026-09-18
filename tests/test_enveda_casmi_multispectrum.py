from __future__ import annotations

import copy
import csv
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from competitions.enveda_casmi_2026.multispectrum import (  # noqa: E402
    PUBLIC_CONTRACT_SHA256,
    RESULT_SCHEMA,
    MultiSpectrumError,
    digest,
    normalize_fixture,
    read_json,
    reciprocal_rank_at_25,
    render_submission_preview_csv,
    run_multispectrum_baseline,
    submission_preview_rows,
    validate_public_contract,
)

BASE = ROOT / "competitions" / "enveda_casmi_2026"
CONTRACT = BASE / "public_competition_contract_2026-09-17.json"
FIXTURE = BASE / "synthetic_multispectrum_fixture.json"
MODULE = BASE / "multispectrum.py"


class CasmiMultiSpectrumTests(unittest.TestCase):
    def contract(self):
        return json.loads(CONTRACT.read_text(encoding="utf-8"))

    def fixture(self):
        return json.loads(FIXTURE.read_text(encoding="utf-8"))

    def result(self):
        return run_multispectrum_baseline(self.fixture())

    def test_public_contract_generation_is_exact_and_authority_false(self):
        raw = self.contract()
        self.assertEqual(digest(raw), PUBLIC_CONTRACT_SHA256)
        validated = validate_public_contract(raw)
        self.assertEqual(validated["evaluation"]["metric"], "MRR@25")
        self.assertEqual(validated["evaluation"]["scoring_unit"], "MOLECULE")
        self.assertTrue(validated["authority"])
        self.assertTrue(all(value is False for value in validated["authority"].values()))

    def test_public_contract_tamper_fails_closed(self):
        raw = self.contract()
        raw["submission"]["max_candidates_per_molecule"] = 26
        with self.assertRaises(MultiSpectrumError):
            validate_public_contract(raw)

    def test_preview_revalidates_exact_public_contract(self):
        raw = self.contract()
        raw["authority"]["competition_submission"] = True
        with self.assertRaises(MultiSpectrumError):
            render_submission_preview_csv(raw, self.fixture())

    def test_baseline_is_deterministic_and_molecule_grouped(self):
        one = self.result()
        two = run_multispectrum_baseline(copy.deepcopy(self.fixture()))
        self.assertEqual(one, two)
        self.assertEqual(one["dataset_kind"], "SYNTHETIC")
        self.assertEqual(one["scoring_unit"], "MOLECULE")
        self.assertEqual(one["molecule_count"], 2)
        self.assertEqual(one["spectrum_count"], 5)
        self.assertEqual(one["mrr_at_25"], 1.0)
        self.assertFalse(one["competition_score_claimed"])
        self.assertFalse(one["submission_used"])
        self.assertIn("NOT_KAGGLE_SCORE", one["metric_kind"])

    def test_result_receipt_is_self_consistent(self):
        result = self.result()
        claimed = result["result_sha256"]
        core = dict(result)
        core.pop("result_sha256")
        self.assertEqual(digest(core), claimed)
        self.assertEqual(result["fixture_sha256"], digest(self.fixture()))

    def test_multispectrum_aggregation_recovers_from_one_misleading_spectrum(self):
        row = next(row for row in self.result()["rows"] if row["molecule_id"] == "M-001")
        self.assertEqual(row["expected_rank"], 1)
        ranked = {item["candidate_id"]: item for item in row["ranking"]}
        self.assertGreater(
            ranked["C-D"]["per_spectrum_scores"][2],
            ranked["C-A"]["per_spectrum_scores"][2],
        )
        self.assertGreater(ranked["C-A"]["aggregate_score"], ranked["C-D"]["aggregate_score"])

    def test_reciprocal_rank_at_25_boundary(self):
        self.assertEqual(reciprocal_rank_at_25(1), 1.0)
        self.assertEqual(reciprocal_rank_at_25(2), 0.5)
        self.assertEqual(reciprocal_rank_at_25(25), 1 / 25)
        self.assertEqual(reciprocal_rank_at_25(26), 0.0)
        for bad in (0, -1, True, 1.5):
            with self.subTest(bad=bad), self.assertRaises(MultiSpectrumError):
                reciprocal_rank_at_25(bad)

    def test_competition_gated_dataset_kind_is_rejected(self):
        raw = self.fixture()
        raw["dataset_kind"] = "COMPETITION"
        with self.assertRaises(MultiSpectrumError):
            run_multispectrum_baseline(raw)

    def test_public_open_label_only_promotion_is_rejected(self):
        raw = self.fixture()
        raw["dataset_kind"] = "PUBLIC_OPEN"
        with self.assertRaisesRegex(MultiSpectrumError, "only SYNTHETIC"):
            run_multispectrum_baseline(raw)

    def test_preview_dataset_authority_relabel_is_rejected(self):
        raw = self.fixture()
        raw["dataset_kind"] = "PUBLIC_OPEN"
        with self.assertRaisesRegex(MultiSpectrumError, "only SYNTHETIC"):
            submission_preview_rows(self.contract(), raw)

    def test_caller_authored_provenance_cannot_widen_public_open_admission(self):
        raw = self.fixture()
        raw["dataset_kind"] = "PUBLIC_OPEN"
        raw["source_manifest"] = {
            "source_url": "https://example.invalid/public.mgf",
            "sha256": "0" * 64,
            "observed_at_utc": "2026-09-17T00:00:00Z",
            "license": "CC0-1.0",
            "use_class": "PUBLIC_RESEARCH",
        }
        with self.assertRaises(MultiSpectrumError):
            normalize_fixture(raw)

    def test_private_label_cannot_promote(self):
        raw = self.fixture()
        raw["dataset_kind"] = "PRIVATE"
        with self.assertRaises(MultiSpectrumError):
            normalize_fixture(raw)

    def test_forged_result_schema_cannot_enter_preview(self):
        forged = {
            "schema": RESULT_SCHEMA,
            "dataset_kind": "SYNTHETIC",
            "rows": [{"molecule_id": "FORGED", "ranking": [{"smiles": "C"}]}],
            "result_sha256": "0" * 64,
        }
        with self.assertRaisesRegex(MultiSpectrumError, "fixture shape/schema mismatch"):
            submission_preview_rows(self.contract(), forged)

    def test_even_valid_stale_result_receipt_cannot_enter_preview(self):
        stale = self.result()
        core = dict(stale)
        receipt = core.pop("result_sha256")
        self.assertEqual(digest(core), receipt)
        with self.assertRaisesRegex(MultiSpectrumError, "fixture shape/schema mismatch"):
            render_submission_preview_csv(self.contract(), stale)

    def test_more_than_sixteen_query_spectra_is_rejected(self):
        raw = self.fixture()
        raw["molecules"][0]["spectra"] = [
            copy.deepcopy(raw["molecules"][0]["spectra"][0]) for _ in range(17)
        ]
        with self.assertRaises(MultiSpectrumError):
            run_multispectrum_baseline(raw)

    def test_duplicate_molecule_id_is_rejected(self):
        raw = self.fixture()
        raw["molecules"].append(copy.deepcopy(raw["molecules"][0]))
        with self.assertRaises(MultiSpectrumError):
            run_multispectrum_baseline(raw)

    def test_missing_expected_candidate_is_rejected(self):
        raw = self.fixture()
        raw["molecules"][0]["expected_candidate_id"] = "C-Z"
        with self.assertRaises(MultiSpectrumError):
            run_multispectrum_baseline(raw)

    def test_unsorted_or_duplicate_peaks_fail_closed(self):
        for peaks in ([[80, 1], [70, 2]], [[70, 1], [70, 2]]):
            raw = self.fixture()
            raw["molecules"][0]["spectra"][0]["peaks"] = peaks
            with self.subTest(peaks=peaks), self.assertRaises(MultiSpectrumError):
                run_multispectrum_baseline(raw)

    def test_bool_numeric_alias_fails_closed(self):
        raw = self.fixture()
        raw["fragment_tolerance_da"] = True
        with self.assertRaises(MultiSpectrumError):
            normalize_fixture(raw)

    def test_submission_preview_is_one_row_per_molecule_with_exact_columns(self):
        rows = submission_preview_rows(self.contract(), self.fixture())
        self.assertEqual([row["molecule_id"] for row in rows], ["M-001", "M-002"])
        self.assertTrue(all(1 <= len(row["smiles"].split(";")) <= 25 for row in rows))
        rendered = render_submission_preview_csv(self.contract(), self.fixture())
        parsed = list(csv.DictReader(io.StringIO(rendered)))
        self.assertEqual(list(parsed[0]), ["molecule_id", "smiles"])
        self.assertEqual(len(parsed), 2)

    def test_submission_preview_dedupes_and_caps_at_twenty_five_after_recompile(self):
        raw = self.fixture()
        template = copy.deepcopy(raw["candidates"][0])
        for i in range(30):
            row = copy.deepcopy(template)
            row["candidate_id"] = f"X-{i:02d}"
            row["smiles"] = "N" if i in (0, 1) else ("N" + "C" * i)
            raw["candidates"].append(row)
        rows = submission_preview_rows(self.contract(), raw)
        values = rows[0]["smiles"].split(";")
        self.assertEqual(len(values), 25)
        self.assertEqual(len(values), len(set(values)))

    def test_submission_unsafe_separator_or_newline_is_rejected_before_preview(self):
        raw = self.fixture()
        raw["candidates"][0]["smiles"] = "C;C"
        with self.assertRaises(MultiSpectrumError):
            render_submission_preview_csv(self.contract(), raw)
        raw = self.fixture()
        raw["candidates"][0]["smiles"] = "C\nC"
        with self.assertRaises(MultiSpectrumError):
            submission_preview_rows(self.contract(), raw)

    def test_strict_loader_rejects_duplicate_keys_and_nonfinite(self):
        with tempfile.TemporaryDirectory() as td:
            dup = Path(td) / "dup.json"
            dup.write_text('{"a":1,"a":2}', encoding="utf-8")
            with self.assertRaises(MultiSpectrumError):
                read_json(dup)
            nan = Path(td) / "nan.json"
            nan.write_text('{"a":NaN}', encoding="utf-8")
            with self.assertRaises(MultiSpectrumError):
                read_json(nan)

    @unittest.skipUnless(hasattr(os, "mkfifo"), "POSIX FIFO required")
    def test_fifo_input_fails_promptly(self):
        with tempfile.TemporaryDirectory() as td:
            fifo = Path(td) / "pipe"
            os.mkfifo(fifo)
            with self.assertRaises(MultiSpectrumError):
                read_json(fifo)

    def test_cli_baseline_and_preview(self):
        baseline = subprocess.run(
            [sys.executable, str(MODULE), "baseline", str(CONTRACT), str(FIXTURE)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(baseline.returncode, 0, baseline.stderr)
        payload = json.loads(baseline.stdout)
        self.assertEqual(payload["mrr_at_25"], 1.0)
        self.assertFalse(payload["competition_score_claimed"])

        preview = subprocess.run(
            [sys.executable, str(MODULE), "preview", str(CONTRACT), str(FIXTURE)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(preview.returncode, 0, preview.stderr)
        rows = list(csv.DictReader(io.StringIO(preview.stdout)))
        self.assertEqual(len(rows), 2)
        self.assertEqual(list(rows[0]), ["molecule_id", "smiles"])

    def test_cli_public_open_label_fails_closed(self):
        raw = self.fixture()
        raw["dataset_kind"] = "PUBLIC_OPEN"
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "public-open.json"
            path.write_text(json.dumps(raw), encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, str(MODULE), "preview", str(CONTRACT), str(path)],
                capture_output=True,
                text=True,
                timeout=10,
            )
        self.assertEqual(proc.returncode, 2)
        self.assertIn("only SYNTHETIC", proc.stderr)


if __name__ == "__main__":
    unittest.main()
