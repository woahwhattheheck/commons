#!/usr/bin/env python3
"""Tests for the UIOWA-105 contract conformance checker.

The point of the checker is that a component author OTHER than the adapter's
author can tell whether their file will join correctly. So these tests assert
the things such an author depends on: that a real defect fails with the record
and path named, that a harmless difference does not fail, and that a verdict of
CONFORMANT actually means the adapter accepts the file.
"""

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr

import adapters
import check_contract as cc
import integrate
from ledgers import (ONE_TIME_EFFORT, RECURRING_EFFORT, ONE_TIME_CASH,
                     RELEASED_CAPACITY, AdapterError)

HERE = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.join(HERE, "fixtures")
GOOD_RESOURCE = os.path.join(FIX, "resource_estimates.contract.json")
GOOD_ECONOMICS = os.path.join(FIX, "economics.contract.json")
BAD_RESOURCE = os.path.join(FIX, "resource_estimates.nonconformant.json")
BAD_ECONOMICS = os.path.join(FIX, "economics.nonconformant.json")

PORT = integrate.find_component("uiowa_rfq_18649_ai_opportunity_portfolio")
PORTFOLIO = os.path.join(PORT, "sample_output", "portfolio.json") if PORT else None
HAVE_PORTFOLIO = bool(PORTFOLIO and os.path.exists(PORTFOLIO))
WHY = ("needs the sibling opportunity-portfolio lane; set UIOWA_REPO_ROOT to "
       "the revenue/ directory when running from a staging copy")


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def run(doc, kind):
    findings, summary = cc.check(doc, kind)
    return findings, summary


def levels(findings, level):
    return [f for f in findings if f.level == level]


def paths(findings, level):
    return sorted(f.path for f in findings if f.level == level)


class ConformantTests(unittest.TestCase):

    def test_resource_contract_fixture_is_conformant(self):
        findings, summary = run(load(GOOD_RESOURCE), "resource")
        self.assertEqual(levels(findings, "FAIL"), [])
        self.assertEqual(summary["records"], 8)

    def test_economics_contract_fixture_is_conformant(self):
        findings, _ = run(load(GOOD_ECONOMICS), "economics")
        self.assertEqual(levels(findings, "FAIL"), [])

    @unittest.skipUnless(HAVE_PORTFOLIO, WHY)
    def test_the_real_landed_portfolio_output_is_conformant(self):
        """The one adapter whose upstream is genuinely on the branch. If this
        ever fails, 072's published output and 105's adapter have diverged."""
        findings, summary = run(load(PORTFOLIO), "portfolio")
        self.assertEqual(levels(findings, "FAIL"), [])
        self.assertEqual(summary["records"], 6)
        # Five candidates carry a benefit figure; OPP-IAM-02 does not.
        self.assertEqual(summary["ledgers_populated"][RELEASED_CAPACITY], 5)
        self.assertEqual(summary["ledgers_unknown"][RELEASED_CAPACITY], 1)

    def test_a_conformant_verdict_means_the_adapter_accepts_the_file(self):
        """The checker's promise. If it says CONFORMANT and the adapter then
        refuses, the checker is worse than useless -- it would send a seat away
        believing their file works."""
        for path, kind, fn in (
                (GOOD_RESOURCE, "resource", adapters.adapt_resource_estimates),
                (GOOD_ECONOMICS, "economics", adapters.adapt_economics)):
            doc = load(path)
            findings, _ = run(doc, kind)
            self.assertEqual(levels(findings, "FAIL"), [], path)
            fn(doc)          # must not raise

    def test_checker_self_reports_if_it_disagrees_with_the_adapter(self):
        """The guard that catches a checker bug: a doc that passes every rule
        but that the adapter still refuses must produce a FAIL naming the
        disagreement rather than a silent pass."""
        doc = load(GOOD_ECONOMICS)
        original = adapters.adapt_economics
        try:
            def refuse(_):
                raise AdapterError("synthetic refusal for the self-check")
            adapters.adapt_economics = refuse
            findings, _ = run(doc, "economics")
        finally:
            adapters.adapt_economics = original
        fails = levels(findings, "FAIL")
        self.assertEqual(len(fails), 1)
        self.assertIn("checker bug", fails[0].message)


