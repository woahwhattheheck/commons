"""Normal and optimized, dependency-free tests of the real remittance sidecar."""
from __future__ import annotations

import copy
import csv
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from revenue.accounts_receivable_leakage_desk import remittance_review as rr


def sample():
    snapshot = "DEMO-20260917"
    def invoice(key, amount, account="ACCT-A", status="OPEN"):
        return dict(snapshot_id=snapshot, invoice_id=key, account_id=account,
                    currency="USD", issue_date="2026-09-01", remaining_minor=amount,
                    status=status, source_event_id="ERP-" + key)
    def payment(key, amount, account="ACCT-A"):
        return dict(snapshot_id=snapshot, payment_id=key, account_id=account,
                    currency="USD", received_date="2026-09-15", available_minor=amount,
                    source_event_id="BANK-" + key)
    def allocation(key, payment_id, invoice_id, amount):
        return dict(snapshot_id=snapshot, allocation_id=key, payment_id=payment_id,
                    invoice_id=invoice_id, amount_minor=amount, remittance_ref="REMIT-" + payment_id)
    return {"schema": rr.SCHEMA, "snapshot_id": snapshot, "analysis_date": "2026-09-17", "currency": "USD",
            "invoices": [invoice("INV-1", 10000), invoice("INV-2", 5000), invoice("INV-3", 3000, "ACCT-B")],
            "payments": [payment("PAY-1", 12000), payment("PAY-2", 2000), payment("PAY-3", 3000, "ACCT-B")],
            "allocations": [allocation("A-1", "PAY-1", "INV-1", 10000),
                            allocation("A-2", "PAY-1", "INV-2", 2000),
                            allocation("A-3", "PAY-2", "INV-2", 1000)]}


