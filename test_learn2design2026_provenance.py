"""Real retained provider positives plus fresh-synthesis predecessor killers."""
from __future__ import annotations

import contextlib
import copy
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
EVIDENCE = ROOT / "revenue" / "learn2design2026"
sys.path.insert(0, str(EVIDENCE))
import evidence
import evidence_contract as contract
import evidence_receipts as receipts


class RecordedProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.manifest = contract.expected_manifest()
        self.paths = {label: EVIDENCE / "recorded_runs" / "34938483198" / f"{label}.json"
                      for label in ("serial_v1", "vectorized_v2")}
        self.serial = contract.read_json(self.paths["serial_v1"])
        self.vector = contract.read_json(self.paths["vectorized_v2"])

    def test_real_retained_artifact_members_unchanged(self):
        expected = {"serial_v1": "74ec227c9673c09b26b0f00a6cbb975b67fb3b241a1b237628c96fa8cf8f0c3b",
                    "vectorized_v2": "8a46fca8106e6113a725919efecefe5b1dd1508bcbca80b82f6c297bd937dcbc"}
        for label, path in self.paths.items():
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), expected[label])
            self.assertEqual(contract.canonical_sha256(contract.read_json(path)), expected[label])

    def test_real_provider_receipts_have_independent_recorded_provenance(self):
        for receipt in (self.serial, self.vector):
            proof = receipts.verify_receipt(receipt, self.manifest)
            self.assertEqual(proof["runId"], "34938483198")
            self.assertEqual(proof["artifactId"], "10384626623")
            self.assertEqual(proof["checkoutSha"], "a1e6c04b5b73accfe930567b99f094db076b82bc")
            self.assertIs(proof["historicalEvidence"], True)
            self.assertIs(proof["liveCiStatusAttested"], False)
            self.assertIs(proof["cryptographicExecutionAttestation"], False)

    def test_real_matched_comparison_preserves_observed_result(self):
        out = receipts.compare_receipts(self.serial, self.vector, self.manifest)
        self.assertEqual(out["status"], "RECORDED_MATCHED_PUBLIC_DEVELOPMENT_COMPARISON")
        self.assertIs(out["measurementProvenanceVerified"], True)
        self.assertEqual(out["result"]["lowerBestLoss"], "serial_v1")
        self.assertEqual(out["result"]["serialBestLoss"], 6.441624982498658)
        self.assertEqual(out["result"]["vectorizedBestLoss"], 6.79631273890978)
        self.assertEqual(out["result"]["evalCountDeltaVectorMinusSerial"], 8)
        self.assertTrue(all(value is False for value in out["authority"].values()))
        receipts.verify_comparison(out, self.serial, self.vector, self.manifest)

    def test_comparison_order_is_stable(self):
        self.assertEqual(receipts.compare_receipts(self.serial,self.vector,self.manifest),
                         receipts.compare_receipts(self.vector,self.serial,self.manifest))

    def test_fresh_expected_class_synthesis_is_rejected_without_helper(self):
        forged = []
        for label, loss in (("serial_v1", .001), ("vectorized_v2", .0001)):
            receipt = receipts.base_receipt(self.manifest,label,"MEASURED",True,True,
                {"bestLoss":loss,"evalCount":999999,"budgetExceeded":True,"elapsedSeconds":30.0},
                None,copy.deepcopy(self.serial["environment"]))
            receipts.verify_receipt_integrity(receipt,self.manifest)
            with self.assertRaisesRegex(contract.EvidenceError,"provenance unrecorded"):
                receipts.verify_receipt(receipt,self.manifest)
            forged.append(receipt)
        with self.assertRaises(contract.EvidenceError):
            receipts.compare_receipts(*forged,self.manifest)
        candidate=receipts.compare_candidate_receipts(*forged,self.manifest)
        self.assertEqual(candidate["status"],"UNVERIFIED_CANDIDATE_COMPARISON")
        self.assertIs(candidate["measurementProvenanceVerified"],False)

    def test_helper_does_not_mint_provenance(self):
        receipt=receipts.make_measured_for_test(self.manifest,"serial_v1",1.0,123,
            copy.deepcopy(self.serial["environment"]["runner"]))
        with self.assertRaises(contract.EvidenceError):
            receipts.verify_receipt(receipt,self.manifest)

    def test_rehashed_mutations_do_not_match_recorded_content(self):
        mutations = [
            ("measurement","bestLoss",0.0), ("measurement","evalCount",999),
            ("measurement","elapsedSeconds",1.0), ("measurement","budgetExceeded",False),
            ("runner","githubRunId","999"), ("runner","githubRunAttempt","2"),
            ("runner","githubJob","another-job"), ("runner","python","3.99.0"),
            ("packages","dfbench","99.0"), ("cell","seed",43),
            ("organizer","commit","0"*40), ("candidate","gitBlobSha1","0"*40),
        ]
        for group,key,value in mutations:
            with self.subTest(group=group,key=key):
                receipt=copy.deepcopy(self.serial)
                target=receipt["environment"][group] if group in ("runner","packages") else receipt[group]
                target[key]=value
                receipt=receipts.sign(receipt)
                with self.assertRaises(contract.EvidenceError):
                    receipts.verify_receipt(receipt,self.manifest)

    def test_self_authored_provider_metadata_cannot_replace_record(self):
        receipt=copy.deepcopy(self.serial)
        receipt["measurement"]["bestLoss"]=0.0
        receipt["provenance"]=receipts.verify_receipt(self.serial,self.manifest)
        receipt["measurementProvenanceVerified"]=True
        receipt=receipts.sign(receipt)
        with self.assertRaises(contract.EvidenceError):
            receipts.verify_receipt(receipt,self.manifest)

    def test_returned_provenance_mutation_does_not_change_catalogue(self):
        proof=receipts.verify_receipt(self.serial,self.manifest)
        proof["artifactId"]="fake"
        self.assertEqual(receipts.verify_receipt(self.serial,self.manifest)["artifactId"],"10384626623")

    def test_synthetic_receipt_cannot_mix_with_real_measurement(self):
        other=copy.deepcopy(self.vector);other["measurement"]["bestLoss"]=1.0
        with self.assertRaises(contract.EvidenceError):
            receipts.compare_receipts(self.serial,receipts.sign(other),self.manifest)

    def test_pending_is_integrity_only(self):
        receipt=receipts.base_receipt(self.manifest,"serial_v1","MEASUREMENT_PENDING",True,False,
                                      None,"organizer unavailable",self.serial["environment"])
        receipts.verify_receipt_integrity(receipt,self.manifest)
        with self.assertRaises(contract.EvidenceError):receipts.verify_receipt(receipt,self.manifest)

    def test_rehashed_comparison_cannot_promote_claims(self):
        report=receipts.compare_receipts(self.serial,self.vector,self.manifest)
        for field,value in (("measurementProvenanceVerified",False),("status","OFFICIAL_WINNER")):
            forged=copy.deepcopy(report);forged[field]=value;forged=receipts.sign(forged)
            with self.assertRaises(contract.EvidenceError):
                receipts.verify_comparison(forged,self.serial,self.vector,self.manifest)
        forged=copy.deepcopy(report);forged["result"]["serialBestLoss"]=0.0
        with self.assertRaises(contract.EvidenceError):
            receipts.verify_comparison(receipts.sign(forged),self.serial,self.vector,self.manifest)

    def test_malformed_values_are_evidence_errors(self):
        for receipt in (None,[],{"candidate":[]},{"candidate":{"label":[]}}):
            with self.assertRaises(contract.EvidenceError):receipts.verify_receipt(receipt,self.manifest)
        for field,value in (("bestLoss",True),("evalCount",True),("elapsedSeconds",-1),
                            ("elapsedSeconds",float("nan")),("budgetExceeded",1)):
            receipt=copy.deepcopy(self.serial);receipt["measurement"][field]=value
            with self.assertRaises(contract.EvidenceError):
                receipts.verify_receipt_integrity(receipts.sign(receipt),self.manifest)

    def test_integer_zero_is_not_false_authority(self):
        receipt=copy.deepcopy(self.serial);receipt["authority"]["officialScoreClaimed"]=0
        with self.assertRaises(contract.EvidenceError):
            receipts.verify_receipt_integrity(receipts.sign(receipt),self.manifest)

    def test_candidate_comparison_rejects_package_mismatch(self):
        other=copy.deepcopy(self.vector);other["environment"]["packages"]["jax"]="other"
        with self.assertRaisesRegex(contract.EvidenceError,"package environments differ"):
            receipts.compare_candidate_receipts(self.serial,receipts.sign(other),self.manifest)

    def test_cli_integrity_and_recorded_verification_are_distinct(self):
        # Manifest source-validation is separately covered by the source identity
        # suite. Only that read boundary is replaced here; provenance is never mocked.
        with patch.object(evidence,"validate_manifest",return_value=self.manifest):
            with contextlib.redirect_stdout(io.StringIO()) as out:
                rc=evidence.main(["verify-integrity",str(self.paths["serial_v1"])])
            self.assertEqual(rc,0);self.assertIn("NOT VERIFIED",out.getvalue())
            with contextlib.redirect_stdout(io.StringIO()) as out:
                rc=evidence.main(["verify-receipt",str(self.paths["serial_v1"])])
            self.assertEqual(rc,0);self.assertIn("RECORDED_GITHUB_ACTIONS_ARTIFACT",out.getvalue())

    def test_cli_rejects_forged_pair_without_writing_positive_report(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);fake=copy.deepcopy(self.vector);fake["measurement"]["bestLoss"]=0.0
            fake_path=root/"fake.json";fake_path.write_text(json.dumps(receipts.sign(fake)))
            result=root/"result.json"
            with patch.object(evidence,"validate_manifest",return_value=self.manifest):
                with contextlib.redirect_stderr(io.StringIO()):
                    rc=evidence.main(["compare",str(self.paths["serial_v1"]),str(fake_path),"--out",str(result)])
                self.assertEqual(rc,2);self.assertFalse(result.exists())
                with contextlib.redirect_stdout(io.StringIO()):
                    rc=evidence.main(["compare-candidates",str(self.paths["serial_v1"]),str(fake_path),"--out",str(result)])
                self.assertEqual(rc,0)
                self.assertIs(contract.read_json(result)["measurementProvenanceVerified"],False)


if __name__ == "__main__":
    unittest.main()