class DefectDetectionTests(unittest.TestCase):

    def setUp(self):
        self.findings, self.summary = run(load(BAD_RESOURCE), "resource")

    def test_five_distinct_defects_are_caught(self):
        self.assertEqual(len(levels(self.findings, "FAIL")), 5)

    def test_each_failure_names_the_record_and_the_path(self):
        for f in levels(self.findings, "FAIL"):
            self.assertTrue(f.path.startswith("$.work_items["), f.path)
            self.assertTrue(f.message)

    def test_estimate_written_in_words_fails(self):
        msgs = " ".join(f.message for f in levels(self.findings, "FAIL"))
        self.assertIn("written in words", msgs)

    def test_partial_range_fails_with_the_bounds_it_did_find(self):
        msg = [f.message for f in levels(self.findings, "FAIL")
               if "partial range" in f.message][0]
        self.assertIn("high, low", msg)
        self.assertIn("not filled in with a default", msg)

    def test_boolean_fails_rather_than_being_read_as_one(self):
        msgs = " ".join(f.message for f in levels(self.findings, "FAIL"))
        self.assertIn("boolean", msgs)

    def test_inverted_bounds_fail(self):
        msgs = " ".join(f.message for f in levels(self.findings, "FAIL"))
        self.assertIn("low <= likely <= high", msgs)

    def test_duplicate_identifier_fails(self):
        self.assertIn("WI-BAD-WORDS-001", self.summary["duplicate_identifiers"])

    def test_a_failed_field_is_not_counted_as_populated(self):
        """Three of six records have a usable one-time effort figure. A checker
        that counted the broken ones would overstate what joins."""
        self.assertEqual(self.summary["ledgers_populated"][ONE_TIME_EFFORT], 3)

    def test_missing_currency_fails_exactly_once(self):
        findings, _ = run(load(BAD_ECONOMICS), "economics")
        currency_fails = [f for f in levels(findings, "FAIL")
                          if f.path == "$.currency"]
        self.assertEqual(len(currency_fails), 1)
        self.assertIn("declared unit", currency_fails[0].message)


class ToleranceTests(unittest.TestCase):
    """What must NOT fail. A checker that is hostile to harmless difference
    makes other seats route around it."""

    def setUp(self):
        self.findings, self.summary = run(load(BAD_RESOURCE), "resource")

    def test_unknown_fields_are_carried_not_refused(self):
        infos = paths(self.findings, "INFO")
        self.assertIn("$.work_items[].vendor_quote_reference", infos)
        self.assertIn("$.work_items[].confidence", infos)
        for f in levels(self.findings, "INFO"):
            self.assertNotIn("error", f.message.lower().replace("not an error", ""))
        self.assertIn("vendor_quote_reference", self.summary["carried_extensions"])

    def test_a_field_from_another_contract_says_which_one(self):
        msg = [f.message for f in levels(self.findings, "INFO")
               if f.path.endswith("one_time_cash")][0]
        self.assertIn("economics contract", msg)
        self.assertIn("double count", msg)

    def test_a_point_estimate_warns_but_does_not_fail(self):
        warn_paths = paths(self.findings, "WARN")
        self.assertTrue(any("work_items[5]" in p for p in warn_paths))
        self.assertFalse(any("work_items[5].one_time_effort_hours" == f.path
                             for f in levels(self.findings, "FAIL")))

    def test_an_unlinked_record_warns_and_is_listed_not_dropped(self):
        findings, summary = run(load(GOOD_RESOURCE), "resource")
        self.assertIn("WI-UNSCOPED-DISCOVERY-001", summary["unmapped_records"])
        self.assertEqual(levels(findings, "FAIL"), [])

    def test_an_absent_optional_range_is_unknown_not_a_failure(self):
        doc = load(GOOD_RESOURCE)
        del doc["work_items"][0]["recurring_effort_fte_per_year"]
        findings, summary = run(doc, "resource")
        self.assertEqual(levels(findings, "FAIL"), [])
        self.assertGreaterEqual(summary["ledgers_unknown"][RECURRING_EFFORT], 1)

    def test_an_empty_collection_warns_rather_than_failing(self):
        doc = load(GOOD_RESOURCE)
        doc["work_items"] = []
        findings, _ = run(doc, "resource")
        self.assertEqual(levels(findings, "FAIL"), [])
        self.assertTrue(levels(findings, "WARN"))


