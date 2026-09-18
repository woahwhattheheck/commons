from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

REPO_ROOT = Path(__file__).resolve().parent
EVIDENCE_ROOT = REPO_ROOT / "revenue" / "learn2design2026"
sys.path.insert(0, str(EVIDENCE_ROOT))

import evidence
import evidence_contract as contract
import evidence_provenance as provenance
import evidence_receipts as receipts


class StrictInputBoundaryTests(unittest.TestCase):
    def _temp_bytes(self, raw: bytes) -> Path:
        tmp = tempfile.NamedTemporaryFile(delete=False)
        tmp.write(raw)
        tmp.close()
        self.addCleanup(lambda: Path(tmp.name).unlink(missing_ok=True))
        return Path(tmp.name)

    def test_recursive_duplicate_keys_rejected(self):
        for raw in (
            b'{"authority":1,"authority":2}\n',
            b'{"outer":{"authority":1,"authority":2}}\n',
        ):
            with self.subTest(raw=raw):
                with self.assertRaises(contract.EvidenceError):
                    contract.read_json(self._temp_bytes(raw))

    def test_lone_surrogate_rejected_at_read_and_canonical_boundaries(self):
        with self.assertRaises(contract.EvidenceError):
            contract.read_json(self._temp_bytes(b'{"x":"\\ud800"}\n'))
        with self.assertRaises(contract.EvidenceError):
            contract.canonical_bytes({"x": "\ud800"})

    def test_recorded_provenance_requires_exact_retained_bytes(self):
        serial_path = EVIDENCE_ROOT / "recorded_runs" / "34938483198" / "serial_v1.json"
        exact = contract.read_json(serial_path)
        proof = provenance.recorded_provenance(exact)
        self.assertEqual(proof["receiptRawSha256"], "74ec227c9673c09b26b0f00a6cbb975b67fb3b241a1b237628c96fa8cf8f0c3b")
        self.assertEqual(proof["receiptCanonicalSha256"], proof["receiptRawSha256"])

        logically_equal = json.loads(serial_path.read_text(encoding="utf-8"))
        self.assertEqual(contract.canonical_sha256(logically_equal), proof["receiptCanonicalSha256"])
        with self.assertRaises(contract.EvidenceError):
            provenance.recorded_provenance(logically_equal)

    def test_resigned_mutation_cannot_inherit_recorded_provenance(self):
        serial_path = EVIDENCE_ROOT / "recorded_runs" / "34938483198" / "serial_v1.json"
        exact = contract.read_json(serial_path)
        mutated = copy.deepcopy(dict(exact))
        mutated["measurement"]["bestLoss"] = 0.0
        resigned = receipts.sign(mutated)
        receipts.verify_receipt_integrity(resigned, contract.expected_manifest())
        with self.assertRaises(contract.EvidenceError):
            provenance.recorded_provenance(resigned)

    def test_cli_verify_rejects_duplicate_key_without_report(self):
        bad = self._temp_bytes(b'{"candidate":{"label":"serial_v1"},"candidate":{"label":"serial_v1"}}\n')
        rc = evidence.main([
            "--repo-root", str(REPO_ROOT),
            "--manifest", str(EVIDENCE_ROOT / "evidence_manifest.json"),
            "verify-receipt", str(bad),
        ])
        self.assertEqual(rc, 2)

    def test_cli_compare_rejects_surrogate_without_writing_report(self):
        bad = self._temp_bytes(b'{"x":"\\ud800"}\n')
        serial = EVIDENCE_ROOT / "recorded_runs" / "34938483198" / "serial_v1.json"
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "report.json"
            rc = evidence.main([
                "--repo-root", str(REPO_ROOT),
                "--manifest", str(EVIDENCE_ROOT / "evidence_manifest.json"),
                "compare", str(serial), str(bad), "--out", str(out),
            ])
            self.assertEqual(rc, 2)
            self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
