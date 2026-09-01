#!/usr/bin/env python3
"""Independent parser and pipeline-determinism locks. No duplicated TestCase import."""

from __future__ import annotations

import unittest

from charttrace.assurance.evaluate import gold_packet, packet_to_canonical_bytes
from charttrace.assurance.pdf_parse import extract_page_texts, pdf_page_count
from charttrace.assurance.pipeline import (
    gold_packet_from_pdfs,
    peer_excerpts_from_pdfs,
    try_lane_b_d_adapters,
)
from charttrace.fixtures.oracle import INJECTION_TEXT, STRUCTURAL, build_oracle, structural_counts
from charttrace.fixtures.pdf_synth import pdf_page_count as synth_page_count


class IndependentPipelineTests(unittest.TestCase):
    def test_independent_parser_recovers_every_generated_pdf(self) -> None:
        oracle = build_oracle()
        self.assertEqual(structural_counts(oracle), STRUCTURAL)
        recovered_injection = False
        for document in oracle.documents:
            pages = extract_page_texts(document.content)
            self.assertEqual(len(pages), document.page_count)
            self.assertEqual(pdf_page_count(document.content), document.page_count)
            self.assertEqual(synth_page_count(document.content), document.page_count)
            if any(INJECTION_TEXT in page for page in pages):
                recovered_injection = True
        self.assertTrue(recovered_injection)

    def test_pipeline_is_byte_identical_across_two_runs(self) -> None:
        first = gold_packet_from_pdfs()
        second = gold_packet_from_pdfs()
        self.assertEqual(
            packet_to_canonical_bytes(first),
            packet_to_canonical_bytes(second),
        )
        self.assertEqual(
            packet_to_canonical_bytes(gold_packet()),
            packet_to_canonical_bytes(first),
        )

    def test_pdf_excerpts_have_no_commercial_keys(self) -> None:
        oracle = build_oracle()
        excerpts = peer_excerpts_from_pdfs(oracle.documents)
        self.assertGreater(len(excerpts), 0)
        for excerpt in excerpts:
            lowered = " ".join(str(key) for key in excerpt).lower()
            self.assertNotIn("price", lowered)
            self.assertNotIn("firm", lowered)
            self.assertNotIn("destination", lowered)
        status = try_lane_b_d_adapters(excerpts)
        self.assertIn(status["peers"], {"bound", "unavailable"})
        self.assertIn(status["review"], {"bound", "unavailable"})


if __name__ == "__main__":
    unittest.main()
