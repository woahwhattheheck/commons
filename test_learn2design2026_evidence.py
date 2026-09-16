from __future__ import annotations

import abc
import copy
import json
from pathlib import Path
import sys
import unittest

REPO_ROOT = Path(__file__).resolve().parent
EVIDENCE_ROOT = REPO_ROOT / "revenue" / "learn2design2026"
sys.path.insert(0, str(EVIDENCE_ROOT))
import evidence_contract as contract
import evidence_receipts as receipts
import evidence


class SourceIdentityTests(unittest.TestCase):
    def test_manifest_and_candidate_bytes_are_exact(self):
        manifest = contract.validate_manifest(EVIDENCE_ROOT / "evidence_manifest.json", REPO_ROOT)
        self.assertEqual(manifest, contract.expected_manifest())
        for label, spec in contract.EXPECTED_CANDIDATES.items():
            source = REPO_ROOT / spec["path"]
            self.assertEqual(contract.git_blob_sha1_bytes(source.read_bytes()), spec["gitBlobSha1"], label)

    def test_frozen_v1_is_exact_merged_baseline(self):
        source = (EVIDENCE_ROOT / "submission_v1.py").read_bytes()
        self.assertEqual(contract.git_blob_sha1_bytes(source), "0e5b0141138c471c9b47163aca4f1a01336dfdf1")

    def test_current_v2_is_exact_merged_successor(self):
        source = (EVIDENCE_ROOT / "submission.py").read_bytes()
        self.assertEqual(contract.git_blob_sha1_bytes(source), "ac814d1f543529a823f7c3afa2a9c4f54c0bfe12")

    def test_authority_ceiling_is_all_false(self):
        self.assertTrue(contract.AUTHORITY)
        self.assertTrue(all(value is False for value in contract.AUTHORITY.values()))


class ReceiptTests(unittest.TestCase):
    def setUp(self):
        self.manifest = contract.expected_manifest()
        self.runner = {
            "python": "3.12.0", "platform": "test", "machine": "x86_64",
            "githubRunId": "123", "githubRunAttempt": "1", "githubJob": "evidence",
            "runnerOs": "Linux", "runnerArch": "X64",
        }

    def measured(self, label: str, loss: float, count: int):
        return receipts.make_measured_for_test(self.manifest, label, best_loss=loss, eval_count=count, runner=self.runner)

    def test_candidate_receipt_integrity_roundtrip(self):
        receipt = self.measured("serial_v1", 1.25, 44)
        receipts.verify_receipt_integrity(receipt, self.manifest)
        self.assertFalse(receipt["authority"]["officialScoreClaimed"])

    def test_digest_tamper_rejected(self):
        receipt = self.measured("serial_v1", 1.25, 44)
        receipt["measurement"]["bestLoss"] = 0.0
        with self.assertRaises(contract.EvidenceError):
            receipts.verify_receipt_integrity(receipt, self.manifest)

    def test_synthetic_evidence_class_rejected_even_if_resigned(self):
        receipt = self.measured("serial_v1", 1.25, 44)
        receipt["evidenceClass"] = "SYNTHETIC_LOCAL"
        receipt = receipts.sign(receipt)
        with self.assertRaises(contract.EvidenceError):
            receipts.verify_receipt_integrity(receipt, self.manifest)

    def test_candidate_label_swap_rejected_even_if_resigned(self):
        receipt = self.measured("serial_v1", 1.25, 44)
        receipt["candidate"]["label"] = "vectorized_v2"
        receipt = receipts.sign(receipt)
        with self.assertRaises(contract.EvidenceError):
            receipts.verify_receipt_integrity(receipt, self.manifest)

    def test_cell_drift_rejected_even_if_resigned(self):
        receipt = self.measured("serial_v1", 1.25, 44)
        receipt["cell"]["seed"] = 7
        receipt = receipts.sign(receipt)
        with self.assertRaises(contract.EvidenceError):
            receipts.verify_receipt_integrity(receipt, self.manifest)

    def test_nonfinite_or_empty_measurement_rejected(self):
        nonfinite = self.measured("serial_v1", 1.0, 2)
        nonfinite["measurement"]["bestLoss"] = float("inf")
        with self.assertRaises(contract.EvidenceError):
            receipts.sign(nonfinite)

        empty = self.measured("serial_v1", 1.0, 2)
        empty["measurement"]["evalCount"] = 0
        empty = receipts.sign(empty)
        with self.assertRaises(contract.EvidenceError):
            receipts.verify_receipt_integrity(empty, self.manifest)

    def test_pending_cannot_be_compared(self):
        serial = self.measured("serial_v1", 1.0, 50)
        vector = self.measured("vectorized_v2", 0.9, 70)
        vector["status"] = "MEASUREMENT_PENDING"
        vector["measurement"] = None
        vector["organizerSourceVerified"] = False
        vector["pendingReason"] = "dependency unavailable"
        vector = receipts.sign(vector)
        receipts.verify_receipt_integrity(vector, self.manifest)
        with self.assertRaises(contract.EvidenceError):
            receipts.compare_candidate_receipts(serial, vector, self.manifest)

    def test_runner_mismatch_rejected(self):
        serial = self.measured("serial_v1", 1.0, 50)
        other = dict(self.runner); other["githubRunId"] = "124"
        vector = receipts.make_measured_for_test(self.manifest, "vectorized_v2", best_loss=.9, eval_count=70, runner=other)
        with self.assertRaises(contract.EvidenceError):
            receipts.compare_candidate_receipts(serial, vector, self.manifest)

    def test_supplied_comparison_is_explicitly_unverified(self):
        serial = self.measured("serial_v1", 1.0, 50)
        vector = self.measured("vectorized_v2", .9, 70)
        out = receipts.compare_candidate_receipts(serial, vector, self.manifest)
        self.assertEqual(out["result"]["lowerBestLoss"], "vectorized_v2")
        self.assertEqual(out["result"]["evalCountDeltaVectorMinusSerial"], 20)
        self.assertIn("execution provenance is unverified", out["interpretation"])
        self.assertEqual(out["status"], "UNVERIFIED_CANDIDATE_COMPARISON")
        self.assertIs(out["measurementProvenanceVerified"], False)
        self.assertTrue(all(v is False for v in out["authority"].values()))
        digest = out.pop("receiptSha256")
        self.assertEqual(digest, contract.canonical_sha256(out))


