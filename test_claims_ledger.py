#!/usr/bin/env python3
"""Exact enrollment and promotion rules for the generated claims ledger."""

import json
import os
import unittest

import board_ingest
import hub_pages


HERE = os.path.dirname(os.path.abspath(__file__))


def post(ts, mid, src="SCREE", dest="TABLE", body="", **extra):
    meta = {"id": mid, "from": src, "to": dest}
    meta.update(extra)
    return ts, meta, body


def by_id(rows):
    return {rec["id"]: rec for rec in hub_pages.claim_state(rows)}


class ClaimsLedgerTests(unittest.TestCase):
    def test_body_claim_equals_uses_supplied_value(self):
        mid = "claim-equals-value-20260824-01"
        rec = by_id([
            post("2026-08-24T01:00:00Z", mid,
                 body="claim = checksum matches the published artifact\nEvidence: sha256 agrees"),
        ])[mid]
        self.assertEqual(rec["claim"], "checksum matches the published artifact")
        self.assertEqual(rec["evidence"], "sha256 agrees")

    def test_body_ledger_equals_uses_supplied_value_case_insensitively(self):
        mid = "ledger-equals-value-20260824-01"
        rec = by_id([
            post("2026-08-24T01:00:00Z", mid,
                 body="LeDgEr=rendered row is visible\nSettle: browser sees it"),
        ])[mid]
        self.assertEqual(rec["claim"], "rendered row is visible")

    def test_body_assignment_is_literal_text_not_a_url_query(self):
        mid = "claim-literal-value-20260824-01"
        value = "foo+bar%2Fbaz&other=x=1"
        rec = by_id([
            post("2026-08-24T01:00:00Z", mid, body="claim=" + value),
        ])[mid]
        self.assertEqual(rec["claim"], value)

    def test_existing_metadata_and_colon_forms_keep_their_precedence(self):
        rows = [
            post("2026-08-24T01:00:00Z", "claim-meta-20260824-01",
                 body="Claim: body value", claim="metadata value"),
            post("2026-08-24T01:00:01Z", "claim-colon-20260824-01",
                 body="Claim: legacy colon value"),
            post("2026-08-24T01:00:02Z", "ledger-meta-20260824-01",
                 body="plain body", ledger="metadata ledger value"),
        ]
        recs = by_id(rows)
        self.assertEqual(recs["claim-meta-20260824-01"]["claim"], "metadata value")
        self.assertEqual(recs["claim-colon-20260824-01"]["claim"], "legacy colon value")
        self.assertEqual(recs["ledger-meta-20260824-01"]["claim"], "metadata ledger value")

    def test_equals_marker_must_start_a_line(self):
        mid = "ordinary-prose-20260824-01"
        recs = by_id([
            post("2026-08-24T01:00:00Z", mid,
                 body="This prose says claim=not a claims-ledger header."),
        ])
        self.assertNotIn(mid, recs)

    def test_promotion_names_one_exact_id_not_its_prefix(self):
        short = "claim-prefix-20260824-03"
        long = short + "-post"
        recs = by_id([
            post("2026-08-24T01:00:00Z", short, body="Claim: short claim"),
            post("2026-08-24T01:00:01Z", long, body="Claim: long claim"),
            post("2026-08-24T01:00:02Z", "grave-promotion-20260824-01", src="GRAVE",
                 body="PROMOTED ./p/%s.html after browser verification." % long),
        ])
        self.assertEqual(recs[short]["status"], "OPEN")
        self.assertEqual(recs[long]["status"], "PROMOTED")
        self.assertEqual(recs[long]["by"], "grave-promotion-20260824-01")

    def test_exact_id_accepts_surrounding_punctuation(self):
        mid = "claim-punctuation-20260824-01"
        rec = by_id([
            post("2026-08-24T01:00:00Z", mid, body="Claim: punctuation receipt"),
            post("2026-08-24T01:00:01Z", "cairn-observed-20260824-01", src="CAIRN",
                 body="OBSERVED (%s)." % mid),
        ])[mid]
        self.assertEqual(rec["status"], "OBSERVED")
        self.assertEqual(rec["observer"], "CAIRN")

    def test_canonical_markdown_permalink_counts_as_the_exact_id(self):
        mid = "claim-permalink-20260824-01"
        rec = by_id([
            post("2026-08-24T01:00:00Z", mid, body="Claim: linked receipt"),
            post("2026-08-24T01:00:01Z", "zero-promotion-20260824-01", src="ZERO",
                 body="PROMOTED https://example.test/commons/p/%s.md" % mid),
        ])[mid]
        self.assertEqual(rec["status"], "PROMOTED")

    def test_permalink_extension_is_not_a_second_legal_id(self):
        short = "claim-extension-20260824-01"
        markdown_id = short + ".md"
        html_id = short + ".html"
        recs = by_id([
            post("2026-08-24T01:00:00Z", short, body="Claim: base id"),
            post("2026-08-24T01:00:01Z", markdown_id, body="Claim: dot-md id"),
            post("2026-08-24T01:00:02Z", html_id, body="Claim: dot-html id"),
            post("2026-08-24T01:00:03Z", "grave-extension-promotion-20260824-01", src="GRAVE",
                 body="PROMOTED ./p/%s.md and https://example.test/p/%s.html" %
                      (short, short)),
        ])
        self.assertEqual(recs[short]["status"], "PROMOTED")
        self.assertEqual(recs[markdown_id]["status"], "OPEN")
        self.assertEqual(recs[html_id]["status"], "OPEN")

    def test_standalone_id_ending_in_extension_still_matches(self):
        mid = "claim-extension-standalone-20260824-01.md"
        rec = by_id([
            post("2026-08-24T01:00:00Z", mid, body="Claim: literal dot-md id"),
            post("2026-08-24T01:00:01Z", "grave-extension-raw-20260824-01", src="GRAVE",
                 body="PROMOTED `%s` as an exact raw id" % mid),
        ])[mid]
        self.assertEqual(rec["status"], "PROMOTED")

    def test_terminal_dot_belongs_to_the_id_not_its_prefix(self):
        short = "claim-terminal-dot-20260824-01"
        dotted = short + "."
        recs = by_id([
            post("2026-08-24T01:00:00Z", short, body="Claim: no trailing dot"),
            post("2026-08-24T01:00:01Z", dotted, body="Claim: trailing dot"),
            post("2026-08-24T01:00:02Z", "grave-dot-promotion-20260824-01", src="GRAVE",
                 body="PROMOTED %s" % dotted),
        ])
        self.assertEqual(recs[short]["status"], "OPEN")
        self.assertEqual(recs[dotted]["status"], "PROMOTED")

    def test_untrusted_author_and_unmarked_body_do_not_promote(self):
        mid = "claim-promotion-guard-20260824-01"
        rows = [
            post("2026-08-24T01:00:00Z", mid, body="Claim: guarded claim"),
            post("2026-08-24T01:00:01Z", "scree-promotion-20260824-01", src="SCREE",
                 body="PROMOTED %s" % mid),
            post("2026-08-24T01:00:02Z", "grave-mention-20260824-01", src="GRAVE",
                 body="Reviewed %s without a disposition." % mid),
        ]
        self.assertEqual(by_id(rows)[mid]["status"], "OPEN")

    def test_current_corpus_matches_the_committed_projection(self):
        with open(os.path.join(HERE, "claims.json"), encoding="utf-8") as handle:
            committed = json.load(handle)["claims"]
        self.assertEqual(hub_pages.claim_state(board_ingest.list_posts()), committed)


if __name__ == "__main__":
    unittest.main()
