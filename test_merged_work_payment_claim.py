from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from revenue.merged_work_payment_claim import core

NOW = "2026-09-17T20:00:00Z"


def ready_doc():
    return {
        "schema": core.SCHEMA,
        "claim_id": "claim-001",
        "work": {
            "repository": "example/project",
            "pr_number": 42,
            "merged_commit_sha": "1" * 40,
            "deliverable_sha256": "2" * 64,
            "merged_at": "2026-09-16T18:00:00Z",
            "source_ref": "github:example/project/pull/42",
            "source_sha256": "3" * 64,
        },
        "compensation": {
            "offer_id": "bounty-42",
            "source_ref": "program:bounty-42",
            "source_sha256": "4" * 64,
            "advertised_at": "2026-09-10T12:00:00Z",
            "expires_at": None,
            "currency": "USD",
            "amount_minor": 9000,
        },
        "acceptance": {
            "acceptance_id": "merge-42",
            "source_class": "TARGET_MERGE_EVENT",
            "source_ref": "github:example/project/pull/42#merged",
            "source_sha256": "5" * 64,
            "accepted_at": "2026-09-16T18:00:00Z",
            "repository": "example/project",
            "pr_number": 42,
            "merged_commit_sha": "1" * 40,
        },
        "eligibility": {
            "status": "ELIGIBLE",
            "source_ref": "program:rules",
            "source_sha256": "6" * 64,
            "observed_at": "2026-09-17T19:00:00Z",
        },
        "followups": [],
        "payment_status": {
            "status": "UNPAID",
            "source_ref": "program:status",
            "source_sha256": "7" * 64,
            "observed_at": "2026-09-17T19:30:00Z",
            "paid_amount_minor": None,
            "payment_ref": None,
        },
        "policy": {"max_status_age_hours": 168, "cooldown_hours": 72},
    }


