from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from .cli import main as cli_main
from .engine import (
    FilingQualityError,
    POLICY_MAX_BYTES,
    SOURCE_MAX_BYTES,
    canonical_bytes,
    compile_report,
    loads_strict,
    render_html,
    verify_bundle,
    verify_report,
    write_bundle,
)


def fact(value, *, filed, accn, end="2026-06-30", start=None, unit_meta=True, frame=None):
    row = {
        "end": end,
        "val": value,
        "accn": accn,
        "form": "10-K",
        "filed": filed,
    }
    if start is not None:
        row["start"] = start
    if unit_meta:
        row["fy"] = 1901
        row["fp"] = "FY"
    if frame is not None:
        row["frame"] = frame
    return row


def sample_source(entity_name="Example & Holdings <QA>"):
    return {
        "cik": 123456,
        "entityName": entity_name,
        "facts": {
            "us-gaap": {
                "Assets": {
                    "units": {"USD": [fact(1000, filed="2026-08-01", accn="a-assets")]}
                },
                "Liabilities": {
                    "units": {"USD": [fact(400, filed="2026-08-01", accn="a-liab")]}
                },
                "StockholdersEquity": {
                    "units": {"USD": [fact(600, filed="2026-08-01", accn="a-equity")]}
                },
                "AssetsAlt": {
                    "units": {
                        "USD": [fact(900, filed="2026-08-01", accn="a-alt", end="2025-12-31")]
                    }
                },
                "EntityCommonStockSharesOutstanding": {
                    "units": {"shares": [fact(10, filed="2026-08-01", accn="a-shares")]}
                },
                "Revenue": {
                    "units": {
                        "USD": [
                            fact(100, filed="2025-08-01", accn="r-prior", start="2024-07-01", end="2025-06-30", frame="CY1901"),
                            fact(120, filed="2026-08-01", accn="r-v1", start="2025-07-01", frame="CY9999"),
                            fact(125, filed="2026-08-15", accn="r-v2", start="2025-07-01", frame="CY1901"),
                            fact(125, filed="2026-08-15", accn="r-v2b", start="2025-07-01", frame="CY0001"),
                            fact(130, filed="2026-09-02", accn="r-after-cutoff", start="2025-07-01"),
                        ]
                    }
                },
                "AmbiguousMetric": {
                    "units": {
                        "USD": [
                            fact(7, filed="2026-08-20", accn="amb-a"),
                            fact(8, filed="2026-08-20", accn="amb-b"),
                        ]
                    }
                },
            }
        },
    }


def sample_policy():
    return {
        "schema": "TJL_FILING_QUALITY_POLICY_V1",
        "cik": "0000123456",
        "filing_cutoff": "2026-08-31",
        "selections": [
            {"id": "assets", "taxonomy": "us-gaap", "concept": "Assets", "unit": "USD", "period": {"kind": "instant", "end": "2026-06-30"}},
            {"id": "liabilities", "taxonomy": "us-gaap", "concept": "Liabilities", "unit": "USD", "period": {"kind": "instant", "end": "2026-06-30"}},
            {"id": "equity", "taxonomy": "us-gaap", "concept": "StockholdersEquity", "unit": "USD", "period": {"kind": "instant", "end": "2026-06-30"}},
            {"id": "assets_alt", "taxonomy": "us-gaap", "concept": "AssetsAlt", "unit": "USD", "period": {"kind": "instant", "end": "2025-12-31"}},
            {"id": "shares", "taxonomy": "us-gaap", "concept": "EntityCommonStockSharesOutstanding", "unit": "shares", "period": {"kind": "instant", "end": "2026-06-30"}},
            {"id": "revenue_prior", "taxonomy": "us-gaap", "concept": "Revenue", "unit": "USD", "period": {"kind": "duration", "start": "2024-07-01", "end": "2025-06-30"}},
            {"id": "revenue_current", "taxonomy": "us-gaap", "concept": "Revenue", "unit": "USD", "period": {"kind": "duration", "start": "2025-07-01", "end": "2026-06-30"}},
            {"id": "ambiguous", "taxonomy": "us-gaap", "concept": "AmbiguousMetric", "unit": "USD", "period": {"kind": "instant", "end": "2026-06-30"}},
            {"id": "missing", "taxonomy": "us-gaap", "concept": "NotThere", "unit": "USD", "period": {"kind": "instant", "end": "2026-06-30"}},
        ],
        "comparisons": [
            {"id": "revenue_change", "left": "revenue_prior", "right": "revenue_current"},
            {"id": "unit_mismatch", "left": "assets", "right": "shares"},
        ],
        "checks": [
            {
                "id": "balance_equation",
                "terms": [
                    {"selection": "liabilities", "coefficient": "1"},
                    {"selection": "equity", "coefficient": "1"},
                ],
                "target": "assets",
                "tolerance": "0",
            },
            {
                "id": "period_hold",
                "terms": [{"selection": "assets", "coefficient": "1"}],
                "target": "assets_alt",
                "tolerance": "0",
            },
            {
                "id": "unit_hold",
                "terms": [{"selection": "assets", "coefficient": "1"}],
                "target": "shares",
                "tolerance": "0",
            },
        ],
    }