def as_csv(packet):
    output = {}
    for kind, columns in rr.COLUMNS.items():
        stream = io.StringIO(newline="")
        writer = csv.DictWriter(stream, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(packet[kind])
        output[kind] = stream.getvalue().encode()
    return output


def findings(report):
    return {f["code"] for c in report["components"] for f in c["findings"]}


class RemittanceReviewTests(unittest.TestCase):
    def setUp(self):
        self.p = sample()

    def compile(self):
        return rr.compile_review(self.p)

    def reject(self, packet=None, code=None):
        with self.assertRaises(rr.ReviewError) as caught:
            rr.compile_review(self.p if packet is None else packet)
        if code:
            self.assertEqual(str(caught.exception), code)

    def test_split_partial_and_unapplied(self):
        r = self.compile()
        self.assertEqual(r["totals"], dict(source_payment_available_minor=17000,
                         source_invoice_remaining_minor=18000, proposed_minor=13000,
                         hypothetical_unapplied_minor=4000, hypothetical_remaining_minor=5000))
        self.assertEqual([p["hypothetical_unapplied_minor"] for p in r["payments"]], [0, 1000, 3000])
        self.assertEqual([i["hypothetical_remaining_minor"] for i in r["invoices"]], [0, 2000, 3000])
        self.assertTrue(all(a["state"] == "PROPOSED_ONLY" for a in r["allocations"]))

    def test_does_not_mutate_input(self):
        original = copy.deepcopy(self.p)
        self.compile()
        self.assertEqual(self.p, original)

    def test_all_authority_false_and_historical_label(self):
        r = self.compile()
        self.assertTrue(all(v is False for v in r["authority"].values()))
        self.assertEqual(r["mode"], "ANALYTICAL_PROPOSAL_NOT_POSTED")
        self.assertEqual(r["evidence_class"], "OWNER_SUPPLIED_SNAPSHOT_UNAUTHENTICATED")

    def test_order_invariance(self):
        before = self.compile()
        for kind in rr.COLUMNS:
            self.p[kind].reverse()
        self.assertEqual(before, self.compile())

    def test_semantic_verifier_and_bool_int_tamper(self):
        r = self.compile()
        self.assertTrue(rr.verify_review(self.p, r))
        r["authority"]["posting"] = 0
        with self.assertRaises(rr.ReviewError):
            rr.verify_review(self.p, r)

    def test_receipt_tamper_even_with_recomputed_self_hash(self):
        r = self.compile()
        r["totals"]["proposed_minor"] = 1
        r["receipt_sha256"] = rr.digest(rr.canonical({k: v for k, v in r.items() if k != "receipt_sha256"}))
        with self.assertRaises(rr.ReviewError):
            rr.verify_review(self.p, r)

    def test_snapshot_replay_rejected(self):
        r = self.compile()
        self.p["snapshot_id"] = "NEXT"
        for kind in rr.COLUMNS:
            for row in self.p[kind]:
                row["snapshot_id"] = "NEXT"
        with self.assertRaises(rr.ReviewError):
            rr.verify_review(self.p, r)

    def test_cross_file_snapshot_rejected(self):
        self.p["payments"][0]["snapshot_id"] = "OTHER"
        self.reject(code="ROW_SNAPSHOT_MISMATCH")

    def test_invoice_oversubscription_holds_entire_component(self):
        # INV-2 is over-requested. PAY-1 -> INV-1 must ALSO hold, not win by order.
        self.p["allocations"][2]["amount_minor"] = 4000
        r = self.compile()
        self.assertIn("INVOICE_OVER_ALLOCATED", findings(r))
        self.assertEqual(r["totals"]["proposed_minor"], 0)
        self.assertEqual(r["totals"]["hypothetical_unapplied_minor"], 17000)
        self.assertEqual(r["allocations"][0]["state"], "REVIEW_HOLD")

    def test_payment_oversubscription_holds_related_invoices(self):
        self.p["payments"][0]["available_minor"] = 11999
        r = self.compile()
        self.assertIn("PAYMENT_OVER_ALLOCATED", findings(r))
        self.assertEqual(r["totals"]["proposed_minor"], 0)

    def test_independent_component_can_progress(self):
        self.p["payments"][0]["available_minor"] = 1
        self.p["allocations"].append(dict(snapshot_id=self.p["snapshot_id"], allocation_id="A-4",
                                          payment_id="PAY-3", invoice_id="INV-3", amount_minor=3000,
                                          remittance_ref="R-3"))
        r = self.compile()
        self.assertEqual(r["totals"]["proposed_minor"], 3000)
        self.assertEqual(r["allocations"][-1]["state"], "PROPOSED_ONLY")

    def test_unknown_invoice_kept_visible_and_holds_payment(self):
        self.p["allocations"][0]["invoice_id"] = "UNKNOWN"
        r = self.compile()
        self.assertIn("UNKNOWN_INVOICE", findings(r))
        self.assertEqual(len(r["allocations"]), 3)
        self.assertEqual(r["totals"]["proposed_minor"], 0)

    def test_unknown_payment_holds_invoice_component(self):
        self.p["allocations"][2]["payment_id"] = "UNKNOWN"
        r = self.compile()
        self.assertIn("UNKNOWN_PAYMENT", findings(r))
        self.assertEqual(r["totals"]["proposed_minor"], 0)

    def test_duplicate_pair_not_silently_double_applied(self):
        row = dict(self.p["allocations"][0], allocation_id="A-4", amount_minor=1)
        self.p["allocations"].append(row)
        r = self.compile()
        self.assertIn("DUPLICATE_PAIR_REVIEW", findings(r))
        self.assertEqual(r["totals"]["proposed_minor"], 0)

    def test_same_amount_different_native_payment_is_not_deduped(self):
        self.p["payments"].append(dict(self.p["payments"][2], payment_id="PAY-4", source_event_id="BANK-4"))
        self.assertEqual(self.compile()["totals"]["source_payment_available_minor"], 20000)

    def test_reminted_native_payment_rejected(self):
        self.p["payments"].append(dict(self.p["payments"][0], payment_id="COPY"))
        self.reject(code="DUPLICATE_SOURCE_EVENT")

    def test_reminted_native_invoice_rejected(self):
        self.p["invoices"].append(dict(self.p["invoices"][0], invoice_id="COPY"))
        self.reject(code="DUPLICATE_SOURCE_EVENT")

    def test_duplicate_stable_ids_rejected(self):
        for kind in rr.COLUMNS:
            p = sample()
            p[kind].append(copy.deepcopy(p[kind][0]))
            self.reject(p, "DUPLICATE_STABLE_ID")

    def test_cross_account_is_hold(self):
        self.p["payments"][0]["account_id"] = "ACCT-B"
        self.assertIn("ACCOUNT_MISMATCH", findings(self.compile()))

    def test_no_currency_coercion(self):
        for target in (self.p, self.p["payments"][0], self.p["invoices"][0]):
            target["currency"] = "EUR"
            self.reject(code="USD_ONLY_NO_FX")
            target["currency"] = "USD"

    def test_dispute_void_conflict_never_downgraded(self):
        for status in ("DISPUTED", "VOID", "CONFLICT"):
            self.p["invoices"][0]["status"] = status
            r = self.compile()
            self.assertIn("INVOICE_" + status, findings(r))
            self.assertEqual(r["totals"]["proposed_minor"], 0)

    def test_future_invoice_and_payment(self):
        self.p["invoices"][0]["issue_date"] = "2026-09-18"
        self.p["payments"][0]["received_date"] = "2026-09-19"
        codes = findings(self.compile())
        self.assertTrue({"INVOICE_AFTER_HORIZON", "PAYMENT_AFTER_HORIZON"}.issubset(codes))

    def test_pre_invoice_receipt_review_not_automatic_application(self):
        self.p["payments"][0]["received_date"] = "2026-08-31"
        self.assertIn("PRE_INVOICE_RECEIPT_REVIEW", findings(self.compile()))

    def test_same_day_payment_allowed(self):
        self.p["payments"][0]["received_date"] = "2026-09-01"
        self.assertEqual(self.compile()["totals"]["proposed_minor"], 13000)

    def test_empty_and_no_instruction_snapshots(self):
        for kind in rr.COLUMNS:
            self.p[kind] = []
        self.assertEqual(self.compile()["totals"]["proposed_minor"], 0)
        self.p = sample()
        self.p["allocations"] = []
        r = self.compile()
        self.assertEqual(r["totals"]["hypothetical_unapplied_minor"], 17000)

    def test_zero_balance_and_zero_available_cannot_absorb(self):
        self.p["invoices"][0]["remaining_minor"] = 0
        self.p["payments"][0]["available_minor"] = 0
        r = self.compile()
        self.assertEqual(r["totals"]["proposed_minor"], 0)
        self.assertTrue({"INVOICE_OVER_ALLOCATED", "PAYMENT_OVER_ALLOCATED"}.issubset(findings(r)))

    def test_monetary_type_and_bounds(self):
        for value in (True, 1.0, "100", -1, 0, rr.MAX_MINOR + 1):
            self.p["allocations"][0]["amount_minor"] = value
            self.reject()

    def test_exact_large_integer_arithmetic(self):
        self.p["allocations"] = self.p["allocations"][:1]
        self.p["allocations"][0]["amount_minor"] = rr.MAX_MINOR
        self.p["payments"][0]["available_minor"] = rr.MAX_MINOR
        self.p["invoices"][0]["remaining_minor"] = rr.MAX_MINOR
        self.assertEqual(self.compile()["totals"]["proposed_minor"], rr.MAX_MINOR)

    def test_unknown_fields_and_admission_flags_rejected(self):
        self.p["approved"] = True
        self.reject(code="SCHEMA_KEYS_MISMATCH")

    def test_unsafe_identifiers(self):
        for value in ("=1+1", "@person", "test@example.com", "x\n", "a/b", "a\u200b", "\ud800", "a"*65):
            self.p["payments"][0]["payment_id"] = value
            self.reject()

    def test_exact_plain_builtins(self):
        class Mapping(dict):
            pass
        self.reject(Mapping(self.p), "NON_PLAIN_JSON_VALUE")

    def test_bad_dates(self):
        for value in ("20260917", "2026-02-30", "2026-9-17", "2026-09-17Z", True):
            self.p["analysis_date"] = value
            self.reject()

    def test_strict_json_ingress(self):
        for raw in (b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":1.0}', b'{"a":Infinity}',
                    b'{"a":' + b'9'*5000 + b'}', b'['*1000 + b'0' + b']'*1000,
                    b'\xff', b' '*(rr.MAX_BYTES + 1)):
            with self.assertRaises(rr.ReviewError):
                rr.loads(raw)

    def test_csv_equivalence_and_header_order(self):
        raw = as_csv(self.p)
        p = rr.from_csv(self.p["snapshot_id"], self.p["analysis_date"], raw)
        self.assertEqual(rr.compile_review(p), self.compile())
        # BOM is supported for ordinary spreadsheet-exported UTF-8 CSV.
        raw["invoices"] = b'\xef\xbb\xbf' + raw["invoices"]
        self.assertEqual(rr.compile_review(rr.from_csv(self.p["snapshot_id"], self.p["analysis_date"], raw)), self.compile())

    def test_csv_headers_ragged_and_numeric_traps(self):
        valid = as_csv(self.p)
        for raw in (b"invoice_id,invoice_id\na,b\n", valid["invoices"] + b"missing,fields\n",
                    valid["invoices"].replace(b",10000,", b",1e4,"),
                    valid["invoices"].replace(b",10000,", b",+10000,"),
                    valid["invoices"].replace(b",10000,", b",010000,"),
                    valid["invoices"].replace(b",10000,", b",100.00,")):
            inputs = {**valid, "invoices": raw}
            with self.assertRaises(rr.ReviewError):
                rr.from_csv(self.p["snapshot_id"], self.p["analysis_date"], inputs)

    def test_json_bundle_roundtrip_and_original_bytes(self):
        raw = json.dumps(self.p, indent=2).encode()
        members = rr.bundle_members(self.p, {"input.json": raw}, "json")
        self.assertEqual(members["input.json"], raw)
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)/"review"
            rr.write_bundle(out, members)
            self.assertTrue(rr.verify_bundle(out))
            with self.assertRaises(FileExistsError):
                rr.write_bundle(out, members)
            self.assertTrue(rr.verify_bundle(out))

    def test_csv_bundle_roundtrip(self):
        inputs = {f"input_{k}.csv": v for k, v in as_csv(self.p).items()}
        members = rr.bundle_members(self.p, inputs, "csv")
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)/"review"
            rr.write_bundle(out, members)
            self.assertTrue(rr.verify_bundle(out))

    def test_every_bundle_artifact_verified(self):
        members = rr.bundle_members(self.p, {"input.json": rr.canonical(self.p)}, "json")
        for target in members:
            with self.subTest(target=target), tempfile.TemporaryDirectory() as td:
                out = Path(td)/"review"
                rr.write_bundle(out, members)
                (out/target).write_bytes(b"tamper\n")
                with self.assertRaises((rr.ReviewError, OSError)):
                    rr.verify_bundle(out)

    def test_raw_source_cannot_be_unrelated_to_snapshot(self):
        other = copy.deepcopy(self.p)
        other["payments"][0]["available_minor"] += 1
        with self.assertRaises(rr.ReviewError):
            rr.bundle_members(self.p, {"input.json": rr.canonical(other)}, "json")

    @unittest.skipUnless(hasattr(os, "O_NOFOLLOW"), "requires no-follow descriptors")
    def test_symlink_input_and_output_refused(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            (p/"real").write_bytes(b"{}")
            (p/"link").symlink_to(p/"real")
            with self.assertRaises(OSError):
                rr.read_regular(p/"link")
            members = rr.bundle_members(self.p, {"input.json": rr.canonical(self.p)}, "json")
            with self.assertRaises(OSError):
                rr.write_bundle(p/"link", members)
            rr.write_bundle(p/"out", members)
            (p/"out"/"review.md").unlink()
            (p/"out"/"review.md").symlink_to(p/"real")
            with self.assertRaises(OSError):
                rr.verify_bundle(p/"out")

    def test_extra_or_missing_bundle_member_refused(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)/"review"
            rr.write_bundle(out, rr.bundle_members(self.p, {"input.json": rr.canonical(self.p)}, "json"))
            (out/"unexpected").write_bytes(b"x")
            with self.assertRaises(rr.ReviewError):
                rr.verify_bundle(out)
            (out/"unexpected").unlink()
            (out/"payments.csv").unlink()
            with self.assertRaises(rr.ReviewError):
                rr.verify_bundle(out)

    def test_markdown_contains_exact_findings_and_csv_residuals(self):
        self.p["payments"][0]["account_id"] = "OTHER"
        report = self.compile()
        rendered = rr.render(report)
        self.assertIn(b"ACCOUNT_MISMATCH", rendered["review.md"])
        self.assertIn(b"A-1", rendered["review.md"])
        self.assertIn(b"PAY-3", rendered["payments.csv"])
        self.assertIn(b"nothing posted", rendered["review.md"])

    def test_real_cli_json_csv_and_optimized_propagation(self):
        executable = [sys.executable] + (["-O"] if sys.flags.optimize else [])
        command = executable + ["-m", "revenue.accounts_receivable_leakage_desk.remittance_review"]
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            (p/"input.json").write_bytes(rr.canonical(self.p))
            run = subprocess.run(command + ["compile", "--input", str(p/"input.json"), "--out", str(p/"json")], capture_output=True, text=True, timeout=20)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertIn("NO_POSTING", run.stdout)
            args = command + ["compile-csv", "--snapshot-id", self.p["snapshot_id"], "--analysis-date", self.p["analysis_date"], "--out", str(p/"csv")]
            for kind, raw in as_csv(self.p).items():
                (p/f"{kind}.csv").write_bytes(raw)
                args += ["--" + kind, str(p/f"{kind}.csv")]
            run = subprocess.run(args, capture_output=True, text=True, timeout=20)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual((p/"json"/"review.json").read_bytes(), (p/"csv"/"review.json").read_bytes())
            for out in ("json", "csv"):
                run = subprocess.run(command + ["verify-bundle", "--directory", str(p/out)], capture_output=True, text=True, timeout=20)
                self.assertEqual(run.returncode, 0, run.stderr)
            (p/"bad.json").write_text('{"secret-ish-input":"private-value", "x":NaN}')
            run = subprocess.run(command + ["compile", "--input", str(p/"bad.json"), "--out", str(p/"bad")], capture_output=True, text=True, timeout=20)
            self.assertEqual(run.returncode, 2)
            self.assertNotIn("private-value", run.stderr)
            self.assertNotIn("Traceback", run.stderr)

    def test_scale_5000_invoices_10000_payments(self):
        base = sample()
        snapshot = base["snapshot_id"]
        base["invoices"] = [dict(base["invoices"][0], invoice_id=f"I-{n}", source_event_id=f"EI-{n}", remaining_minor=2) for n in range(5000)]
        template = base["payments"][0]
        base["payments"] = [dict(template, payment_id=f"P-{n}", source_event_id=f"EP-{n}", available_minor=1) for n in range(10000)]
        base["allocations"] = [dict(snapshot_id=snapshot, allocation_id=f"A-{n}", payment_id=f"P-{n}", invoice_id=f"I-{n//2}", amount_minor=1, remittance_ref=f"R-{n}") for n in range(10000)]
        report = rr.compile_review(base)
        self.assertEqual(report["totals"]["proposed_minor"], 10000)
        self.assertEqual(report["totals"]["hypothetical_unapplied_minor"], 0)
        self.assertEqual(report["totals"]["hypothetical_remaining_minor"], 0)
        base["payments"].append(dict(template, payment_id="OVER", source_event_id="EP-OVER"))
        self.reject(base, "ROW_LIMIT_OR_ARRAY_TYPE")


    def test_maximum_declared_scope_20000_allocations(self):
        p = sample()
        snapshot = p["snapshot_id"]
        invoice, payment = p["invoices"][0], p["payments"][0]
        p["invoices"] = [dict(invoice, invoice_id=f"I-{n}", source_event_id=f"EI-{n}", remaining_minor=4) for n in range(5000)]
        p["payments"] = [dict(payment, payment_id=f"P-{n}", source_event_id=f"EP-{n}", available_minor=2) for n in range(10000)]
        p["allocations"] = [dict(snapshot_id=snapshot, allocation_id=f"A-{n}", payment_id=f"P-{n//2}", invoice_id=f"I-{n%5000}", amount_minor=1, remittance_ref=f"R-{n}") for n in range(20000)]
        report = rr.compile_review(p)
        self.assertEqual(report["totals"]["proposed_minor"], 20000)
        self.assertTrue(rr.verify_review(p, rr.loads(rr.canonical(report), artifact=True)))

    def test_random_graph_conservation_and_permutation(self):
        import random
        rng = random.Random(917)
        for trial in range(30):
            p = sample()
            p["allocations"] = []
            for n in range(rng.randrange(12)):
                p["allocations"].append(dict(snapshot_id=p["snapshot_id"], allocation_id=f"A-{n}",
                    payment_id=rng.choice(["PAY-1", "PAY-2", "PAY-3", "MISSING"]),
                    invoice_id=rng.choice(["INV-1", "INV-2", "INV-3", "MISSING"]),
                    amount_minor=rng.randrange(1, 15000), remittance_ref=f"R-{n}"))
            r = rr.compile_review(p)
            for row in r["payments"]:
                self.assertEqual(row["available_minor"], row["proposed_minor"] + row["hypothetical_unapplied_minor"])
                self.assertGreaterEqual(row["hypothetical_unapplied_minor"], 0)
            for row in r["invoices"]:
                self.assertEqual(row["remaining_minor"], row["proposed_minor"] + row["hypothetical_remaining_minor"])
                self.assertGreaterEqual(row["hypothetical_remaining_minor"], 0)
            for kind in rr.COLUMNS:
                rng.shuffle(p[kind])
            self.assertEqual(rr.compile_review(p), r)


    if not sys.flags.optimize:
        def test_full_suite_in_real_optimized_interpreter(self):
            run = subprocess.run([sys.executable, "-O", "-m", "unittest", "-q", "test_ar_remittance_review"],
                                 capture_output=True, text=True, timeout=60)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            self.assertIn("Ran 46 tests", run.stderr)



if __name__ == "__main__":
    unittest.main()
