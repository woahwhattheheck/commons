from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "opportunities" / "nysdec_hale_creek_lims" / "carrier.py"
SOURCE_PATH = ROOT / "opportunities" / "nysdec_hale_creek_lims" / "source_snapshot.json"

spec = importlib.util.spec_from_file_location("nysdec_hale_creek_lims_carrier", MODULE_PATH)
assert spec and spec.loader
carrier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(carrier)


class HaleCreekCarrierTests(unittest.TestCase):
    def test_compile_truth_boundary_and_all_questions(self):
        receipt = carrier.compile_from_path(SOURCE_PATH)
        self.assertEqual(receipt["schema"], carrier.RECEIPT_SCHEMA)
        self.assertEqual(receipt["source_sha256"], carrier.SOURCE_SHA256)
        self.assertEqual(receipt["direct_cots_lims_prime_status"], "HOLD")
        self.assertEqual(receipt["teaming_status"], "TEAMING_ROUTE_OPEN_INTERNAL")
        self.assertEqual(receipt["rough_order_of_magnitude"]["status"], "NOT_PRICED")
        self.assertEqual([q["number"] for q in receipt["response_scaffold"]], list(range(1, 29)))
        self.assertTrue(all(value is False for value in receipt["authority"].values()))
        self.assertEqual(receipt["gap_summary"]["supported_internal_questions"], [27])
        self.assertIn("No partner is selected or represented", receipt["response_scaffold"][26]["draft_response"])
        self.assertEqual(
            receipt["internal_engineering_evidence"]["source"]["merge_commit"],
            "3aa038bf56117465a92e4026dda4498932085922",
        )
        self.assertNotIn("$24,000", json.dumps(receipt))
        self.assertNotIn("$6,000", json.dumps(receipt))

    def test_source_byte_change_fails_even_if_json_is_valid(self):
        value = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
        value["opportunity"]["rfi_responses_due"] = "2026-10-21"
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "source.json"
            path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(carrier.CarrierError, "retained generation"):
                carrier.compile_from_path(path)

    def test_duplicate_json_key_rejected(self):
        with self.assertRaisesRegex(carrier.CarrierError, "duplicate JSON key"):
            carrier.parse_json_bytes(b'{"a":1,"a":2}', where="test")

    def test_valid_non_bmp_allowed_but_lone_surrogate_rejected(self):
        value = carrier.parse_json_bytes('{"emoji":"😀"}'.encode("utf-8"), where="test")
        self.assertEqual(value["emoji"], "😀")
        with self.assertRaises(carrier.CarrierError):
            carrier.parse_json_bytes(b'{"bad":"\\ud800"}', where="test")

    def test_code_owned_status_map_cannot_be_promoted_through_source_input(self):
        receipt = carrier.compile_from_path(SOURCE_PATH)
        q15 = receipt["response_scaffold"][14]
        q27 = receipt["response_scaffold"][26]
        self.assertEqual(q15["status"], "EVIDENCE_REQUIRED")
        self.assertEqual(q27["status"], "SUPPORTED_INTERNAL")
        self.assertIn("HOLD", q15["draft_response"])
        self.assertIn("bounded desired role", q27["draft_response"])

    def test_receipt_tamper_is_rejected(self):
        receipt = carrier.compile_from_path(SOURCE_PATH)
        receipt["authority"]["rfi_submission_authorized"] = True
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "receipt.json"
            path.write_text(json.dumps(receipt, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(carrier.CarrierError, "exact recomputed"):
                carrier.verify_receipt(SOURCE_PATH, path)

    def test_rom_promotion_is_rejected(self):
        receipt = carrier.compile_from_path(SOURCE_PATH)
        receipt["rough_order_of_magnitude"] = {"status": "PRICED", "amount_usd": 24000}
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "receipt.json"
            path.write_text(json.dumps(receipt, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(carrier.CarrierError, "exact recomputed"):
                carrier.verify_receipt(SOURCE_PATH, path)

    def test_round_trip_compile_verify(self):
        with tempfile.TemporaryDirectory() as td:
            receipt_path = Path(td) / "receipt.json"
            receipt_path.write_text(
                json.dumps(carrier.compile_from_path(SOURCE_PATH), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            result = carrier.verify_receipt(SOURCE_PATH, receipt_path)
            self.assertTrue(result["valid"])
            self.assertFalse(result["external_authority"])

    def test_real_cli_compile_then_verify(self):
        with tempfile.TemporaryDirectory() as td:
            receipt = Path(td) / "receipt.json"
            compile_run = subprocess.run(
                [sys.executable, str(MODULE_PATH), "compile", "--source", str(SOURCE_PATH), "--output", str(receipt)],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(compile_run.returncode, 0, compile_run.stderr)
            verify_run = subprocess.run(
                [sys.executable, str(MODULE_PATH), "verify", "--source", str(SOURCE_PATH), "--receipt", str(receipt)],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(verify_run.returncode, 0, verify_run.stderr)
            verified = json.loads(verify_run.stdout)
            self.assertTrue(verified["valid"])
            self.assertFalse(verified["external_authority"])


    def test_fifo_swap_after_lstat_fails_closed_without_blocking(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "source.json"
            path.write_bytes(SOURCE_PATH.read_bytes())
            real_open = carrier.os.open
            observed_flags = []

            def swap_to_fifo_then_open(target, flags, *args, **kwargs):
                if Path(target) == path and not observed_flags:
                    observed_flags.append(flags)
                    path.unlink()
                    os.mkfifo(path)
                return real_open(target, flags, *args, **kwargs)

            with patch.object(carrier.os, "open", side_effect=swap_to_fifo_then_open):
                with self.assertRaisesRegex(carrier.CarrierError, "opened input is not a regular file"):
                    carrier.read_regular(path, max_bytes=carrier.MAX_SOURCE_BYTES, where="source")

            self.assertEqual(1, len(observed_flags))
            if hasattr(os, "O_NONBLOCK"):
                self.assertTrue(observed_flags[0] & os.O_NONBLOCK)

    def test_returned_evidence_mutation_cannot_poison_future_recomputation(self):
        poisoned = carrier.compile_from_path(SOURCE_PATH)
        poisoned["internal_engineering_evidence"]["source"]["merge_commit"] = "0" * 40
        poisoned.pop("receipt_sha256")
        poisoned["receipt_sha256"] = carrier.digest(poisoned)

        fresh = carrier.compile_from_path(SOURCE_PATH)
        self.assertEqual(
            "3aa038bf56117465a92e4026dda4498932085922",
            fresh["internal_engineering_evidence"]["source"]["merge_commit"],
        )

        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "poisoned.json"
            path.write_text(json.dumps(poisoned, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(carrier.CarrierError, "exact recomputed"):
                carrier.verify_receipt(SOURCE_PATH, path)

    def test_output_is_create_exclusive(self):
        with tempfile.TemporaryDirectory() as td:
            output = Path(td) / "receipt.json"
            output.write_text("preexisting", encoding="utf-8")
            run = subprocess.run(
                [sys.executable, str(MODULE_PATH), "compile", "--source", str(SOURCE_PATH), "--output", str(output)],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(run.returncode, 2)
            self.assertEqual(output.read_text(encoding="utf-8"), "preexisting")


if __name__ == "__main__":
    unittest.main()