class HostileInputTests(unittest.TestCase):

    def test_wrong_schema_version_fails_and_says_so_plainly(self):
        doc = load(GOOD_RESOURCE)
        doc["schema_version"] = "uiowa-086-resource-estimate/7"
        findings, _ = run(doc, "resource")
        msg = [f.message for f in levels(findings, "FAIL")
               if f.path == "$.schema_version"][0]
        self.assertIn("should not be guessed", msg)

    def test_top_level_not_an_object_fails_without_crashing(self):
        findings, _ = run(["not", "a", "document"], "resource")
        self.assertTrue(levels(findings, "FAIL"))

    def test_collection_not_a_list_fails_without_crashing(self):
        doc = load(GOOD_RESOURCE)
        doc["work_items"] = {"WI-1": {}}
        findings, _ = run(doc, "resource")
        self.assertTrue(any("must be a list" in f.message
                            for f in levels(findings, "FAIL")))

    def test_a_record_that_is_not_an_object_fails_without_crashing(self):
        doc = load(GOOD_RESOURCE)
        doc["work_items"].append("oops")
        findings, _ = run(doc, "resource")
        self.assertTrue(any("expected an object" in f.message
                            for f in levels(findings, "FAIL")))

    def test_absent_collection_fails_without_crashing(self):
        findings, _ = run({"schema_version": adapters.RESOURCE_SCHEMA}, "resource")
        self.assertTrue(levels(findings, "FAIL"))

    def test_record_with_no_identifier_fails(self):
        doc = load(GOOD_RESOURCE)
        del doc["work_items"][0]["work_item_id"]
        findings, _ = run(doc, "resource")
        self.assertTrue(any("identifier is absent" in f.message
                            for f in levels(findings, "FAIL")))


class CliTests(unittest.TestCase):

    def _run(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = cc.main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_conformant_file_exits_zero(self):
        code, out, _ = self._run(["--resource", GOOD_RESOURCE])
        self.assertEqual(code, 0)
        self.assertIn("CONFORMANT", out)

    def test_non_conformant_file_exits_one(self):
        code, out, _ = self._run(["--resource", BAD_RESOURCE])
        self.assertEqual(code, 1)
        self.assertIn("NON-CONFORMANT", out)

    def test_missing_file_exits_two(self):
        with tempfile.TemporaryDirectory() as d:
            code, _, err = self._run(["--resource", os.path.join(d, "nope.json")])
        self.assertEqual(code, 2)
        self.assertIn("UNUSABLE", err)

    def test_malformed_json_exits_two(self):
        with tempfile.TemporaryDirectory() as d:
            bad = os.path.join(d, "bad.json")
            with open(bad, "w", encoding="utf-8") as fh:
                fh.write("{oops")
            code, _, err = self._run(["--resource", bad])
        self.assertEqual(code, 2)
        self.assertIn("UNUSABLE", err)

    def test_json_output_is_machine_readable(self):
        code, out, _ = self._run(["--resource", GOOD_RESOURCE, "--json"])
        payload = json.loads(out)
        self.assertEqual(code, 0)
        self.assertTrue(payload["conformant"])
        self.assertIn("summary", payload)

    def test_explain_prints_the_contract_for_every_kind(self):
        for kind in sorted(cc.CONTRACTS):
            code, out, _ = self._run(["--explain", kind])
            self.assertEqual(code, 0)
            self.assertIn(cc.CONTRACTS[kind]["schema_version"], out)
            for ledger in cc.CONTRACTS[kind]["fills"]:
                self.assertIn(ledger, out)

    def test_explain_states_every_accepted_range_form(self):
        _, out, _ = self._run(["--explain", "resource"])
        for form in ("low", "mid", "value", "basis", "UNKNOWN"):
            self.assertIn(form, out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
