from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("provider_preflight_v1.py")
spec = importlib.util.spec_from_file_location("provider_preflight_v1", MODULE_PATH)
guard = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = guard
spec.loader.exec_module(guard)


def h(ch: str) -> str:
    return ch * 64


def base_snapshot() -> dict:
    return {
        "schema_version": "outbound-provider-preflight-snapshot/v1",
        "as_of_utc": "2026-09-16T14:30:00Z",
        "ledger_complete": True,
        "request": {
            "schema_version": "outbound-provider-preflight-request/v1",
            "publication_key": h("a"),
            "candidate_sha256": h("b"),
            "intent_sha256": h("c"),
            "buyer_scope_sha256": h("d"),
            "recipient_fingerprint": h("e"),
            "route_kind": "EMAIL",
            "operation_id": "OP-ACME-20260916",
            "prepared_at": "2026-09-16T14:20:00Z",
        },
        "send_receipts": [],
        "dnr_receipts": [],
        "source_observations": [h("f"), h("1")],
    }


def send_receipt(**updates) -> dict:
    row = {
        "provider": "GMAIL",
        "provider_message_id": "gmail:msg-001",
        "sent_at": "2026-09-16T14:25:00Z",
        "publication_key": h("a"),
        "candidate_sha256": h("b"),
        "intent_sha256": h("c"),
        "buyer_scope_sha256": h("d"),
        "recipient_fingerprint": h("e"),
        "route_kind": "EMAIL",
        "operation_id": "OP-ACME-20260916",
    }
    row.update(updates)
    return row


def dnr_receipt(**updates) -> dict:
    row = {
        "provider_ref": "slack:dnr:001",
        "observed_at": "2026-09-16T14:22:00Z",
        "buyer_scope_sha256": h("d"),
        "recipient_fingerprint": h("e"),
        "route_kind": "EMAIL",
        "reason_code": "HARD_NEGATIVE",
    }
    row.update(updates)
    return row


