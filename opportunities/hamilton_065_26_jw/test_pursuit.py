from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from opportunities.hamilton_065_26_jw import pursuit as p


class HamiltonPursuitTests(unittest.TestCase):
    AS_OF = "2026-09-17T06:00:00Z"

    def owner(self):
        return {
            "schema": p.OWNER_SCHEMA,
            "organization_ref": "tjlabs-owner",
            "capabilities": [],
            "partner": {
                "state": "NONE",
                "partner_ref": None,
                "evidence_sha256": None,
            },
        }

    def proven(self, *ids):
        value = self.owner()
        for index, capability_id in enumerate(ids):
            value["capabilities"].append(
                {
                    "capability_id": capability_id,
                    "state": "PROVEN",
                    "evidence_sha256": hashlib.sha256(
                        f"evidence-{index}".encode()
                    ).hexdigest(),
                    "observed_at_utc": "2026-09-17T05:30:00Z",
                }
            )
        return value

    def test_default_is_controlling_packet_hold(self):
        receipt = p.compile_pursuit(None, as_of=self.AS_OF)
        self.assertEqual("HOLD_CONTROLLING_PACKET", receipt["disposition"])
        self.assertFalse(
            receipt["source_state"]["secondary_facts_are_buyer_requirements"]
        )
        self.assertIn("CONTROLLING_COUNTY_PACKET_NOT_CAPTURED", receipt["reasons"])
        self.assertTrue(all(value is False for value in receipt["authority"].values()))

    def test_even_all_specialist_evidence_cannot_promote_secondary_summary(self):
        receipt = p.compile_pursuit(
            self.proven(*p.ALLOWED_CAPABILITIES), as_of=self.AS_OF
        )
        self.assertEqual("HOLD_CONTROLLING_PACKET", receipt["disposition"])
        self.assertEqual(
            "DISCOVERY_ONLY_NOT_PARTNER_READY", receipt["teaming_posture"]["state"]
        )
        self.assertFalse(receipt["teaming_posture"]["partner_contact_authorized"])

    def test_uncommitted_partner_does_not_carry_commitment_evidence(self):
        owner = self.owner()
        owner["partner"] = {
            "state": "IDENTIFIED_NOT_COMMITTED",
            "partner_ref": "candidate-prime-1",
            "evidence_sha256": "a" * 64,
        }
        with self.assertRaisesRegex(p.PursuitError, "uncommitted partner"):
            p.compile_pursuit(owner, as_of=self.AS_OF)

    def test_committed_partner_still_cannot_promote_missing_buyer_packet(self):
        owner = self.owner()
        owner["partner"] = {
            "state": "COMMITTED",
            "partner_ref": "candidate-prime-1",
            "evidence_sha256": "a" * 64,
        }
        receipt = p.compile_pursuit(owner, as_of=self.AS_OF)
        self.assertEqual("HOLD_CONTROLLING_PACKET", receipt["disposition"])
        self.assertNotIn("NO_EVIDENCE_BOUND_TEAMING_COMMITMENT", receipt["reasons"])

    def test_unknown_owner_keys_cannot_inject_deadline_or_official_status(self):
        owner = self.owner()
        owner["proposal_deadline"] = "2099-01-01"
        with self.assertRaisesRegex(p.PursuitError, "schema/keys drift"):
            p.compile_pursuit(owner, as_of=self.AS_OF)

    def test_duplicate_capability_id_rejected(self):
        owner = self.proven("api_integration")
        owner["capabilities"].append(copy.deepcopy(owner["capabilities"][0]))
        with self.assertRaisesRegex(p.PursuitError, "duplicate capability_id"):
            p.compile_pursuit(owner, as_of=self.AS_OF)

    def test_non_proven_capability_cannot_carry_evidence(self):
        owner = self.owner()
        owner["capabilities"] = [
            {
                "capability_id": "api_integration",
                "state": "UNKNOWN",
                "evidence_sha256": "b" * 64,
                "observed_at_utc": None,
            }
        ]
        with self.assertRaisesRegex(p.PursuitError, "non-PROVEN"):
            p.compile_pursuit(owner, as_of=self.AS_OF)

    def test_future_owner_evidence_rejected(self):
        owner = self.proven("api_integration")
        owner["capabilities"][0]["observed_at_utc"] = "2026-09-18T05:30:00Z"
        with self.assertRaisesRegex(p.PursuitError, "future evidence"):
            p.compile_pursuit(owner, as_of=self.AS_OF)

    def test_as_of_before_retained_observation_rejected(self):
        with self.assertRaisesRegex(p.PursuitError, "predates retained"):
            p.compile_pursuit(None, as_of="2026-09-17T04:59:59Z")

    def test_receipt_is_order_invariant_for_capabilities(self):
        owner = self.proven(
            "observability_evidence", "api_integration", "migration_cutover"
        )
        a = p.compile_pursuit(owner, as_of=self.AS_OF)
        owner["capabilities"].reverse()
        b = p.compile_pursuit(owner, as_of=self.AS_OF)
        self.assertEqual(p.canonical_bytes(a), p.canonical_bytes(b))

    def test_verify_recompiles_exact_inputs(self):
        owner = self.proven("api_integration")
        receipt = p.compile_pursuit(owner, as_of=self.AS_OF)
        self.assertTrue(p.verify_receipt(receipt, owner, as_of=self.AS_OF))
        receipt["reasons"].append("FORGED")
        with self.assertRaisesRegex(p.PursuitError, "receipt digest mismatch"):
            p.verify_receipt(receipt, owner, as_of=self.AS_OF)

    def test_verify_rejects_different_owner_evidence(self):
        owner = self.proven("api_integration")
        receipt = p.compile_pursuit(owner, as_of=self.AS_OF)
        with self.assertRaisesRegex(
            p.PursuitError, "does not match exact current inputs"
        ):
            p.verify_receipt(receipt, self.owner(), as_of=self.AS_OF)

    def test_retained_authority_tamper_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "authority.json"
            value = p.load_retained_authority()
            value["controlling_packet_status"] = "CAPTURED"
            path.write_bytes(p.canonical_bytes(value))
            with self.assertRaisesRegex(p.PursuitError, "root mismatch"):
                p.compile_pursuit(
                    None, as_of=self.AS_OF, authority_path=path
                )

    def test_duplicate_json_key_rejected(self):
        with self.assertRaisesRegex(p.PursuitError, "duplicate JSON key"):
            p.parse_json_bytes(b'{"schema":"x","schema":"y"}', "fixture")

    def test_markdown_preserves_no_action_truth_boundary(self):
        receipt = p.compile_pursuit(None, as_of=self.AS_OF)
        text = p.render_markdown(receipt)
        self.assertIn("External action authority:** none", text)
        self.assertIn(
            "Secondary discovery is not promoted to a County mandate", text
        )

    def test_create_exclusive_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "out.json"
            path.write_text("keep", encoding="utf-8")
            with self.assertRaisesRegex(p.PursuitError, "exclusive create"):
                p._write_exclusive(path, b"replace")
            self.assertEqual("keep", path.read_text(encoding="utf-8"))

    def test_compile_cli_refuses_mixed_outputs_before_creating_any(self):
        with tempfile.TemporaryDirectory() as td:
            existing = Path(td) / "existing.md"
            fresh = Path(td) / "fresh.json"
            existing.write_text("keep", encoding="utf-8")
            rc = p.main(
                [
                    "compile",
                    "--as-of",
                    self.AS_OF,
                    "--json-out",
                    str(fresh),
                    "--markdown-out",
                    str(existing),
                ]
            )
            self.assertEqual(2, rc)
            self.assertFalse(fresh.exists())
            self.assertEqual("keep", existing.read_text(encoding="utf-8"))

    def test_safe_id_rejects_contact_path_material(self):
        owner = self.owner()
        owner["organization_ref"] = "foo@example.com"
        with self.assertRaises(p.PursuitError):
            p.compile_pursuit(owner, as_of=self.AS_OF)


if __name__ == "__main__":
    unittest.main()
