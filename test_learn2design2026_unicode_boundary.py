"""Hostile non-scalar Unicode closure for the Learn2Design evidence verifier."""
from __future__ import annotations

import contextlib
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
EVIDENCE = ROOT / "revenue" / "learn2design2026"
if str(EVIDENCE) not in sys.path:
    sys.path.insert(0, str(EVIDENCE))

import evidence
import evidence_contract as contract


class Learn2DesignUnicodeBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = contract.expected_manifest()
        self.serial_path = EVIDENCE / "recorded_runs" / "34938483198" / "serial_v1.json"
        self.vector_path = EVIDENCE / "recorded_runs" / "34938483198" / "vectorized_v2.json"
        self.serial = contract.read_json(self.serial_path)

    def _hostile_path(self, root: Path) -> Path:
        hostile = copy.deepcopy(self.serial)
        hostile["environment"]["runner"]["platform"] = "\ud800"
        path = root / "hostile-surrogate.json"
        # ensure_ascii keeps the file itself valid UTF-8 while json.loads reconstructs
        # the non-scalar code point that previously escaped canonical UTF-8 encoding.
        path.write_text(json.dumps(hostile, ensure_ascii=True), encoding="utf-8")
        return path

    def test_canonical_json_rejects_non_scalar_unicode_as_evidence_error(self) -> None:
        with self.assertRaises(contract.EvidenceError):
            contract.canonical_bytes({"value": "\ud800"})

    def test_public_verify_cli_closes_escaped_lone_surrogate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            hostile = self._hostile_path(Path(directory))
            with patch.object(evidence, "validate_manifest", return_value=self.manifest):
                stderr = io.StringIO()
                with contextlib.redirect_stderr(stderr):
                    rc = evidence.main(["verify-receipt", str(hostile)])
            self.assertEqual(rc, 2)
            self.assertIn("evidence error:", stderr.getvalue())

    def test_public_compare_cli_closes_escaped_lone_surrogate_without_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            hostile = self._hostile_path(root)
            out = root / "comparison.json"
            with patch.object(evidence, "validate_manifest", return_value=self.manifest):
                stderr = io.StringIO()
                with contextlib.redirect_stderr(stderr):
                    rc = evidence.main([
                        "compare",
                        str(hostile),
                        str(self.vector_path),
                        "--out",
                        str(out),
                    ])
            self.assertEqual(rc, 2)
            self.assertFalse(out.exists())
            self.assertIn("evidence error:", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
