from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import tempfile
import unittest

from .acceptance import make_clean_bundle
from .cli import main
from .core import canonical_json, evaluate


class ConsolidationQACliTests(unittest.TestCase):
    def _write(self, path: Path, value) -> None:
        path.write_bytes(canonical_json(value) + b"\n")

    def test_evaluate_clean_bundle_writes_verifiable_pass_receipt(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            bundle = root / "bundle.json"
            receipt = root / "receipt.json"
            self._write(bundle, make_clean_bundle(6))
            self.assertEqual(0, main(["evaluate", str(bundle), "--output", str(receipt)]))
            row = json.loads(receipt.read_text())
            self.assertEqual("PASS", row["status"])
            self.assertEqual(6, row["migration_candidate_count"])
            self.assertFalse(row["migration_authorized"])

    def test_evaluate_hold_is_written_but_returns_nonzero(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            bundle_row = make_clean_bundle(6)
            bundle_row["batches"][0]["content_sha256"] = "0" * 64
            bundle = root / "bundle.json"
            receipt = root / "receipt.json"
            self._write(bundle, bundle_row)
            self.assertEqual(2, main(["evaluate", str(bundle), "--output", str(receipt)]))
            row = json.loads(receipt.read_text())
            self.assertEqual("HOLD", row["status"])
            self.assertGreater(row["invalid_batch_count"], 0)

    def test_verify_valid_receipt(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            receipt = root / "receipt.json"
            self._write(receipt, evaluate(make_clean_bundle(4)).receipt)
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                self.assertEqual(0, main(["verify", str(receipt)]))
            self.assertTrue(json.loads(stdout.getvalue())["verified"])

    def test_verify_tampered_receipt_returns_three(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            row = evaluate(make_clean_bundle(4)).receipt
            row["migration_candidate_count"] += 1
            receipt = root / "receipt.json"
            self._write(receipt, row)
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                self.assertEqual(3, main(["verify", str(receipt)]))
            self.assertFalse(json.loads(stdout.getvalue())["verified"])

    def test_duplicate_key_input_fails_closed_without_receipt(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            bundle = root / "bundle.json"
            receipt = root / "receipt.json"
            bundle.write_text('{"schema":"x","schema":"y"}', encoding="utf-8")
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                self.assertEqual(4, main(["evaluate", str(bundle), "--output", str(receipt)]))
            self.assertFalse(receipt.exists())
            self.assertIn("DUPLICATE_JSON_KEY", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