class EvidenceInitAdapterTests(unittest.TestCase):
    def test_only_abstract_init_is_adapted_without_changing_optimize(self):
        class Legacy(abc.ABC):
            algorithm_str = "legacy"
            @abc.abstractmethod
            def __init__(self):
                raise NotImplementedError
            def optimize(self, objective=None, random_seed=None):
                return (objective, random_seed)
        original_optimize = Legacy.optimize
        instance = evidence.instantiate_candidate(Legacy)
        self.assertEqual(instance.algorithm_str, "legacy")
        self.assertIs(type(instance).optimize, original_optimize)
        self.assertEqual(instance.optimize("obj", 42), ("obj", 42))

    def test_extra_abstract_method_is_rejected(self):
        class Broken(abc.ABC):
            algorithm_str = "broken"
            @abc.abstractmethod
            def __init__(self):
                raise NotImplementedError
            @abc.abstractmethod
            def optimize(self, objective=None, random_seed=None):
                raise NotImplementedError
        with self.assertRaises(contract.EvidenceError):
            evidence.instantiate_candidate(Broken)

    def test_nonabstract_candidate_instantiates_normally(self):
        class Current:
            algorithm_str = "current"
            def __init__(self):
                self.ready = True
            def optimize(self, objective=None, random_seed=None):
                return None
        instance = evidence.instantiate_candidate(Current)
        self.assertTrue(instance.ready)
        self.assertIs(type(instance), Current)


class ContractMutationTests(unittest.TestCase):
    def test_candidate_swap_changes_hard_contract(self):
        manifest = copy.deepcopy(contract.expected_manifest())
        manifest["candidates"]["serial_v1"]["path"] = manifest["candidates"]["vectorized_v2"]["path"]
        self.assertNotEqual(manifest, contract.expected_manifest())

    def test_organizer_revision_drift_changes_hard_contract(self):
        manifest = copy.deepcopy(contract.expected_manifest())
        manifest["organizer"]["commit"] = "0" * 40
        self.assertNotEqual(manifest, contract.expected_manifest())


if __name__ == "__main__":
    unittest.main()
