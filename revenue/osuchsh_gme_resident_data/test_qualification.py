from __future__ import annotations

import unittest

from .core import DataError
from .qualification import qualify_manifest


def sha(char: str) -> str:
    return char * 64


def base_manifest():
    return {
        "opportunity_id": "OSUTUL-RFP-001864-2027",
        "controlling_packet_sha256": None,
        "similar_reference_receipts": [],
        "non_collusion_owner_confirmed": False,
        "portal_registration_confirmed": False,
        "pricing_owner_confirmed": False,
    }


class QualificationTests(unittest.TestCase):
    def test_current_real_state_is_teaming_required(self):
        result = qualify_manifest(base_manifest())
        self.assertEqual(result["status"], "TEAMING_REQUIRED")
        self.assertIn("CONTROLLING_PACKET_NOT_RETAINED", result["holds"])
        self.assertIn("THREE_SIMILAR_REFERENCES_NOT_EVIDENCED", result["holds"])
        self.assertFalse(result["submission_authorized"])

    def test_packet_alone_does_not_make_prime_ready(self):
        manifest = base_manifest()
        manifest["controlling_packet_sha256"] = sha("a")
        self.assertEqual(qualify_manifest(manifest)["status"], "TEAMING_REQUIRED")

    def test_three_refs_but_owner_gates_hold(self):
        manifest = base_manifest()
        manifest["controlling_packet_sha256"] = sha("a")
        manifest["similar_reference_receipts"] = [
            {"organization": f"Org {i}", "scope": "similar data system", "evidence_sha256": sha(str(i))}
            for i in (1, 2, 3)
        ]
        result = qualify_manifest(manifest)
        self.assertEqual(result["status"], "HOLD")
        self.assertNotIn("THREE_SIMILAR_REFERENCES_NOT_EVIDENCED", result["holds"])

    def test_all_evidence_can_reach_prime_evidence_ready_but_never_submit(self):
        manifest = base_manifest()
        manifest.update(
            {
                "controlling_packet_sha256": sha("a"),
                "similar_reference_receipts": [
                    {"organization": f"Org {i}", "scope": "similar data system", "evidence_sha256": sha(str(i))}
                    for i in (1, 2, 3)
                ],
                "non_collusion_owner_confirmed": True,
                "portal_registration_confirmed": True,
                "pricing_owner_confirmed": True,
            }
        )
        result = qualify_manifest(manifest)
        self.assertEqual(result["status"], "PRIME_EVIDENCE_READY")
        self.assertEqual(result["holds"], [])
        self.assertFalse(result["submission_authorized"])
        self.assertFalse(result["buyer_contact_authorized"])

    def test_duplicate_reference_org_rejected(self):
        manifest = base_manifest()
        manifest["similar_reference_receipts"] = [
            {"organization": "Same", "scope": "x", "evidence_sha256": sha("1")},
            {"organization": " same ", "scope": "y", "evidence_sha256": sha("2")},
        ]
        with self.assertRaises(DataError):
            qualify_manifest(manifest)

    def test_bad_sha_rejected(self):
        manifest = base_manifest()
        manifest["controlling_packet_sha256"] = "abc"
        with self.assertRaises(DataError):
            qualify_manifest(manifest)

    def test_extra_key_rejected(self):
        manifest = base_manifest()
        manifest["submission_authorized"] = True
        with self.assertRaises(DataError):
            qualify_manifest(manifest)

    def test_wrong_opportunity_rejected(self):
        manifest = base_manifest()
        manifest["opportunity_id"] = "other"
        with self.assertRaises(DataError):
            qualify_manifest(manifest)

    def test_non_boolean_owner_flag_rejected(self):
        manifest = base_manifest()
        manifest["pricing_owner_confirmed"] = 1
        with self.assertRaises(DataError):
            qualify_manifest(manifest)

    def test_evidence_digest_deterministic(self):
        self.assertEqual(qualify_manifest(base_manifest())["evidence_digest"], qualify_manifest(base_manifest())["evidence_digest"])


if __name__ == "__main__":
    unittest.main()
