#!/usr/bin/env python3
"""Git-durability tests for three Bid 1421 leftover lanes still 404 on main."""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parent
PACK = ROOT / "revenue" / "billings_bid_1421"
FIXTURES = PACK / "instrument_fixtures"
CORPUS = PACK / "acceptance_corpus"
OPS = PACK / "operations_package"
MATRIX = PACK / "compliance_matrix"

SLACK_CORPUS_JSON = "355924d3e03dae5f2fb6759a927338a56d57ce1a9606897d65621256b340d313"
SLACK_CORPUS_MD = "62bb217e8b5c661b564da7974eacce21c7dc7be791abeeff737caf26469c1db4"
SLACK_OPS = "49d6d56a5726d598966e8185ec84f3401faf405a9f8a0ccb9804248ad13885bc"
SLACK_MATRIX_MD = "16073bccde73417805b7a6996802b1e245e6d4a18f26b948fadefb4b742c3ce6"
INSTRUMENT_RECEIPT_BLOB = "03ff210c2385e5cbf9785e706d97c41b44689976"


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_matrix_rows(text: str):
    rows = []
    for line in text.splitlines():
        if re.match(r"^\| (A\d+|S3-|E\d+|AA\d+|AB\d+|AC\d+|AD\d+|AF-)", line):
            parts = [x.strip() for x in line.strip().strip("|").split("|")]
            rows.append({"id": parts[0], "status": parts[3]})
    return rows


class BillingsBid1421LeftoverLanesTests(unittest.TestCase):
    def test_three_receipts_exist(self):
        for name in (
            "billings-bid-1421-acceptance-corpus-20260831-01.md",
            "billings-bid-1421-operations-package-20260831-01.md",
            "billings-bid-1421-rfp-compliance-matrix-20260831-01.md",
        ):
            path = ROOT / "p" / name
            self.assertTrue(path.is_file(), name)
            body = path.read_text(encoding="utf-8")
            self.assertIn("cash_usd: 0", body)
            self.assertIn("No City contact", body)
            self.assertIn("No submission", body)

    def test_acceptance_corpus_100_unique_at_cases_and_slack_hash(self):
        json_path = CORPUS / "billings-bid-1421-aquatrace-acceptance-corpus.json"
        md_path = CORPUS / "billings-bid-1421-aquatrace-acceptance-corpus.md"
        self.assertEqual(sha256(json_path), SLACK_CORPUS_JSON)
        self.assertEqual(sha256(md_path), SLACK_CORPUS_MD)
        obj = json.loads(json_path.read_text(encoding="utf-8"))
        ids = [case["id"] for case in obj["cases"]]
        self.assertEqual(len(ids), 100)
        self.assertEqual(len(set(ids)), 100)
        self.assertEqual(ids, [f"AT-{i:03d}" for i in range(1, 101)])
        self.assertEqual(sum(obj["category_distribution"].values()), 100)
        self.assertEqual(obj["id"], "billings-bid-1421-acceptance-corpus-20260831-01")
        self.assertEqual(obj["state"], "SYNTHETIC_TEST_SPEC_ONLY")
        self.assertFalse(obj["truth_boundary"]["city_submission"])
        self.assertFalse(obj["truth_boundary"]["instrument_compatibility_claimed"])
        for case in obj["cases"]:
            self.assertFalse(case["system_may_release_regulatory_result"])
            self.assertFalse(case["system_may_contact_external_endpoint"])
        md = md_path.read_text(encoding="utf-8")
        self.assertEqual(len(re.findall(r"^### AT-\d{3} ", md, flags=re.M)), 100)

    def test_operations_package_slack_hash_and_labels(self):
        path = OPS / "billings-bid-1421-operations-package.md"
        raw = path.read_bytes()
        self.assertEqual(len(raw), 17916)
        self.assertEqual(raw.count(b"\n"), 165)
        self.assertEqual(sha256(path), SLACK_OPS)
        text = path.read_text(encoding="utf-8")
        self.assertIn("PLANNED_AFTER_AWARD", text)
        self.assertIn("BUYER_INPUT_REQUIRED", text)
        self.assertIn("CANNOT_CLAIM", text)
        self.assertIn("NOT SUBMITTED", text)
        self.assertNotRegex(text, r"full instrument compatibility")
        self.assertNotRegex(text, r"guaranteed SLA")

    def test_compliance_matrix_121_rows_and_status_counts(self):
        md_path = MATRIX / "billings-bid-1421-rfp-compliance-matrix.md"
        json_path = MATRIX / "billings-bid-1421-rfp-compliance-matrix.json"
        self.assertEqual(sha256(md_path), SLACK_MATRIX_MD)
        rows = parse_matrix_rows(md_path.read_text(encoding="utf-8"))
        self.assertEqual(len(rows), 121)
        self.assertEqual(len({row["id"] for row in rows}), 121)
        counts = {status: 0 for status in ("EVIDENCE_NOW", "PROTOTYPE_EVIDENCE", "PLANNED_AFTER_AWARD", "CANNOT_CLAIM")}
        for row in rows:
            counts[row["status"]] += 1
        self.assertEqual(counts["EVIDENCE_NOW"], 1)
        self.assertEqual(counts["PROTOTYPE_EVIDENCE"], 9)
        self.assertEqual(counts["PLANNED_AFTER_AWARD"], 2)
        self.assertEqual(counts["CANNOT_CLAIM"], 109)
        obj = json.loads(json_path.read_text(encoding="utf-8"))
        self.assertEqual(obj["row_count"], 121)
        self.assertEqual(obj["status_counts"], counts)
        self.assertEqual(obj["decision"], "HOLD / NO SUBMISSION")
        self.assertFalse(obj["city_submission"])
        self.assertEqual(obj["cash_usd"], 0)
        self.assertEqual(obj["source"]["only_positive_evidence"]["attachment_e_sent_receipt"], "1a055c181593fa52")
        evidence = [row for row in obj["rows"] if row["status"] == "EVIDENCE_NOW"]
        self.assertEqual(len(evidence), 1)
        self.assertEqual(evidence[0]["id"], "A05")
        self.assertIn("1a055c181593fa52", evidence[0]["artifact_needed"])

    def test_instrument_fixtures_untouched(self):
        self.assertTrue((FIXTURES / "manifest.json").is_file())
        receipt = ROOT / "p" / "billings-bid-1421-instrument-fixtures-20260831-01.md"
        self.assertTrue(receipt.is_file())
        import subprocess

        blob = subprocess.check_output(
            ["git", "hash-object", str(receipt)],
            cwd=ROOT,
            text=True,
        ).strip()
        self.assertEqual(blob, INSTRUMENT_RECEIPT_BLOB)
        text = receipt.read_text(encoding="utf-8")
        self.assertIn("id: billings-bid-1421-instrument-fixtures-20260831-01", text)
        self.assertIn("cash_usd: 0", text)
        self.assertNotIn("AT-001", text)


if __name__ == "__main__":
    unittest.main()
