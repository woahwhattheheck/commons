"""Lead contract and forbidden-input tests."""

from __future__ import annotations

import unittest

from charttrace.peers.contracts import (
    EvidenceGrade,
    PeerLead,
    RelevanceGrade,
    REQUIRED_LEAD_FIELDS,
    assert_lead_complete,
    detect_forbidden_inputs,
    strip_forbidden_inputs,
)
from charttrace.peers.scope import GLOBAL_SCOPE_STATEMENT


class ContractsTests(unittest.TestCase):
    def test_global_scope_statement_once(self):
        self.assertIn("investigative research aid", GLOBAL_SCOPE_STATEMENT)
        self.assertIn("Licensed counsel", GLOBAL_SCOPE_STATEMENT)
        self.assertIn("qualified clinicians", GLOBAL_SCOPE_STATEMENT)

    def test_forbidden_inputs_stripped(self):
        raw = {
            "case_id": "case-1",
            "price": 999,
            "destination_firm": "Acme LLP",
            "affiliate_identity": "AffiliateX",
            "compensation": 50,
            "excerpts": [{"text": "note", "payment": 1}],
        }
        cleaned = strip_forbidden_inputs(raw)
        self.assertNotIn("price", cleaned)
        self.assertNotIn("destination_firm", cleaned)
        self.assertNotIn("affiliate_identity", cleaned)
        self.assertNotIn("compensation", cleaned)
        self.assertNotIn("payment", cleaned["excerpts"][0])
        found = detect_forbidden_inputs(raw)
        self.assertTrue(any(x.endswith("price") or x == "price" for x in found))

    def test_lead_requires_supporting_facts(self):
        with self.assertRaises(ValueError):
            PeerLead(
                lead_id="bad1",
                title="t",
                domain="d",
                care_phase="p",
                cited_observation="obs",
                hypothesis="h",
                review_question="q",
                supporting_facts=(),
                counterevidence=(),
                conflicts=(),
                missing_records=(),
                alternative_explanations=(),
                source_universe_searched=("notes",),
                external_authorities=(),
                jurisdiction_date_scope="US|2020",
                evidence_grade=EvidenceGrade.CLUE,
                relevance_grade=RelevanceGrade.TENUOUS,
                clinical_plausibility="unknown",
                temporal_linkage="unknown",
                peer_version="x@1",
            )

    def test_complete_lead_roundtrip(self):
        lead = PeerLead(
            lead_id="lead-ok-1",
            title="Unsigned addendum",
            domain="provenance",
            care_phase="documentation",
            cited_observation="doc:p1 :: unsigned addendum",
            hypothesis="May reflect delayed authentication.",
            review_question="Is authentication present elsewhere?",
            supporting_facts=("doc:p1 :: unsigned addendum",),
            counterevidence=(),
            conflicts=(),
            missing_records=("signature log",),
            alternative_explanations=("Template artifact",),
            source_universe_searched=("progress_notes",),
            external_authorities=("42_cfr_482_24",),
            jurisdiction_date_scope="US-federal|2024-01-01–2024-02-01",
            evidence_grade=EvidenceGrade.SUPPORTED,
            relevance_grade=RelevanceGrade.PLAUSIBLE,
            clinical_plausibility="documentation signal",
            temporal_linkage="same encounter",
            peer_version="source_provenance@1.1",
            weak_label="weak_or_longshot",
        )
        data = lead.to_dict()
        assert_lead_complete(data)
        self.assertTrue(REQUIRED_LEAD_FIELDS.issubset(data.keys()))
        self.assertEqual(data["evidence_grade"], "SUPPORTED")
        self.assertEqual(data["weak_label"], "weak_or_longshot")


if __name__ == "__main__":
    unittest.main()
