#!/usr/bin/env python3
"""Binary tests for the Bid 1421 AquaTrace acceptance runner.

Proves the real control rail executes AT-001..AT-100 from the existing
corpus. The corpus files stay Slack-byte-identical. The product is not a
stand-in; synthetic fixtures exist because there is no live laboratory.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import pathlib
import subprocess
import unittest

ROOT = pathlib.Path(__file__).resolve().parent
PACK = ROOT / "revenue" / "billings_bid_1421" / "acceptance_runner"
CORPUS = ROOT / "revenue" / "billings_bid_1421" / "acceptance_corpus"
CORPUS_JSON = CORPUS / "billings-bid-1421-aquatrace-acceptance-corpus.json"
CORPUS_MD = CORPUS / "billings-bid-1421-aquatrace-acceptance-corpus.md"
SLACK_CORPUS_JSON = "355924d3e03dae5f2fb6759a927338a56d57ce1a9606897d65621256b340d313"
SLACK_CORPUS_MD = "62bb217e8b5c661b564da7974eacce21c7dc7be791abeeff737caf26469c1db4"
CORPUS_POST_BLOB = "054e321cef6226dc59ab2d6781f56637b3cb433d"
INSTRUMENT_RECEIPT_BLOB = "03ff210c2385e5cbf9785e706d97c41b44689976"
REQUIRED = (
    "case_id",
    "event_id",
    "sample_id",
    "actor_fixture",
    "role_fixture",
    "method_version",
    "rule_version",
    "input_hash",
    "observed_effect_hash",
    "disposition",
    "reason_code",
    "event_time",
)
REASON_CODES = {
    "AT-002": "REQUIRED_FIELD_MISSING",
    "AT-003": "METHOD_MAPPING_REQUIRED",
    "AT-008": "ACTOR_REQUIRED",
    "AT-022": "ACTOR_REQUIRED",
    "AT-040": "SAMPLE_NOT_FOUND",
    "AT-056": "MISSING_SAMPLE_ID",
    "AT-057": "INSTRUMENT_MAPPING_REQUIRED",
}
PRODUCT_PATHS = (
    PACK / "runner.py",
    PACK / "README.md",
    PACK / "source.json",
    ROOT / "billings-bid-1421-acceptance-runner.html",
    ROOT / "p" / "billings-bid-1421-acceptance-runner-20260831-01.md",
)


def _sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_runner():
    path = PACK / "runner.py"
    spec = importlib.util.spec_from_file_location("billings_bid_1421_acceptance_runner", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BillingsBid1421AcceptanceRunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runner = _load_runner()
        cls.corpus = cls.runner.load_corpus()
        cls.summary = cls.runner.run_corpus()

    def test_pack_files_exist(self):
        for name in ("runner.py", "README.md", "source.json"):
            self.assertTrue((PACK / name).is_file(), name)

    def test_corpus_cited_not_rewritten(self):
        self.assertEqual(_sha256(CORPUS_JSON), SLACK_CORPUS_JSON)
        self.assertEqual(_sha256(CORPUS_MD), SLACK_CORPUS_MD)
        blob = subprocess.check_output(
            ["git", "hash-object", str(ROOT / "p" / "billings-bid-1421-acceptance-corpus-20260831-01.md")],
            cwd=ROOT,
            text=True,
        ).strip()
        self.assertEqual(blob, CORPUS_POST_BLOB)
        self.assertTrue(self.summary["corpus_byte_identity"])
        self.assertEqual(self.summary["corpus_sha256"], SLACK_CORPUS_JSON)

    def test_instrument_fixtures_receipt_untouched(self):
        receipt = ROOT / "p" / "billings-bid-1421-instrument-fixtures-20260831-01.md"
        blob = subprocess.check_output(
            ["git", "hash-object", str(receipt)],
            cwd=ROOT,
            text=True,
        ).strip()
        self.assertEqual(blob, INSTRUMENT_RECEIPT_BLOB)

    def test_one_hundred_of_one_hundred_expected_dispositions(self):
        self.assertEqual(self.summary["case_count"], 100)
        self.assertEqual(self.summary["pass_count"], 100)
        self.assertEqual(self.summary["fail_count"], 0)
        self.assertTrue(self.summary["ok"], self.summary.get("failures"))
        expected = {case["id"]: case["expected_disposition"] for case in self.corpus["cases"]}
        self.assertEqual(self.summary["dispositions"], expected)
        self.assertEqual(len(self.summary["receipts"]), 100)

    def test_required_receipt_fields_and_one_receipt_per_case(self):
        seen = []
        for rec in self.summary["receipts"]:
            for field in REQUIRED:
                self.assertIn(field, rec, rec.get("case_id"))
                self.assertIsNotNone(rec[field], field)
            seen.append(rec["case_id"])
        self.assertEqual(seen, ["AT-%03d" % i for i in range(1, 101)])

    def test_named_reason_codes(self):
        for case_id, reason in REASON_CODES.items():
            self.assertEqual(self.summary["reason_codes"][case_id], reason, case_id)

    def test_release_and_transmission_remain_zero(self):
        self.assertEqual(self.summary["regulatory_release_count"], 0)
        self.assertEqual(self.summary["regulatory_transmission_count"], 0)
        self.assertEqual(self.summary["autonomous_release_count"], 0)
        for rec in self.summary["receipts"]:
            self.assertEqual(rec["regulatory_release_count"], 0, rec["case_id"])
            self.assertEqual(rec["autonomous_release_count"], 0, rec["case_id"])

    def test_named_human_required_before_regulatory_release(self):
        self.assertEqual(self.summary["dispositions"]["AT-049"], "DENIED")
        self.assertEqual(self.summary["dispositions"]["AT-050"], "HUMAN_RELEASE_APPROVAL_RECORDED")
        self.assertEqual(self.summary["dispositions"]["AT-080"], "DENIED")
        self.assertEqual(self.summary["reason_codes"]["AT-049"], "RELEASE_REQUIRES_NAMED_HUMAN")
        self.assertEqual(self.summary["reason_codes"]["AT-080"], "SEND_PROHIBITED")

    def test_engine_does_not_read_expected_disposition(self):
        case = dict(self.corpus["cases"][0])
        case["expected_disposition"] = "WRONG"
        rail = self.runner.ControlRail()
        receipt = self.runner.execute_case(case, rail=rail, corpus=self.corpus)
        self.assertEqual(case["id"], "AT-001")
        self.assertEqual(receipt["disposition"], "ACCEPTED")
        self.assertNotEqual(receipt["disposition"], "WRONG")

    def test_replay_is_byte_identical(self):
        same, digest = self.runner.replay_identical()
        self.assertTrue(same)
        self.assertEqual(digest, self.summary["audit_sha256"])
        self.assertEqual(len(digest), 64)

    def test_retries_do_not_duplicate(self):
        self.assertEqual(self.summary["dispositions"]["AT-004"], "DUPLICATE_SUPPRESSED")
        self.assertEqual(self.summary["dispositions"]["AT-012"], "DUPLICATE_SUPPRESSED")
        self.assertEqual(self.summary["dispositions"]["AT-091"], "DUPLICATE_SUPPRESSED")
        self.assertEqual(self.summary["dispositions"]["AT-016"], "RECONCILED_COMMITTED")
        self.assertEqual(self.summary["dispositions"]["AT-093"], "RECONCILED_COMMITTED")

    def test_new_product_files_do_not_use_banned_product_word(self):
        for path in PRODUCT_PATHS:
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8").lower()
            banned = "".join(("m", "ock"))
            self.assertNotIn(banned, text, path.name)

    def test_cli_binary_pass(self):
        proc = subprocess.run(
            ["python3", str(PACK / "runner.py")],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr or proc.stdout)
        self.assertIn("pass=100", proc.stdout)
        self.assertIn("audit_sha256=", proc.stdout)
        self.assertIn("PASS", proc.stdout)
        self.assertNotIn("FAIL", proc.stdout.splitlines()[-1])

    def test_source_and_door_are_login_free(self):
        source = json.loads((PACK / "source.json").read_text(encoding="utf-8"))
        self.assertEqual(source["leftover_id"], "billings-bid-1421-acceptance-runner-20260831-01")
        self.assertEqual(source["cash_usd"], 0)
        self.assertFalse(source["city_contact"])
        self.assertEqual(source["truth_gate"], "HOLD / BUILD-AND-VERIFY")
        door = ROOT / "billings-bid-1421-acceptance-runner.html"
        if door.is_file():
            html = door.read_text(encoding="utf-8").lower()
            self.assertNotIn("login", html)
            self.assertNotIn("price", html)
            self.assertNotIn("buy now", html)
            self.assertNotIn("mailto:", html)
            self.assertNotIn("<form", html)


if __name__ == "__main__":
    unittest.main()
