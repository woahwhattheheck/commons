from __future__ import annotations

"""Regression harness for the NASPO SW1045 v1 trust-root recovery.

All legacy hostile/boundary tests are retained unchanged in
qualification_tests_v1.py.  The three legacy tests that expected caller-made
metadata to mint READY are replaced below with predecessor killers asserting
that the metadata-only v1 compiler stays fail closed.
"""
import unittest

from opportunities.naspo_sw1045_qualification_2026 import qualification as q
from opportunities.naspo_sw1045_qualification_2026 import qualification_tests_v1 as _legacy


def _prime_metadata_cannot_mint_ready(self):
    s, a, r = _legacy.ready_packet()
    o = _legacy.owner(team=False, cats=["CATEGORY_1_CONSULTING"])
    o["public_sector_references"] = [_legacy.ref()]
    o["personnel_evidence"] = [_legacy.staff()]
    o["mandatory_requirement_evidence"] = [_legacy.mreq("CATEGORY_1_CONSULTING", "C1-EXP")]
    rec = q.evaluate(s, a, r, o, trusted_now=_legacy.NOW)
    self.assertFalse(rec["official_packet_ready"])
    self.assertEqual(rec["route_states"]["PRIME_CATEGORY_1_CONSULTING"], q.HOLD_PACKET)
    self.assertEqual(rec["state"], q.HOLD_PACKET)
    self.assertNotEqual(rec["recommended_route"], "PRIME_CATEGORY_1_CONSULTING")


def _category_metadata_cannot_mint_ready(self):
    s, a, r = _legacy.ready_packet()
    o = _legacy.owner(team=False, cats=["CATEGORY_1_CONSULTING", "CATEGORY_2_SERVICES"])
    o["public_sector_references"] = [_legacy.ref()]
    o["personnel_evidence"] = [_legacy.staff()]
    o["mandatory_requirement_evidence"] = [_legacy.mreq("CATEGORY_1_CONSULTING", "C1-EXP")]
    rec = q.evaluate(s, a, r, o, trusted_now=_legacy.NOW)
    self.assertFalse(rec["official_packet_ready"])
    self.assertEqual(rec["route_states"]["PRIME_CATEGORY_1_CONSULTING"], q.HOLD_PACKET)
    self.assertEqual(rec["route_states"]["PRIME_CATEGORY_2_SERVICES"], q.HOLD_PACKET)
    self.assertEqual(rec["state"], q.HOLD_PACKET)


def _partner_metadata_cannot_mint_ready(self):
    s, a, r = _legacy.ready_packet()
    o = _legacy.owner(team=True, cats=[])
    o["prime_partner"] = {
        "status": "COMMITTED",
        "organization_ref": "partner:opaque",
        "commitment_evidence_ref": "evidence:commit",
        "commitment_evidence_sha256": _legacy.H("6"),
        "public_sector_prime_track_record": ["evidence-bound public-sector prime record"],
        "cooperative_contract_admin_evidence_ref": "evidence:coop-admin",
        "cooperative_contract_admin_evidence_sha256": _legacy.H("7"),
    }
    rec = q.evaluate(s, a, r, o, trusted_now=_legacy.NOW)
    self.assertFalse(rec["official_packet_ready"])
    self.assertEqual(rec["state"], q.TEAM_DRAFT)
    self.assertNotEqual(rec["state"], q.TEAM_READY)


# Replace only the three unsafe legacy expectations.  Keep every other test,
# helper, and hostile input from the original carrier unchanged.
_legacy.RouteTests.test_prime_cat1_ready_only_after_packet_and_exact_requirement_evidence = _prime_metadata_cannot_mint_ready
_legacy.RouteTests.test_category1_evidence_does_not_bleed_to_category2 = _category_metadata_cannot_mint_ready
_legacy.RouteTests.test_partner_committed_plus_packet_can_be_teaming_ready = _partner_metadata_cannot_mint_ready

RouteTests = _legacy.RouteTests
SourceAuthorityTests = _legacy.SourceAuthorityTests
FreshnessTests = _legacy.FreshnessTests
EvidenceTests = _legacy.EvidenceTests
DraftCompletenessTests = _legacy.DraftCompletenessTests
JsonBoundaryTests = _legacy.JsonBoundaryTests
FileBoundaryTests = _legacy.FileBoundaryTests


class TrustRootCeilingTests(unittest.TestCase):
    def test_packet_ready_is_never_authenticated_by_metadata_only_v1(self):
        s, a, r = _legacy.ready_packet()
        self.assertFalse(q.packet_ready(s, a, r))

    def test_verify_recomputes_fail_closed_policy(self):
        s, a, r = _legacy.ready_packet()
        o = _legacy.owner(team=True, cats=[])
        rec = q.evaluate(s, a, r, o, trusted_now=_legacy.NOW)
        self.assertTrue(q.verify(s, a, r, o, rec, trusted_now=_legacy.NOW))
        self.assertFalse(rec["official_packet_ready"])


if __name__ == "__main__":
    unittest.main()
