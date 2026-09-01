"""Isolation / no-cross-anchoring / child-process contract tests."""

from __future__ import annotations

import unittest

from charttrace.peers.isolation import (
    ALL_ROLE_IDS,
    DISCOVERY_ROLE_IDS,
    SYNTHESIS_ROLE_ID,
    assert_discovery_isolation,
    run_peer_child_process,
    run_peer_in_process,
    stamp_trusted_result,
)
from charttrace.peers.packet import PeerPacket, RecordExcerpt
from charttrace.peers.registry import list_role_ids


def _packet(**kwargs):
    base = dict(
        case_id="syn-case-1",
        jurisdiction="US-federal-context",
        care_date_start="2024-01-01",
        care_date_end="2024-01-31",
        excerpts=[
            RecordExcerpt(
                document_id="note-1",
                page=1,
                source_sha256="a" * 64,
                text="Patient admitted. Critical value pending. Referral recommended.",
                care_phase="acute_care",
                source_category="progress_note",
            )
        ],
        known_facts=["fact:note-1:p1:admitted"],
        source_universe=["progress_note"],
        grounding_pack_ids=["42_cfr_482_24"],
    )
    base.update(kwargs)
    return PeerPacket(**base)


class IsolationTests(unittest.TestCase):
    def test_twelve_roles_registered(self):
        self.assertEqual(len(ALL_ROLE_IDS), 12)
        self.assertEqual(len(DISCOVERY_ROLE_IDS), 11)
        self.assertEqual(set(list_role_ids()), set(ALL_ROLE_IDS))
        self.assertIn(SYNTHESIS_ROLE_ID, ALL_ROLE_IDS)

    def test_discovery_cannot_see_sealed_results(self):
        with self.assertRaises(ValueError):
            assert_discovery_isolation(
                {"sealed_peer_results": [{"role_id": "x"}]},
                "source_provenance",
            )

    def test_discovery_peers_run_without_cross_input(self):
        packet = _packet()
        for role_id in DISCOVERY_ROLE_IDS:
            result = run_peer_in_process(role_id, packet)
            self.assertEqual(result["role_id"], role_id)
            self.assertFalse(result["allows_cross_peer_input"])
            self.assertEqual(result["external_model_calls"], 0)
            self.assertGreaterEqual(len(result["leads"]), 1)

    def test_child_process_contract(self):
        packet = _packet()
        result = run_peer_child_process("medication_allergy", packet)
        self.assertEqual(result["role_id"], "medication_allergy")
        self.assertEqual(result["external_model_calls"], 0)

    def test_spoofed_role_and_model_calls_rejected(self):
        with self.assertRaises(ValueError):
            stamp_trusted_result(
                "source_provenance",
                {
                    "role_id": "synthesis",
                    "schema_version": "attacker.v9",
                    "external_model_calls": 42,
                    "leads": [{"lead_id": "x"}],
                },
            )


if __name__ == "__main__":
    unittest.main()
