import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from revenue.land_bank_online_library import (
    EvidenceRef,
    PaidWorkshare,
    PrimeCandidate,
    SourceCustody,
    SubmissionAuthority,
    compile_readiness,
)
from revenue.land_bank_online_library.core import (
    REQUIRED_PRIME_EVIDENCE,
    WORKSHARE_DELIVERABLES,
)


def ref(label="Synthetic", locator="fixture://evidence/1", hashed=False):
    return EvidenceRef(
        label=label,
        locator=locator,
        sha256_hex="a" * 64 if hashed else "",
        note="unit-test fixture only",
    )


def source_ready():
    return SourceCustody(
        authoritative_tender_ref=ref("Tender", "fixture://tender.pdf", hashed=True),
        annexure_refs=(ref("SLA", "fixture://sla.pdf", hashed=True),),
        secondary_listing_refs=(ref("Listing", "fixture://listing"),),
    )


def good_prime(**changes):
    evidence = {key: ref(key, f"fixture://prime/{key}") for key in REQUIRED_PRIME_EVIDENCE}
    values = {"legal_name": "Synthetic Qualified Prime", "evidence": evidence}
    values.update(changes)
    return PrimeCandidate(**values)


def good_workshare(**changes):
    values = dict(
        owner="TJLabs",
        deliverables=WORKSHARE_DELIVERABLES,
        acceptance_criteria=(
            "all agreed requirements map to retained evidence",
            "unresolved facts remain HOLD",
        ),
        exclusions=(
            "prime procurement returnables",
            "legal-content licensing rights",
            "buyer submission",
        ),
    )
    values.update(changes)
    return PaidWorkshare(**values)


class SourceCustodyTests(unittest.TestCase):
    def test_secondary_listing_never_substitutes_for_buyer_bytes(self):
        result = SourceCustody(
            authoritative_tender_ref=None,
            secondary_listing_refs=(ref("Listing", "https://example.invalid/listing"),),
        ).result()
        self.assertEqual(result["status"], "HOLD")
        self.assertIn("authoritative_tender_bytes_not_retained", result["blockers"])
        self.assertFalse(result["secondary_sources_are_authority"])

    def test_authoritative_source_requires_hash(self):
        result = SourceCustody(authoritative_tender_ref=ref("Tender", "fixture://tender")).result()
        self.assertEqual(result["status"], "HOLD")

    def test_hashed_authoritative_source_passes(self):
        self.assertEqual(source_ready().result()["status"], "SOURCE_BYTES_READY")


class PrimeGateTests(unittest.TestCase):
    def test_missing_prime_evidence_holds(self):
        result = PrimeCandidate(legal_name="", evidence={}).result()
        self.assertEqual(result["status"], "HOLD")
        self.assertIn("missing_legal_name", result["blockers"])
        self.assertTrue(any(x.startswith("missing_prime_evidence:") for x in result["blockers"]))

    def test_unknown_prime_key_fails_closed(self):
        prime = good_prime()
        evidence = dict(prime.evidence)
        evidence["self_attested_magic"] = ref()
        result = PrimeCandidate(prime.legal_name, evidence).result()
        self.assertEqual(result["status"], "HOLD")
        self.assertIn("unknown_prime_evidence_keys", result["blockers"])

    def test_complete_synthetic_prime_can_reach_evidence_ready(self):
        self.assertEqual(good_prime().result(True)["status"], "PRIME_EVIDENCE_READY")


class WorkshareTests(unittest.TestCase):
    def test_free_discovery_is_not_a_valid_workshare_state(self):
        result = good_workshare(commercial_state="FREE_DISCOVERY").result()
        self.assertEqual(result["status"], "HOLD")
        self.assertIn("unsupported_commercial_state", result["blockers"])

    def test_missing_one_deliverable_holds(self):
        result = good_workshare(deliverables=WORKSHARE_DELIVERABLES[:-1]).result()
        self.assertEqual(result["status"], "HOLD")
        self.assertIn("missing_workshare_deliverables", result["blockers"])

    def test_unknown_deliverable_holds(self):
        result = good_workshare(deliverables=WORKSHARE_DELIVERABLES + ("buyer_submission",)).result()
        self.assertEqual(result["status"], "HOLD")
        self.assertIn("unknown_workshare_deliverables", result["blockers"])