class ProviderPreflightTests(unittest.TestCase):
    def test_clear_for_muse_preflight(self):
        report = guard.compile_report(base_snapshot())
        self.assertEqual(report["payload"]["result"], "CLEAR_FOR_MUSE_PREFLIGHT")
        self.assertFalse(report["payload"]["authorities"]["externalSendAuthorized"])
        self.assertTrue(report["payload"]["requiresCanonicalMuseElectionV2"])
        self.assertTrue(guard.verify_report(base_snapshot(), report)["valid"])

    def test_exact_intent_send_holds(self):
        s = base_snapshot(); s["send_receipts"] = [send_receipt()]
        r = guard.compile_report(s)["payload"]
        self.assertEqual(r["result"], "HOLD_EXACT_INTENT_ALREADY_SENT")
        self.assertEqual(r["evidence"]["providerMessageId"], "gmail:msg-001")

    def test_same_publication_different_candidate_holds(self):
        s = base_snapshot(); s["send_receipts"] = [send_receipt(candidate_sha256=h("9"), intent_sha256=h("8"), operation_id="OP-OTHER")]
        self.assertEqual(guard.compile_report(s)["payload"]["result"], "HOLD_PUBLICATION_ALREADY_SENT")

    def test_unrelated_publication_does_not_hold(self):
        s = base_snapshot(); s["send_receipts"] = [send_receipt(publication_key=h("9"), candidate_sha256=h("9"), intent_sha256=h("8"), buyer_scope_sha256=h("7"), recipient_fingerprint=h("6"), operation_id="OP-OTHER")]
        self.assertEqual(guard.compile_report(s)["payload"]["result"], "CLEAR_FOR_MUSE_PREFLIGHT")

    def test_matching_dnr_holds(self):
        s = base_snapshot(); s["dnr_receipts"] = [dnr_receipt()]
        r = guard.compile_report(s)["payload"]
        self.assertEqual(r["result"], "HOLD_AFTER_DNR")
        self.assertEqual(r["evidence"]["providerRef"], "slack:dnr:001")

    def test_dnr_stronger_than_exact_send(self):
        s = base_snapshot(); s["dnr_receipts"] = [dnr_receipt()]; s["send_receipts"] = [send_receipt()]
        self.assertEqual(guard.compile_report(s)["payload"]["result"], "HOLD_AFTER_DNR")

    def test_dnr_other_recipient_does_not_hold(self):
        s = base_snapshot(); s["dnr_receipts"] = [dnr_receipt(recipient_fingerprint=h("9"))]
        self.assertEqual(guard.compile_report(s)["payload"]["result"], "CLEAR_FOR_MUSE_PREFLIGHT")

    def test_dnr_other_buyer_does_not_hold(self):
        s = base_snapshot(); s["dnr_receipts"] = [dnr_receipt(buyer_scope_sha256=h("9"))]
        self.assertEqual(guard.compile_report(s)["payload"]["result"], "CLEAR_FOR_MUSE_PREFLIGHT")

    def test_dnr_other_route_does_not_hold(self):
        s = base_snapshot(); s["dnr_receipts"] = [dnr_receipt(route_kind="DIRECT_MESSAGE")]
        self.assertEqual(guard.compile_report(s)["payload"]["result"], "CLEAR_FOR_MUSE_PREFLIGHT")

    def test_incomplete_ledger_holds(self):
        s = base_snapshot(); s["ledger_complete"] = False
        self.assertEqual(guard.compile_report(s)["payload"]["result"], "HOLD_LEDGER_INCOMPLETE")

    def test_prepared_after_as_of_holds(self):
        s = base_snapshot(); s["request"]["prepared_at"] = "2026-09-16T14:31:00Z"
        self.assertEqual(guard.compile_report(s)["payload"]["result"], "HOLD_EVIDENCE_ORDERING")

    def test_future_send_holds(self):
        s = base_snapshot(); s["send_receipts"] = [send_receipt(sent_at="2026-09-16T14:31:00Z")]
        self.assertEqual(guard.compile_report(s)["payload"]["result"], "HOLD_EVIDENCE_ORDERING")

    def test_future_dnr_holds(self):
        s = base_snapshot(); s["dnr_receipts"] = [dnr_receipt(observed_at="2026-09-16T14:31:00Z")]
        self.assertEqual(guard.compile_report(s)["payload"]["result"], "HOLD_EVIDENCE_ORDERING")

    def test_candidate_publication_rebound_holds_source_conflict(self):
        s = base_snapshot(); s["send_receipts"] = [send_receipt(publication_key=h("9"))]
        self.assertEqual(guard.compile_report(s)["payload"]["result"], "HOLD_SOURCE_CONFLICT")

    def test_candidate_intent_rebound_holds_source_conflict(self):
        s = base_snapshot(); s["send_receipts"] = [send_receipt(intent_sha256=h("9"))]
        self.assertEqual(guard.compile_report(s)["payload"]["result"], "HOLD_SOURCE_CONFLICT")

    def test_candidate_operation_rebound_holds_source_conflict(self):
        s = base_snapshot(); s["send_receipts"] = [send_receipt(operation_id="OP-OTHER")]
        self.assertEqual(guard.compile_report(s)["payload"]["result"], "HOLD_SOURCE_CONFLICT")

    def test_candidate_route_rebound_holds_source_conflict(self):
        s = base_snapshot(); s["send_receipts"] = [send_receipt(route_kind="DIRECT_MESSAGE")]
        self.assertEqual(guard.compile_report(s)["payload"]["result"], "HOLD_SOURCE_CONFLICT")

    def test_duplicate_provider_message_id_rejected(self):
        s = base_snapshot(); s["send_receipts"] = [send_receipt(), send_receipt()]
        with self.assertRaises(guard.PreflightError) as ctx: guard.compile_report(s)
        self.assertEqual(ctx.exception.code, "DUPLICATE_PROVIDER_MESSAGE_ID")

    def test_same_message_id_different_provider_allowed(self):
        s = base_snapshot(); s["send_receipts"] = [send_receipt(), send_receipt(provider="SLACK")]
        self.assertEqual(guard.compile_report(s)["payload"]["result"], "HOLD_EXACT_INTENT_ALREADY_SENT")

    def test_duplicate_dnr_ref_rejected(self):
        s = base_snapshot(); s["dnr_receipts"] = [dnr_receipt(), dnr_receipt()]
        with self.assertRaises(guard.PreflightError) as ctx: guard.compile_report(s)
        self.assertEqual(ctx.exception.code, "DUPLICATE_DNR_PROVIDER_REF")

    def test_duplicate_source_observation_rejected(self):
        s = base_snapshot(); s["source_observations"].append(s["source_observations"][0])
        with self.assertRaises(guard.PreflightError): guard.compile_report(s)

    def test_empty_source_observation_rejected(self):
        s = base_snapshot(); s["source_observations"] = []
        with self.assertRaises(guard.PreflightError): guard.compile_report(s)

    def test_unknown_root_field_rejected(self):
        s = base_snapshot(); s["extra"] = 1
        with self.assertRaises(guard.PreflightError): guard.compile_report(s)

    def test_unknown_send_field_rejected(self):
        s = base_snapshot(); row = send_receipt(); row["extra"] = "x"; s["send_receipts"] = [row]
        with self.assertRaises(guard.PreflightError): guard.compile_report(s)

    def test_unsupported_route_rejected(self):
        s = base_snapshot(); s["request"]["route_kind"] = "FAX"
        with self.assertRaises(guard.PreflightError) as ctx: guard.compile_report(s)
        self.assertEqual(ctx.exception.code, "ROUTE_KIND_INVALID")

    def test_unsupported_provider_rejected(self):
        s = base_snapshot(); s["send_receipts"] = [send_receipt(provider="SMTP")]
        with self.assertRaises(guard.PreflightError) as ctx: guard.compile_report(s)
        self.assertEqual(ctx.exception.code, "PROVIDER_INVALID")

    def test_bool_ledger_required(self):
        s = base_snapshot(); s["ledger_complete"] = 1
        with self.assertRaises(guard.PreflightError) as ctx: guard.compile_report(s)
        self.assertEqual(ctx.exception.code, "LEDGER_COMPLETE_BOOL_REQUIRED")

    def test_invalid_hash_rejected(self):
        s = base_snapshot(); s["request"]["publication_key"] = "abc"
        with self.assertRaises(guard.PreflightError): guard.compile_report(s)

    def test_invalid_utc_rejected(self):
        s = base_snapshot(); s["as_of_utc"] = "2026-99-99T00:00:00Z"
        with self.assertRaises(guard.PreflightError): guard.compile_report(s)

    def test_duplicate_json_key_rejected(self):
        with self.assertRaises(guard.PreflightError) as ctx: guard.strict_json_loads('{"x":1,"x":2}')
        self.assertEqual(ctx.exception.code, "DUPLICATE_JSON_KEY")

    def test_float_rejected(self):
        with self.assertRaises(guard.PreflightError) as ctx: guard.strict_json_loads('{"x":1.5}')
        self.assertEqual(ctx.exception.code, "FLOAT_NOT_ALLOWED")

    def test_nonfinite_rejected(self):
        with self.assertRaises(guard.PreflightError) as ctx: guard.strict_json_loads('{"x":NaN}')
        self.assertEqual(ctx.exception.code, "NONFINITE_NUMBER")

    def test_report_tamper_rejected(self):
        s = base_snapshot(); report = guard.compile_report(s); report["payload"]["result"] = "HOLD_AFTER_DNR"
        self.assertFalse(guard.verify_report(s, report)["valid"])

    def test_resealed_report_tamper_rejected(self):
        s = base_snapshot(); report = guard.compile_report(s); report["payload"]["result"] = "HOLD_AFTER_DNR"; report["receiptSha256"] = guard.sha256_text(guard.canonical_json(report["payload"]))
        self.assertFalse(guard.verify_report(s, report)["valid"])

    def test_source_mutation_breaks_verification(self):
        s = base_snapshot(); report = guard.compile_report(s); s["source_observations"][0] = h("9")
        self.assertFalse(guard.verify_report(s, report)["valid"])

    def test_input_order_deterministic(self):
        s = base_snapshot(); s["send_receipts"] = [send_receipt(provider_message_id="gmail:z", sent_at="2026-09-16T14:26:00Z"), send_receipt(provider_message_id="gmail:a", candidate_sha256=h("9"), intent_sha256=h("8"), operation_id="OP-OTHER", sent_at="2026-09-16T14:21:00Z")]
        # Avoid candidate rebound by making both different candidates.
        s["send_receipts"][0]["candidate_sha256"] = h("7"); s["send_receipts"][0]["intent_sha256"] = h("6"); s["send_receipts"][0]["operation_id"] = "OP-OTHER-2"
        r1 = guard.compile_report(s); s["send_receipts"].reverse(); r2 = guard.compile_report(s)
        self.assertEqual(r1, r2)

    def test_public_authority_mutation_cannot_authorize(self):
        original = deepcopy(guard.AUTHORITY_FALSE)
        try:
            for k in guard.AUTHORITY_FALSE: guard.AUTHORITY_FALSE[k] = True
            report = guard.compile_report(base_snapshot())
            self.assertTrue(all(v is False for v in report["payload"]["authorities"].values()))
        finally:
            guard.AUTHORITY_FALSE.clear(); guard.AUTHORITY_FALSE.update(original)

    def test_public_authority_rebind_cannot_authorize(self):
        original = guard.AUTHORITY_FALSE
        try:
            guard.AUTHORITY_FALSE = {"externalSendAuthorized": True}
            report = guard.compile_report(base_snapshot())
            self.assertTrue(all(v is False for v in report["payload"]["authorities"].values()))
        finally: guard.AUTHORITY_FALSE = original

    def test_clear_is_not_send_authority(self):
        p = guard.compile_report(base_snapshot())["payload"]
        self.assertEqual(p["result"], "CLEAR_FOR_MUSE_PREFLIGHT")
        self.assertTrue(p["requiresFreshProviderPreflight"])
        self.assertTrue(p["requiresCanonicalMuseElectionV2"])
        self.assertFalse(p["authorities"]["externalSendAuthorized"])
        self.assertFalse(p["authorities"]["providerMutationAuthorized"])

    def test_cli_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td); src = td / "snapshot.json"; out = td / "report.json"
            src.write_text(json.dumps(base_snapshot()), encoding="utf-8")
            p = subprocess.run([sys.executable, str(MODULE_PATH), "compile", str(src), str(out)], capture_output=True, text=True, check=False)
            self.assertEqual(p.returncode, 0, p.stderr); self.assertEqual(p.stdout.strip(), "CLEAR_FOR_MUSE_PREFLIGHT")
            v = subprocess.run([sys.executable, str(MODULE_PATH), "verify", str(src), str(out)], capture_output=True, text=True, check=False)
            self.assertEqual(v.returncode, 0, v.stderr); self.assertEqual(v.stdout.strip(), "VERIFIED")

    def test_cli_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td); src = td / "snapshot.json"; out = td / "report.json"
            src.write_text(json.dumps(base_snapshot()), encoding="utf-8"); out.write_text("occupied", encoding="utf-8")
            p = subprocess.run([sys.executable, str(MODULE_PATH), "compile", str(src), str(out)], capture_output=True, text=True, check=False)
            self.assertEqual(p.returncode, 2); self.assertIn("OUTPUT_EXISTS", p.stderr)

    @unittest.skipUnless(hasattr(os, "symlink"), "symlink unavailable")
    def test_cli_refuses_input_symlink(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td); real = td / "real.json"; link = td / "link.json"; out = td / "report.json"
            real.write_text(json.dumps(base_snapshot()), encoding="utf-8"); os.symlink(real, link)
            p = subprocess.run([sys.executable, str(MODULE_PATH), "compile", str(link), str(out)], capture_output=True, text=True, check=False)
            self.assertEqual(p.returncode, 2); self.assertIn("INPUT_OPEN_FAILED", p.stderr)


if __name__ == "__main__":
    unittest.main()
