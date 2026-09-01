"""Tests for the eight-stage review pipeline."""

from __future__ import annotations

import unittest

from charttrace.review.dispositions import Disposition
from charttrace.review.fixtures_synth import (
    base_packet,
    clean_lead,
    weak_grounded_lead,
)
from charttrace.review.pipeline import (
    PACKET_SECTION_ORDER,
    STAGE_NAMES,
    ReviewPipeline,
)


class PipelineTests(unittest.TestCase):
    def test_eight_stages(self) -> None:
        self.assertEqual(len(STAGE_NAMES), 8)

    def test_clean_packet_passes(self) -> None:
        result = ReviewPipeline().run(base_packet())
        self.assertFalse(result.release_blocked)
        self.assertTrue(result.ok)
        self.assertEqual(list(result.packet_sections.keys()), list(PACKET_SECTION_ORDER))
        strong_ids = {
            x["lead_id"] for x in result.packet_sections["strongest_grounded_patterns"]
        }
        self.assertIn("L-clean-1", strong_ids)

    def test_preflight_fails_on_bad_hash(self) -> None:
        packet = base_packet()
        packet["sources"][0]["sha256"] = "short"
        result = ReviewPipeline().run(packet)
        self.assertTrue(result.release_blocked)
        pre = next(s for s in result.stages if s.name == "preflight")
        self.assertFalse(pre.ok)

    def test_forbidden_peer_inputs_fail_discovery(self) -> None:
        packet = base_packet()
        packet["discovery"]["peer_runs"][0]["inputs"]["price"] = 100
        result = ReviewPipeline().run(packet)
        disc = next(s for s in result.stages if s.name == "discovery_input")
        self.assertFalse(disc.ok)
        self.assertTrue(result.release_blocked)

    def test_unsupported_fact_quarantined_never_leaves(self) -> None:
        bad = clean_lead(
            lead_id="L-bad-cite",
            cited_observation="invented diagnosis of zebra syndrome confirmed",
            citations=[{"text": "routine vital signs within normal limits"}],
            band="primary",
        )
        packet = base_packet(leads=[clean_lead(), bad, weak_grounded_lead()])
        result = ReviewPipeline().run(packet)
        self.assertIn("L-bad-cite", result.quarantine_ids)
        for section_items in result.packet_sections.values():
            ids = {i.get("lead_id") for i in section_items if isinstance(i, dict)}
            self.assertNotIn("L-bad-cite", ids)
        strong_ids = {
            i["lead_id"] for i in result.packet_sections["strongest_grounded_patterns"]
        }
        self.assertIn("L-clean-1", strong_ids)

    def test_soft_rejection_blocked_weak_lead_survives_appendix(self) -> None:
        weak = weak_grounded_lead(
            lead_id="L-soft",
            reject_reason_only="not actionable",
            grounded=True,
            band="weak",
        )
        packet = base_packet(leads=[clean_lead(), weak])
        result = ReviewPipeline().run(packet)
        self.assertIn("L-soft", result.appendix_ids)
        appendix_ids = {
            i["lead_id"] for i in result.packet_sections["weak_lead_appendix"]
        }
        self.assertIn("L-soft", appendix_ids)
        soft_rejects = [
            d
            for d in result.dispositions
            if d.item_id == "L-soft"
            and d.disposition == Disposition.REJECT_UNSUPPORTED
        ]
        self.assertEqual(soft_rejects, [])

    def test_dedup_preserves_dissent(self) -> None:
        a = clean_lead(lead_id="L-a", dedup_key="same", hypothesis="Hypothesis A")
        b = clean_lead(
            lead_id="L-b",
            dedup_key="same",
            hypothesis="Hypothesis B dissenting",
            band="secondary",
        )
        packet = base_packet(leads=[a, b])
        result = ReviewPipeline().run(packet)
        synth = next(s for s in result.stages if s.name == "synthesis_dedup")
        self.assertGreaterEqual(synth.details.get("dissent_preserved", 0), 1)
        self.assertTrue(
            any(d.disposition == Disposition.WEAK_APPENDIX for d in synth.dispositions)
        )

    def test_named_human_required_and_counsel_only_legal_fields(self) -> None:
        packet = base_packet()
        packet["release"]["named_human_reviewer"] = None
        result = ReviewPipeline().run(packet)
        self.assertTrue(result.release_blocked)

        packet2 = base_packet(
            leads=[clean_lead(legal_relevance="high", counsel_filled=False)]
        )
        result2 = ReviewPipeline().run(packet2)
        release = next(s for s in result2.stages if s.name == "named_human_release")
        self.assertFalse(release.ok)

    def test_prompt_injection_break_the_packet(self) -> None:
        packet = base_packet()
        packet["adversarial"] = {
            "attacks": [
                {
                    "kind": "prompt_injection",
                    "followed": True,
                    "lead_id": "L-inj",
                }
            ]
        }
        packet["leads"].append(
            clean_lead(lead_id="L-inj", followed_source_prompt=True, band="secondary")
        )
        result = ReviewPipeline().run(packet)
        self.assertIn("L-inj", result.quarantine_ids)
        brk = next(s for s in result.stages if s.name == "break_the_packet")
        self.assertFalse(brk.ok)

    def test_packet_section_order_contract(self) -> None:
        self.assertEqual(
            list(PACKET_SECTION_ORDER),
            [
                "strongest_grounded_patterns",
                "secondary_findings",
                "weak_lead_appendix",
                "counterevidence_alternatives",
                "missing_record_requests",
                "chronology_citation_index",
            ],
        )


if __name__ == "__main__":
    unittest.main()