class ReadinessTests(unittest.TestCase):
    def test_missing_source_blocks_teaming_even_when_workshare_is_good(self):
        pack = compile_readiness(
            source_custody=SourceCustody(None),
            prime=good_prime(),
            workshare=good_workshare(),
        )
        self.assertEqual(pack["teaming_status"], "HOLD")
        self.assertIn("source_custody", pack["teaming_blockers"])

    def test_teaming_packet_can_be_ready_while_prime_is_hold(self):
        pack = compile_readiness(
            source_custody=source_ready(),
            prime=PrimeCandidate("", {}),
            workshare=good_workshare(),
            authority_root=True,
        )
        self.assertEqual(pack["teaming_status"], "TEAMING_PACKET_READY")
        self.assertEqual(pack["response_status"], "HOLD")
        self.assertEqual(pack["submission_status"], "HOLD")

    def test_prime_response_can_be_ready_without_submission_authority(self):
        pack = compile_readiness(
            source_custody=source_ready(),
            prime=good_prime(),
            workshare=good_workshare(),
            authority_root=True,
        )
        self.assertEqual(pack["response_status"], "PRIME_RESPONSE_ASSEMBLY_READY")
        self.assertEqual(pack["submission_status"], "HOLD")

    def test_submission_requires_exact_true_flags(self):
        auth = SubmissionAuthority(
            buyer_submission_instructions_verified="yes",  # type: ignore[arg-type]
            authorized_signatory_confirmed=True,
            prime_approved_submission=True,
            physical_delivery_authorized=True,
        )
        pack = compile_readiness(
            source_custody=source_ready(),
            prime=good_prime(),
            workshare=good_workshare(),
            submission_authority=auth,
        )
        self.assertEqual(pack["submission_status"], "HOLD")
        self.assertIn(
            "buyer_submission_instructions_verified:not_confirmed",
            pack["submission_authority"]["blockers"],
        )

    def test_complete_synthetic_path_can_be_submission_ready(self):
        auth = SubmissionAuthority(True, True, True, True)
        pack = compile_readiness(
            source_custody=source_ready(),
            prime=good_prime(),
            workshare=good_workshare(),
            submission_authority=auth,
            authority_root=True,
        )
        self.assertEqual(pack["submission_status"], "SUBMISSION_READY")

    def test_receipt_is_deterministic(self):
        kwargs = dict(
            source_custody=source_ready(),
            prime=good_prime(),
            workshare=good_workshare(),
        )
        self.assertEqual(
            compile_readiness(**kwargs)["receipt_sha256"],
            compile_readiness(**kwargs)["receipt_sha256"],
        )


class CliTests(unittest.TestCase):
    def test_hold_fixture_returns_rc2_without_traceback(self):
        fixture = {
            "source_custody": {
                "authoritative_tender_ref": None,
                "secondary_listing_refs": [
                    {"label": "Public listing", "locator": "https://example.invalid/listing"}
                ],
            },
            "prime": {"legal_name": "", "evidence": {}},
            "paid_workshare": {
                "owner": "TJLabs",
                "deliverables": list(WORKSHARE_DELIVERABLES),
                "acceptance_criteria": ["retain evidence", "fail closed"],
                "exclusions": ["prime qualification", "submission"],
            },
            "submission_authority": {},
        }
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "hold.json"
            path.write_text(json.dumps(fixture), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, "-S", "-m", "revenue.land_bank_online_library.cli", str(path)],
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(result.returncode, 2, msg=result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        pack = json.loads(result.stdout)
        self.assertEqual(pack["teaming_status"], "HOLD")
        self.assertEqual(pack["submission_status"], "HOLD")

    def test_scalar_json_returns_rc2(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "bad.json"
            path.write_text("[]", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, "-S", "-m", "revenue.land_bank_online_library.cli", str(path)],
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(result.returncode, 2)
        self.assertIn("ERROR:", result.stdout)
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
