import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from revenue.land_bank_online_library import EvidenceRef, PaidWorkshare, PrimeCandidate, SourceCustody, compile_readiness
from revenue.land_bank_online_library.cli import compile_from_dict
from revenue.land_bank_online_library.core import REQUIRED_PRIME_EVIDENCE, WORKSHARE_DELIVERABLES


def ref(label="Synthetic", locator="fixture://evidence/1"):
    return EvidenceRef(label=label, locator=locator, note="unit-test fixture only")


def good_prime(**changes):
    evidence = {key: ref(key, f"fixture://prime/{key}") for key in REQUIRED_PRIME_EVIDENCE}
    values = {"legal_name": "Synthetic Candidate Prime", "evidence": evidence}
    values.update(changes)
    return PrimeCandidate(**values)


def good_workshare(**changes):
    values = dict(
        owner="TJLabs",
        deliverables=WORKSHARE_DELIVERABLES,
        acceptance_criteria=("all agreed requirements map to retained evidence", "unresolved facts remain HOLD"),
        exclusions=("prime procurement returnables", "legal-content licensing rights", "buyer submission"),
    )
    values.update(changes)
    return PaidWorkshare(**values)


def retained_source(path, expected=""):
    return SourceCustody(
        candidate_buyer_source_path=str(path),
        candidate_buyer_source_label="Synthetic retained candidate",
        candidate_buyer_source_locator="fixture://candidate/tender.pdf",
        expected_sha256=expected,
        secondary_listing_refs=(ref("Listing", "fixture://listing"),),
    )


def cli_payload(source_path=None, expected_sha256=""):
    return {
        "source_custody": {
            "candidate_buyer_source_path": source_path,
            "candidate_buyer_source_label": "Synthetic retained candidate",
            "candidate_buyer_source_locator": "fixture://candidate/tender.pdf",
            "expected_sha256": expected_sha256,
            "secondary_listing_refs": [{"label": "Listing", "locator": "fixture://listing", "note": "discovery"}],
        },
        "prime": {
            "legal_name": "Synthetic Candidate Prime",
            "evidence": {
                key: {"label": key, "locator": f"fixture://prime/{key}", "note": "candidate evidence"}
                for key in REQUIRED_PRIME_EVIDENCE
            },
        },
        "paid_workshare": {
            "owner": "TJLabs",
            "deliverables": list(WORKSHARE_DELIVERABLES),
            "acceptance_criteria": ["retain evidence", "fail closed"],
            "exclusions": ["prime qualification", "submission"],
            "commercial_state": "PAID_SCOPE_TO_BE_AGREED",
        },
    }


