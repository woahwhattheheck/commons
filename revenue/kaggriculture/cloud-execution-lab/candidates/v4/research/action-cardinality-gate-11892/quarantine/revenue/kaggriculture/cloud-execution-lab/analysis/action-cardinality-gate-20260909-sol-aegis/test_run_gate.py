from __future__ import annotations

import gzip
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import action_cardinality_gate as gate
import gate_common
from test_support import _replay


class RunGateTests(unittest.TestCase):
    def _write_replay(self, directory: Path, replay: dict, *, gzip_it: bool) -> Path:
        payload = gate.canonical_json_bytes(replay)
        path = directory / ("replay.json.gz" if gzip_it else "replay.json")
        path.write_bytes(gzip.compress(payload, mtime=0) if gzip_it else payload)
        return path

    def test_plain_and_gzip_have_same_analysis(self) -> None:
        replay = _replay([4, 5], [[["PASS"]] * 4, [["WEST"]] * 5], seat=1)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plain = gate.run_gate(self._write_replay(root, replay, gzip_it=False), seat=1)
            zipped = gate.run_gate(self._write_replay(root, replay, gzip_it=True), seat=1)
        self.assertEqual(plain["verdict"], "REJECT")
        self.assertEqual(zipped["verdict"], "REJECT")
        self.assertEqual(plain["analysis"], zipped["analysis"])
        self.assertNotEqual(plain["input"]["raw_sha256"], zipped["input"]["raw_sha256"])

    def test_expected_raw_hash_mismatch_is_invalid(self) -> None:
        replay = _replay([0], [[]], seat=1)
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_replay(Path(tmp), replay, gzip_it=False)
            receipt = gate.run_gate(path, seat=1, expected_sha256="0" * 64)
        self.assertEqual(receipt["verdict"], "INVALID")
        self.assertIn("SHA-256 mismatch", receipt["reason"])

    def test_invalid_expected_hash_shape_is_invalid(self) -> None:
        replay = _replay([0], [[]], seat=1)
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_replay(Path(tmp), replay, gzip_it=False)
            receipt = gate.run_gate(path, seat=1, expected_sha256="ABC")
        self.assertEqual(receipt["verdict"], "INVALID")
        self.assertIn("lowercase hexadecimal", receipt["reason"])

    def test_truncated_gzip_is_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json.gz"
            path.write_bytes(b"\x1f\x8b\x08\x00broken")
            receipt = gate.run_gate(path, seat=1)
        self.assertEqual(receipt["verdict"], "INVALID")
        self.assertIn("invalid gzip", receipt["reason"])

    def test_invalid_json_is_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            path.write_text("{not-json", encoding="utf-8")
            receipt = gate.run_gate(path, seat=1)
        self.assertEqual(receipt["verdict"], "INVALID")
        self.assertIn("valid JSON", receipt["reason"])

    def test_duplicate_json_key_is_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "duplicate.json"
            path.write_text('{"name":"kaggriculture","name":"shadow"}', encoding="utf-8")
            receipt = gate.run_gate(path, seat=1)
        self.assertEqual(receipt["verdict"], "INVALID")
        self.assertIn("duplicate JSON key", receipt["reason"])

    def test_nonfinite_json_number_is_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nan.json"
            path.write_text('{"value":NaN}', encoding="utf-8")
            receipt = gate.run_gate(path, seat=1)
        self.assertEqual(receipt["verdict"], "INVALID")
        self.assertIn("non-finite JSON number", receipt["reason"])

    def test_invalid_utf8_is_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            path.write_bytes(b"\xff\xfe")
            receipt = gate.run_gate(path, seat=1)
        self.assertEqual(receipt["verdict"], "INVALID")
        self.assertIn("not UTF-8", receipt["reason"])

    def test_decoded_gzip_ceiling_is_fail_closed(self) -> None:
        replay = _replay([0], [[]], seat=1)
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_replay(Path(tmp), replay, gzip_it=True)
            with mock.patch.object(gate_common, "MAX_REPLAY_BYTES", 32):
                receipt = gate.run_gate(path, seat=1)
        self.assertEqual(receipt["verdict"], "INVALID")
        self.assertIn("byte", receipt["reason"])

    def test_missing_file_is_invalid(self) -> None:
        receipt = gate.run_gate("/definitely/missing/replay.json", seat=1)
        self.assertEqual(receipt["verdict"], "INVALID")
        self.assertIn("cannot stat replay", receipt["reason"])

    def test_receipt_hash_verifies_and_tamper_fails(self) -> None:
        receipt = gate.seal_receipt({"verdict": "PASS", "count": 3})
        self.assertEqual(gate.verify_receipt(receipt), (True, "receipt hash verified"))
        receipt["count"] = 4
        valid, message = gate.verify_receipt(receipt)
        self.assertFalse(valid)
        self.assertIn("hash mismatch", message)

    def test_receipt_hash_shape_is_strict(self) -> None:
        valid, message = gate.verify_receipt({"receipt_sha256": "G" * 64})
        self.assertFalse(valid)
        self.assertIn("lowercase hexadecimal", message)

    def test_atomic_json_write_round_trip(self) -> None:
        value = gate.seal_receipt({"verdict": "REJECT", "count": 1})
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nested" / "receipt.json"
            gate.atomic_write_json(path, value)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), value)
            self.assertTrue(path.read_bytes().endswith(b"\n"))

    def test_exit_code_mapping(self) -> None:
        self.assertEqual(gate._check_exit_code("PASS"), gate.EXIT_PASS)
        self.assertEqual(gate._check_exit_code("REJECT"), gate.EXIT_REJECT)
        self.assertEqual(gate._check_exit_code("INVALID"), gate.EXIT_INVALID)

if __name__ == "__main__":
    unittest.main()