class ClaimTests(unittest.TestCase):
    def compile(self, doc=None, now=NOW):
        return core.compile_artifacts(ready_doc() if doc is None else doc, now)

    def state(self, doc=None, now=NOW):
        return self.compile(doc, now)[0]["state"]

    def test_ready(self):
        report, markdown, receipt = self.compile()
        self.assertEqual(report["state"], "READY_FOR_MUSE_PAYMENT_REQUEST")
        self.assertEqual(report["payment_request"]["advertised_amount_minor"], 9000)
        self.assertIsNone(report["payment_request"]["recipient"])
        self.assertIsNone(report["payment_request"]["route"])
        self.assertIn("Direct payment-request draft", markdown)
        self.assertTrue(all(value is False for value in report["authority"].values()))
        self.assertTrue(core.verify_artifacts(ready_doc(), NOW, report, markdown, receipt))

    def test_no_compensation(self):
        doc = ready_doc(); doc["compensation"] = None
        report, markdown, _ = self.compile(doc)
        self.assertEqual(report["state"], "HOLD_NO_COMPENSATION")
        self.assertIsNone(report["payment_request"])
        self.assertIn("advertised_compensation_missing", markdown)

    def test_no_acceptance(self):
        doc = ready_doc(); doc["acceptance"] = None
        self.assertEqual(self.state(doc), "HOLD_NO_ACCEPTANCE")

    def test_ineligible(self):
        doc = ready_doc(); doc["eligibility"]["status"] = "INELIGIBLE"
        self.assertEqual(self.state(doc), "HOLD_INELIGIBLE")

    def test_already_paid(self):
        doc = ready_doc()
        doc["payment_status"].update(status="PAID", paid_amount_minor=9000, payment_ref="provider:payment-1")
        self.assertEqual(self.state(doc), "HOLD_ALREADY_PAID")

    def test_unknown_eligibility_holds(self):
        doc = ready_doc(); doc["eligibility"]["status"] = "UNKNOWN"
        report, _, _ = self.compile(doc)
        self.assertEqual(report["state"], "HOLD_EVIDENCE")
        self.assertIn("eligibility_not_proven", report["blockers"])

    def test_unknown_payment_holds(self):
        doc = ready_doc(); doc["payment_status"]["status"] = "UNKNOWN"
        report, _, _ = self.compile(doc)
        self.assertEqual(report["state"], "HOLD_EVIDENCE")
        self.assertIn("unpaid_status_not_proven", report["blockers"])

    def test_stale_status(self):
        doc = ready_doc(); doc["policy"]["max_status_age_hours"] = 1
        doc["eligibility"]["observed_at"] = "2026-09-17T18:59:59Z"
        self.assertEqual(self.state(doc), "HOLD_STALE")

    def test_status_age_exact_boundary_is_fresh(self):
        doc = ready_doc(); doc["policy"]["max_status_age_hours"] = 1
        doc["eligibility"]["observed_at"] = "2026-09-17T19:00:00Z"
        doc["payment_status"]["observed_at"] = "2026-09-17T19:00:00Z"
        self.assertEqual(self.state(doc), "READY_FOR_MUSE_PAYMENT_REQUEST")

    def test_expiry_exact_boundary_is_valid(self):
        doc = ready_doc(); doc["compensation"]["expires_at"] = NOW
        self.assertEqual(self.state(doc), "READY_FOR_MUSE_PAYMENT_REQUEST")

    def test_expiry_first_second_after_holds(self):
        doc = ready_doc(); doc["compensation"]["expires_at"] = "2026-09-17T19:59:59Z"
        self.assertEqual(self.state(doc), "HOLD_STALE")

    def test_cooldown(self):
        doc = ready_doc()
        doc["followups"] = [{
            "id": "f1", "kind": "PAYMENT_REQUEST_SENT", "source_ref": "gmail:msg1",
            "source_sha256": "8" * 64, "observed_at": "2026-09-17T19:00:00Z"
        }]
        self.assertEqual(self.state(doc), "HOLD_COOLDOWN")

    def test_cooldown_exact_boundary_is_ready(self):
        doc = ready_doc(); doc["policy"]["cooldown_hours"] = 1
        doc["followups"] = [{
            "id": "f1", "kind": "PAYMENT_REQUEST_SENT", "source_ref": "gmail:msg1",
            "source_sha256": "8" * 64, "observed_at": "2026-09-17T19:00:00Z"
        }]
        self.assertEqual(self.state(doc), "READY_FOR_MUSE_PAYMENT_REQUEST")

    def test_rejection_requires_review(self):
        doc = ready_doc()
        doc["followups"] = [{
            "id": "f1", "kind": "PAYMENT_REJECTED", "source_ref": "sponsor:reply",
            "source_sha256": "8" * 64, "observed_at": "2026-09-17T19:00:00Z"
        }]
        self.assertEqual(self.state(doc), "HOLD_EVIDENCE")

    def test_acceptance_cross_repo_rejected(self):
        doc = ready_doc(); doc["acceptance"]["repository"] = "other/project"
        with self.assertRaises(core.ClaimError):
            self.compile(doc)

    def test_acceptance_cross_commit_rejected(self):
        doc = ready_doc(); doc["acceptance"]["merged_commit_sha"] = "a" * 40
        with self.assertRaises(core.ClaimError):
            self.compile(doc)

    def test_future_evidence_rejected(self):
        doc = ready_doc(); doc["payment_status"]["observed_at"] = "2026-09-17T20:00:01Z"
        with self.assertRaises(core.ClaimError):
            self.compile(doc)

    def test_bool_not_int_pr(self):
        doc = ready_doc(); doc["work"]["pr_number"] = True
        with self.assertRaises(core.ClaimError):
            self.compile(doc)

    def test_bool_not_int_amount(self):
        doc = ready_doc(); doc["compensation"]["amount_minor"] = False
        with self.assertRaises(core.ClaimError):
            self.compile(doc)

    def test_nonpaid_cannot_carry_payment_reference(self):
        doc = ready_doc(); doc["payment_status"]["payment_ref"] = "provider:payment"
        with self.assertRaises(core.ClaimError):
            self.compile(doc)

    def test_duplicate_followup_id_rejected(self):
        row = {
            "id": "same", "kind": "SPONSOR_REPLIED", "source_ref": "r1",
            "source_sha256": "8" * 64, "observed_at": "2026-09-17T18:00:00Z"
        }
        doc = ready_doc(); doc["followups"] = [copy.deepcopy(row), copy.deepcopy(row)]
        with self.assertRaises(core.ClaimError):
            self.compile(doc)

    def test_reminted_duplicate_followup_rejected(self):
        row = {
            "id": "a", "kind": "SPONSOR_REPLIED", "source_ref": "r1",
            "source_sha256": "8" * 64, "observed_at": "2026-09-17T18:00:00Z"
        }
        other = copy.deepcopy(row); other["id"] = "b"
        doc = ready_doc(); doc["followups"] = [row, other]
        with self.assertRaises(core.ClaimError):
            self.compile(doc)

    def test_duplicate_json_key_rejected(self):
        with self.assertRaises(core.ClaimError):
            core.strict_loads('{"a":1,"a":1}')

    def test_float_and_nonfinite_rejected(self):
        for text in ('{"a":1.5}', '{"a":NaN}', '{"a":Infinity}'):
            with self.subTest(text=text), self.assertRaises(core.ClaimError):
                core.strict_loads(text)

    def test_unsafe_integer_rejected_at_json_boundary(self):
        with self.assertRaises(core.ClaimError):
            core.strict_loads('{"a":9007199254740992}')

    def test_lone_surrogate_rejected(self):
        with self.assertRaises(core.ClaimError):
            core.strict_loads('"\\ud800"')

    def test_unknown_field_rejected(self):
        doc = ready_doc(); doc["surprise"] = "x"
        with self.assertRaises(core.ClaimError):
            self.compile(doc)

    def test_order_invariance(self):
        doc = ready_doc()
        reversed_doc = dict(reversed(list(doc.items())))
        a = self.compile(doc)
        b = self.compile(reversed_doc)
        self.assertEqual(core._canonical(a[0]), core._canonical(b[0]))
        self.assertEqual(a[1], b[1])
        self.assertEqual(core._canonical(a[2]), core._canonical(b[2]))

    def test_bool_int_artifact_alias_fails_verifier(self):
        report, markdown, receipt = self.compile()
        mutated = copy.deepcopy(report)
        mutated["authority"]["send_authorized"] = 0
        self.assertEqual(mutated, report)  # Python equality aliases False and 0.
        self.assertFalse(core.verify_artifacts(ready_doc(), NOW, mutated, markdown, receipt))

    def test_receipt_tamper_fails(self):
        report, markdown, receipt = self.compile()
        mutated = copy.deepcopy(receipt); mutated["input_sha256"] = "f" * 64
        self.assertFalse(core.verify_artifacts(ready_doc(), NOW, report, markdown, mutated))

    def test_markdown_tamper_fails(self):
        report, markdown, receipt = self.compile()
        self.assertFalse(core.verify_artifacts(ready_doc(), NOW, report, markdown + "x", receipt))

    def test_input_transplant_fails(self):
        report, markdown, receipt = self.compile()
        other = ready_doc(); other["claim_id"] = "other"
        self.assertFalse(core.verify_artifacts(other, NOW, report, markdown, receipt))

    def test_publish_create_exclusive(self):
        report, markdown, receipt = self.compile()
        with tempfile.TemporaryDirectory() as td:
            directory = Path(td)
            paths = core.publish(directory, report, markdown, receipt)
            self.assertTrue(all(path.is_file() for path in paths))
            with self.assertRaises(core.ClaimError):
                core.publish(directory, report, markdown, receipt)

    @unittest.skipUnless(hasattr(os, "symlink"), "symlink unavailable")
    def test_symlink_input_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            real = root / "real.json"; real.write_text(json.dumps(ready_doc()), encoding="utf-8")
            link = root / "link.json"; os.symlink(real, link)
            with self.assertRaises(core.ClaimError):
                core.load_json_file(link)

    def test_cli_compile_verify(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            packet = root / "input.json"
            packet.write_text(json.dumps(ready_doc(), separators=(",", ":")), encoding="utf-8")
            out = root / "out"; out.mkdir()
            env = dict(os.environ)
            repo_root = Path(__file__).resolve().parent
            cmd = [sys.executable, "-m", "revenue.merged_work_payment_claim.core", "compile", str(packet), str(out), "--evaluation-at", NOW]
            first = subprocess.run(cmd, cwd=repo_root, env=env, text=True, capture_output=True)
            self.assertEqual(first.returncode, 0, first.stderr + first.stdout)
            verify = subprocess.run(
                [sys.executable, "-m", "revenue.merged_work_payment_claim.core", "verify", str(packet), str(out / "payment-claim.report.json"), str(out / "payment-claim.md"), str(out / "payment-claim.receipt.json"), "--evaluation-at", NOW],
                cwd=repo_root, env=env, text=True, capture_output=True,
            )
            self.assertEqual(verify.returncode, 0, verify.stderr + verify.stdout)
            self.assertIn("VERIFIED", verify.stdout)


if __name__ == "__main__":
    unittest.main()