def raw(value):
    return json.dumps(value, separators=(",", ":"), sort_keys=True)


def by_id(rows):
    return {row["id"]: row for row in rows}


class FilingQualityDeskTests(unittest.TestCase):
    def compile(self, source=None, policy=None):
        return compile_report(raw(source or sample_source()), raw(policy or sample_policy()))

    def test_exact_selection_cutoff_and_metadata_not_period_identity(self):
        report = self.compile()
        selections = by_id(report["selections"])
        current = selections["revenue_current"]
        self.assertEqual(current["status"], "SELECTED")
        self.assertEqual(current["selected_value"], "125")
        self.assertEqual(current["selected_filed"], "2026-08-15")
        self.assertEqual(current["selected_accessions"], ["r-v2", "r-v2b"])
        self.assertNotIn("r-after-cutoff", {o["accession"] for o in current["observations"]})
        self.assertIn("REPORTED_VALUE_CHANGED_ACROSS_FILINGS", current["findings"])
        self.assertIn("SAME_VALUE_MULTIPLE_ACCESSIONS_ON_LATEST_DATE", current["findings"])
        self.assertEqual({o.get("frame") for o in current["observations"]}, {"CY9999", "CY1901", "CY0001"})

    def test_same_day_differing_values_refuse_selection(self):
        row = by_id(self.compile()["selections"])["ambiguous"]
        self.assertEqual(row["status"], "AMBIGUOUS_LATEST_FILING_DATE")
        self.assertIsNone(row["selected_value"])
        self.assertIn("SAME_FILED_DATE_DIFFERING_VALUES", row["findings"])

    def test_missing_fact_is_explicit(self):
        row = by_id(self.compile()["selections"])["missing"]
        self.assertEqual(row["status"], "NO_MATCHING_FACT")

    def test_comparison_reports_delta_without_restatement_claim(self):
        comparison = by_id(self.compile()["comparisons"])["revenue_change"]
        self.assertEqual(comparison["status"], "OK")
        self.assertEqual(comparison["delta"], "25")
        self.assertIn("not labeled a restatement", comparison["note"])

    def test_comparison_unit_mismatch_holds(self):
        comparison = by_id(self.compile()["comparisons"])["unit_mismatch"]
        self.assertEqual(comparison["status"], "HOLD_INCOMPATIBLE_UNIT")

    def test_exact_decimal_arithmetic_check(self):
        check = by_id(self.compile()["checks"])["balance_equation"]
        self.assertEqual(check["status"], "PASS")
        self.assertEqual(check["computed"], "1000")
        self.assertEqual(check["difference"], "0")

    def test_arithmetic_incompatible_period_and_unit_hold(self):
        checks = by_id(self.compile()["checks"])
        self.assertEqual(checks["period_hold"]["status"], "HOLD_INCOMPATIBLE_PERIOD")
        self.assertEqual(checks["unit_hold"]["status"], "HOLD_INCOMPATIBLE_UNIT")

    def test_check_failure_uses_inclusive_tolerance(self):
        policy = sample_policy()
        check = next(x for x in policy["checks"] if x["id"] == "balance_equation")
        check["terms"][1]["coefficient"] = "0.99"
        check["tolerance"] = "5.99"
        row = by_id(self.compile(policy=policy)["checks"])["balance_equation"]
        self.assertEqual(row["difference"], "-6")
        self.assertEqual(row["status"], "FAIL")
        check["tolerance"] = "6"
        row = by_id(self.compile(policy=policy)["checks"])["balance_equation"]
        self.assertEqual(row["status"], "PASS")

    def test_duplicate_json_key_rejected(self):
        with self.assertRaises(FilingQualityError):
            loads_strict('{"x":1,"x":2}', max_bytes=100)

    def test_nonfinite_rejected(self):
        with self.assertRaises(FilingQualityError):
            loads_strict('{"x":NaN}', max_bytes=100)

    def test_bool_value_not_numeric(self):
        source = sample_source()
        source["facts"]["us-gaap"]["Assets"]["units"]["USD"][0]["val"] = True
        with self.assertRaises(FilingQualityError):
            self.compile(source=source)

    def test_excessive_numeric_magnitude_rejected(self):
        source = sample_source()
        source["facts"]["us-gaap"]["Assets"]["units"]["USD"][0]["val"] = "1e61"
        with self.assertRaises(FilingQualityError):
            self.compile(source=source)

    def test_policy_unknown_field_rejected(self):
        policy = sample_policy()
        policy["owner_says_ok"] = True
        with self.assertRaises(FilingQualityError):
            self.compile(policy=policy)

    def test_policy_selection_unknown_field_rejected(self):
        policy = sample_policy()
        policy["selections"][0]["frame"] = "CY2026Q2I"
        with self.assertRaises(FilingQualityError):
            self.compile(policy=policy)

    def test_cik_mismatch_rejected(self):
        policy = sample_policy()
        policy["cik"] = "999"
        with self.assertRaises(FilingQualityError):
            self.compile(policy=policy)

    def test_invalid_date_rejected(self):
        policy = sample_policy()
        policy["filing_cutoff"] = "2026-02-30"
        with self.assertRaises(FilingQualityError):
            self.compile(policy=policy)

    def test_instant_fact_with_start_does_not_match(self):
        source = sample_source()
        source["facts"]["us-gaap"]["Assets"]["units"]["USD"][0]["start"] = "2026-01-01"
        row = by_id(self.compile(source=source)["selections"])["assets"]
        self.assertEqual(row["status"], "NO_MATCHING_FACT")

    def test_source_and_policy_bytes_are_bound(self):
        source_obj = sample_source()
        policy_obj = sample_policy()
        compact_source = raw(source_obj)
        pretty_source = json.dumps(source_obj, indent=2, sort_keys=True)
        compact_policy = raw(policy_obj)
        a = compile_report(compact_source, compact_policy)
        b = compile_report(pretty_source, compact_policy)
        self.assertNotEqual(a["source"]["sha256"], b["source"]["sha256"])
        self.assertFalse(verify_report(a, pretty_source, compact_policy))
        self.assertTrue(verify_report(a, compact_source, compact_policy))

    def test_receipt_tamper_rejected(self):
        source = raw(sample_source())
        policy = raw(sample_policy())
        report = compile_report(source, policy)
        tampered = copy.deepcopy(report)
        by_id(tampered["selections"])["assets"]["selected_value"] = "999"
        self.assertFalse(verify_report(tampered, source, policy))

    def test_bundle_verification_and_no_overwrite(self):
        source = raw(sample_source())
        policy = raw(sample_policy())
        report = compile_report(source, policy)
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "bundle"
            write_bundle(out, report)
            self.assertTrue(verify_bundle(out, source, policy))
            with self.assertRaises(FilingQualityError):
                write_bundle(out, report)
            (out / "observations.csv").write_text("tampered\n", encoding="utf-8")
            self.assertFalse(verify_bundle(out, source, policy))

    def test_html_escapes_entity_name(self):
        page = render_html(self.compile())
        self.assertIn("Example &amp; Holdings &lt;QA&gt;", page)
        self.assertNotIn("Example & Holdings <QA>", page)

    def test_output_is_order_invariant_for_fact_list(self):
        source = sample_source()
        a = self.compile(source=source)
        source["facts"]["us-gaap"]["Revenue"]["units"]["USD"].reverse()
        b = self.compile(source=source)
        # exact source-byte digests differ because the retained bytes differ, but the selected semantics do not.
        self.assertEqual(by_id(a["selections"])["revenue_current"]["selected_value"], by_id(b["selections"])["revenue_current"]["selected_value"])
        self.assertEqual(by_id(a["comparisons"])["revenue_change"]["delta"], by_id(b["comparisons"])["revenue_change"]["delta"])

    def test_authority_ceiling_is_hard_false(self):
        report = self.compile()
        self.assertTrue(report["authority"])
        self.assertFalse(any(report["authority"].values()))

    def test_cli_compile_then_verify(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "source.json"
            policy = root / "policy.json"
            out = root / "out"
            source.write_text(raw(sample_source()), encoding="utf-8")
            policy.write_text(raw(sample_policy()), encoding="utf-8")
            self.assertEqual(cli_main(["compile", str(source), str(policy), str(out)]), 0)
            self.assertEqual(cli_main(["verify", str(source), str(policy), str(out)]), 0)

    def test_input_byte_limits(self):
        with self.assertRaises(FilingQualityError):
            loads_strict(" " * (POLICY_MAX_BYTES + 1), max_bytes=POLICY_MAX_BYTES)
        with self.assertRaises(FilingQualityError):
            loads_strict(" " * (SOURCE_MAX_BYTES + 1), max_bytes=SOURCE_MAX_BYTES)


if __name__ == "__main__":
    unittest.main()