class SourceCustodyTests(unittest.TestCase):
    def test_missing_retained_file_holds(self):
        result = SourceCustody(None, "Candidate", "fixture://candidate").result()
        self.assertEqual(result["status"], "HOLD")
        self.assertFalse(result["buyer_source_authority_established"])

    def test_arbitrary_claimed_digest_is_not_an_input_surface(self):
        data = cli_payload(None)
        data["source_custody"]["authoritative_tender_ref"] = {
            "label": "Tender",
            "locator": "fixture://not-retained.pdf",
            "sha256": "a" * 64,
        }
        with self.assertRaises(ValueError):
            compile_from_dict(data)

    def test_regular_file_digest_is_computed_from_bytes(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "tender.pdf"
            raw = b"buyer-byte-candidate\n"
            path.write_bytes(raw)
            result = retained_source(path).result()
        self.assertEqual(result["status"], "RETAINED_SOURCE_CANDIDATE_HASHED")
        self.assertEqual(result["retained_candidate"]["sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(result["retained_candidate"]["byte_size"], len(raw))
        self.assertFalse(result["buyer_source_authority_established"])

    def test_matching_expected_digest_only_constrains_actual_file(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "tender.pdf"
            raw = b"candidate"
            path.write_bytes(raw)
            result = retained_source(path, hashlib.sha256(raw).hexdigest()).result()
        self.assertEqual(result["status"], "RETAINED_SOURCE_CANDIDATE_HASHED")

    def test_wrong_expected_digest_holds(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "tender.pdf"
            path.write_bytes(b"candidate")
            result = retained_source(path, "a" * 64).result()
        self.assertEqual(result["status"], "HOLD")
        self.assertIsNone(result["retained_candidate"])

    def test_symlink_candidate_holds(self):
        if not hasattr(os, "symlink"):
            self.skipTest("symlink unsupported")
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "real.pdf"
            link = Path(td) / "link.pdf"
            target.write_bytes(b"candidate")
            try:
                os.symlink(target, link)
            except OSError:
                self.skipTest("symlink unavailable")
            result = retained_source(link).result()
        self.assertEqual(result["status"], "HOLD")

    def test_fifo_candidate_is_rejected_without_read(self):
        if not hasattr(os, "mkfifo"):
            self.skipTest("fifo unsupported")
        with tempfile.TemporaryDirectory() as td:
            fifo = Path(td) / "pipe"
            os.mkfifo(fifo)
            result = retained_source(fifo).result()
        self.assertEqual(result["status"], "HOLD")

    def test_sparse_oversize_candidate_holds_from_metadata(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "large.pdf"
            with open(path, "wb") as handle:
                handle.truncate(67_108_865)
            result = retained_source(path).result()
        self.assertEqual(result["status"], "HOLD")


class PrimeAndWorkshareTests(unittest.TestCase):
    def test_complete_prime_rows_are_inventory_not_qualification(self):
        result = good_prime().result()
        self.assertEqual(result["status"], "PRIME_EVIDENCE_INVENTORY_COMPLETE")
        self.assertFalse(result["prime_qualification_established"])

    def test_missing_prime_evidence_holds_inventory(self):
        result = PrimeCandidate("", {}).result()
        self.assertEqual(result["status"], "HOLD")
        self.assertIn("missing_legal_name", result["blockers"])

    def test_unknown_prime_evidence_key_holds(self):
        prime = good_prime()
        evidence = dict(prime.evidence)
        evidence["self_attested_magic"] = ref()
        result = PrimeCandidate(prime.legal_name, evidence).result()
        self.assertEqual(result["status"], "HOLD")
        self.assertIn("unknown_prime_evidence_keys", result["blockers"])

    def test_free_workshare_state_holds(self):
        result = good_workshare(commercial_state="FREE_DISCOVERY").result()
        self.assertEqual(result["status"], "HOLD")
        self.assertIn("unsupported_commercial_state", result["blockers"])

    def test_unknown_workshare_deliverable_holds(self):
        result = good_workshare(deliverables=WORKSHARE_DELIVERABLES + ("buyer_submission",)).result()
        self.assertEqual(result["status"], "HOLD")


class AuthorityBoundaryTests(unittest.TestCase):
    def test_even_complete_internal_packet_cannot_authorize_submission(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "candidate.pdf"
            path.write_bytes(b"candidate")
            pack = compile_readiness(
                source_custody=retained_source(path),
                prime=good_prime(),
                workshare=good_workshare(),
            )
        self.assertEqual(pack["teaming_status"], "TEAMING_WORKSHARE_PACKET_READY_FOR_REVIEW")
        self.assertEqual(pack["prime_review_status"], "EVIDENCE_INVENTORY_READY_FOR_EXTERNAL_QUALIFICATION_REVIEW")
        self.assertEqual(pack["submission_status"], "HOLD_EXTERNAL_PRIME_AUTHORITY_REQUIRED")
        self.assertTrue(all(value is False for value in pack["external_authority"].values()))

    def test_submission_authority_booleans_are_rejected_at_schema_boundary(self):
        data = cli_payload(None)
        data["submission_authority"] = {
            "buyer_submission_instructions_verified": True,
            "authorized_signatory_confirmed": True,
            "prime_approved_submission": True,
            "physical_delivery_authorized": True,
        }
        with self.assertRaises(ValueError):
            compile_from_dict(data)

    def test_prime_refs_cannot_change_hard_false_authority(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "candidate.pdf"
            path.write_bytes(b"candidate")
            pack = compile_readiness(
                source_custody=retained_source(path),
                prime=good_prime(),
                workshare=good_workshare(),
            )
        self.assertFalse(pack["external_authority"]["prime_qualification_established"])
        self.assertFalse(pack["external_authority"]["submission_authority_established"])
        self.assertFalse(pack["external_authority"]["revenue_established"])

    def test_receipt_is_deterministic_for_same_retained_bytes_and_metadata(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "candidate.pdf"
            path.write_bytes(b"candidate")
            kwargs = dict(source_custody=retained_source(path), prime=good_prime(), workshare=good_workshare())
            one = compile_readiness(**kwargs)["receipt_sha256"]
            two = compile_readiness(**kwargs)["receipt_sha256"]
        self.assertEqual(one, two)


class CliTests(unittest.TestCase):
    def _run(self, payload):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "input.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            return subprocess.run(
                [sys.executable, "-S", "-m", "revenue.land_bank_online_library.cli", str(path)],
                capture_output=True,
                text=True,
                check=False,
            )

    def test_real_hold_fixture_returns_rc2_and_no_traceback(self):
        fixture = Path("revenue/land_bank_online_library/example_hold.json")
        result = subprocess.run(
            [sys.executable, "-S", "-m", "revenue.land_bank_online_library.cli", str(fixture)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 2, msg=result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        pack = json.loads(result.stdout)
        self.assertEqual(pack["teaming_status"], "HOLD")
        self.assertEqual(pack["submission_status"], "HOLD_EXTERNAL_PRIME_AUTHORITY_REQUIRED")

    def test_fully_self_authored_v1_style_json_cannot_get_rc0(self):
        data = cli_payload(None)
        data["source_custody"] = {
            "authoritative_tender_ref": {
                "label": "Tender",
                "locator": "fixture://not-retained.pdf",
                "sha256": "a" * 64,
            }
        }
        data["submission_authority"] = {
            "buyer_submission_instructions_verified": True,
            "authorized_signatory_confirmed": True,
            "prime_approved_submission": True,
            "physical_delivery_authorized": True,
        }
        result = self._run(data)
        self.assertEqual(result.returncode, 2)
        self.assertIn("ERROR:", result.stdout)
        self.assertNotIn("Traceback", result.stderr)
        self.assertNotIn("SUBMISSION_READY", result.stdout)

    def test_even_complete_local_review_packet_returns_rc2_and_submission_hold(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "candidate.pdf"
            source.write_bytes(b"candidate")
            data = cli_payload(str(source))
            input_path = Path(td) / "input.json"
            input_path.write_text(json.dumps(data), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, "-S", "-m", "revenue.land_bank_online_library.cli", str(input_path)],
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(result.returncode, 2, msg=result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        pack = json.loads(result.stdout)
        self.assertEqual(pack["teaming_status"], "TEAMING_WORKSHARE_PACKET_READY_FOR_REVIEW")
        self.assertEqual(pack["submission_status"], "HOLD_EXTERNAL_PRIME_AUTHORITY_REQUIRED")
        self.assertTrue(all(value is False for value in pack["external_authority"].values()))

    def test_ref_sha256_field_is_rejected_not_laundered(self):
        data = cli_payload(None)
        data["prime"]["evidence"][REQUIRED_PRIME_EVIDENCE[0]]["sha256"] = "a" * 64
        result = self._run(data)
        self.assertEqual(result.returncode, 2)
        self.assertIn("ERROR:", result.stdout)

    def test_scalar_json_returns_rc2(self):
        result = self._run([])
        self.assertEqual(result.returncode, 2)
        self.assertIn("ERROR:", result.stdout)
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
