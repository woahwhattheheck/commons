import copy
import json
import tempfile
import unittest
from pathlib import Path

from engine import EvidenceError, canonical_bytes, cli, compile_packet, decisions_csv, digest, loads_strict, summary_markdown, verify_result

HERE = Path(__file__).resolve().parent
FIXTURE = json.loads((HERE / "fixture.json").read_text())
AS_OF = "2026-09-13T10:45:00Z"


class EngineTests(unittest.TestCase):
    def test_control_fixture_exact_counts(self):
        result = compile_packet(FIXTURE, as_of=AS_OF)
        self.assertEqual(result["manifest"]["counts"], {"total": 12, "ready": 7, "hold": 5})
        holds = {r["invoice_id"]: r["reasons"] for r in result["queue"]}
        self.assertEqual(set(holds), {"INV-003", "INV-005", "INV-007", "INV-009", "INV-011"})
        self.assertIn("PO_MISSING", holds["INV-003"])
        self.assertIn("VENDOR_INACTIVE", holds["INV-005"])
        self.assertIn("INVOICE_EXCEEDS_PO", holds["INV-007"])
        self.assertIn("INVOICE_PREDATES_PO", holds["INV-009"])
        self.assertIn("DUE_DATE_PRECEDES_INVOICE", holds["INV-011"])

    def test_replay_byte_identical(self):
        a = compile_packet(FIXTURE, as_of=AS_OF)
        b = compile_packet(copy.deepcopy(FIXTURE), as_of=AS_OF)
        self.assertEqual(canonical_bytes(a), canonical_bytes(b))
        self.assertEqual(decisions_csv(a), decisions_csv(b))
        self.assertEqual(summary_markdown(a), summary_markdown(b))

    def test_verify_round_trip(self):
        result = compile_packet(FIXTURE, as_of=AS_OF)
        self.assertTrue(verify_result(FIXTURE, result, as_of=AS_OF))

    def test_tampered_decision_fails_verify(self):
        result = compile_packet(FIXTURE, as_of=AS_OF)
        result["decisions"][0]["state"] = "HOLD"
        with self.assertRaises(EvidenceError):
            verify_result(FIXTURE, result, as_of=AS_OF)

    def test_duplicate_json_key_rejected(self):
        with self.assertRaisesRegex(EvidenceError, "duplicate JSON key"):
            loads_strict('{"schema_version":"x","schema_version":"y"}')

    def test_nonfinite_json_rejected(self):
        with self.assertRaises(EvidenceError):
            loads_strict('{"x": NaN}')

    def test_unknown_root_field_rejected(self):
        p = copy.deepcopy(FIXTURE); p["surprise"] = True
        with self.assertRaisesRegex(EvidenceError, "unknown fields"):
            compile_packet(p, as_of=AS_OF)

    def test_duplicate_invoice_id_rejected(self):
        p = copy.deepcopy(FIXTURE); p["invoices"].append(copy.deepcopy(p["invoices"][0]))
        with self.assertRaisesRegex(EvidenceError, "duplicate invoice_id"):
            compile_packet(p, as_of=AS_OF)

    def test_semantic_duplicate_holds_both(self):
        p = copy.deepcopy(FIXTURE)
        extra = copy.deepcopy(p["invoices"][0]); extra["invoice_id"] = "INV-099"; extra["snapshot_sha256"] = "f" * 64
        p["invoices"].append(extra)
        r = compile_packet(p, as_of=AS_OF)
        states = {x["invoice_id"]: x for x in r["decisions"]}
        self.assertIn("DUPLICATE_INVOICE_EVIDENCE", states["INV-001"]["reasons"])
        self.assertIn("DUPLICATE_INVOICE_EVIDENCE", states["INV-099"]["reasons"])

    def test_vendor_missing_holds(self):
        p = copy.deepcopy(FIXTURE); p["invoices"][0]["vendor_id"] = "V-NOPE"
        r = compile_packet(p, as_of=AS_OF)
        row = next(x for x in r["decisions"] if x["invoice_id"] == "INV-001")
        self.assertIn("VENDOR_MISSING", row["reasons"])

    def test_po_vendor_mismatch_holds(self):
        p = copy.deepcopy(FIXTURE); p["purchase_orders"][0]["vendor_id"] = "V-002"
        r = compile_packet(p, as_of=AS_OF)
        row = next(x for x in r["decisions"] if x["invoice_id"] == "INV-001")
        self.assertIn("PO_VENDOR_MISMATCH", row["reasons"])

    def test_po_currency_mismatch_rejected_at_boundary(self):
        p = copy.deepcopy(FIXTURE); p["purchase_orders"][0]["currency"] = "EUR"
        with self.assertRaisesRegex(EvidenceError, "unsupported currency"):
            compile_packet(p, as_of=AS_OF)

    def test_amount_requires_string(self):
        p = copy.deepcopy(FIXTURE); p["invoices"][0]["amount"] = 1000.00
        with self.assertRaisesRegex(EvidenceError, "expected string"):
            compile_packet(p, as_of=AS_OF)

    def test_amount_requires_two_decimals(self):
        p = copy.deepcopy(FIXTURE); p["invoices"][0]["amount"] = "1000"
        with self.assertRaisesRegex(EvidenceError, "two decimal"):
            compile_packet(p, as_of=AS_OF)

    def test_negative_amount_rejected(self):
        p = copy.deepcopy(FIXTURE); p["invoices"][0]["amount"] = "-1.00"
        with self.assertRaisesRegex(EvidenceError, "nonnegative"):
            compile_packet(p, as_of=AS_OF)

    def test_bad_digest_rejected(self):
        p = copy.deepcopy(FIXTURE); p["invoices"][0]["snapshot_sha256"] = "A" * 64
        with self.assertRaisesRegex(EvidenceError, "lowercase sha256"):
            compile_packet(p, as_of=AS_OF)

    def test_future_capture_rejected(self):
        p = copy.deepcopy(FIXTURE); p["captured_at"] = "2026-09-13T10:46:00Z"
        with self.assertRaisesRegex(EvidenceError, "future evidence"):
            compile_packet(p, as_of=AS_OF)

    def test_stale_capture_rejected(self):
        p = copy.deepcopy(FIXTURE); p["captured_at"] = "2026-01-01T00:00:00Z"
        with self.assertRaisesRegex(EvidenceError, "stale evidence"):
            compile_packet(p, as_of=AS_OF)

    def test_noncanonical_instant_rejected(self):
        p = copy.deepcopy(FIXTURE); p["captured_at"] = "2026-09-13T10:40:00.000Z"
        with self.assertRaisesRegex(EvidenceError, "canonical seconds"):
            compile_packet(p, as_of=AS_OF)

    def test_due_before_invoice_holds_not_rejects_packet(self):
        result = compile_packet(FIXTURE, as_of=AS_OF)
        row = next(x for x in result["decisions"] if x["invoice_id"] == "INV-011")
        self.assertEqual(row["state"], "HOLD")
        self.assertEqual(row["reasons"], ["DUE_DATE_PRECEDES_INVOICE"])

    def test_authority_ceiling_all_false_except_read_only(self):
        a = compile_packet(FIXTURE, as_of=AS_OF)["manifest"]["authority"]
        self.assertTrue(a.pop("read_only"))
        self.assertTrue(all(v is False for v in a.values()))

    def test_manifest_digest_self_verifies(self):
        r = compile_packet(FIXTURE, as_of=AS_OF)
        m = r["manifest"]
        core = {k: v for k, v in m.items() if k != "manifest_sha256"}
        self.assertEqual(m["manifest_sha256"], digest(core))

    def test_csv_is_stable_and_has_13_lines(self):
        text = decisions_csv(compile_packet(FIXTURE, as_of=AS_OF))
        self.assertEqual(len(text.splitlines()), 13)
        self.assertTrue(text.startswith("invoice_id,state,reasons"))

    def test_markdown_contains_authority_warning(self):
        md = summary_markdown(compile_packet(FIXTURE, as_of=AS_OF))
        self.assertIn("cannot approve an invoice", md)
        self.assertIn("READY: **7**", md)
        self.assertIn("HOLD: **5**", md)

    def test_cli_compile_and_verify(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            src = td / "packet.json"
            src.write_text(json.dumps(FIXTURE), encoding="utf-8")
            out = td / "out"
            self.assertEqual(cli(["compile", str(src), "--as-of", AS_OF, "--out-dir", str(out)]), 0)
            self.assertTrue((out / "result.json").exists())
            self.assertTrue((out / "decisions.csv").exists())
            self.assertTrue((out / "receipt.md").exists())
            self.assertEqual(cli(["verify", str(src), str(out / "result.json"), "--as-of", AS_OF]), 0)

    def test_cli_refuses_tampered_result(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            src = td / "packet.json"; src.write_text(json.dumps(FIXTURE), encoding="utf-8")
            result = compile_packet(FIXTURE, as_of=AS_OF); result["manifest"]["counts"]["ready"] = 99
            rp = td / "result.json"; rp.write_text(json.dumps(result), encoding="utf-8")
            self.assertEqual(cli(["verify", str(src), str(rp), "--as-of", AS_OF]), 2)


if __name__ == "__main__":
    unittest.main()
