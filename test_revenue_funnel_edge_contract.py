import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import revenue.revenue_funnel_control as package_api
from revenue.revenue_funnel_control.engine import FunnelError, compile_portfolio
from test_revenue_funnel_control import SHA_F, base_doc, event


class FunnelEdgeContractTests(unittest.TestCase):
    def test_package_lazy_api_resolves(self):
        self.assertTrue(callable(package_api.compile_bundle))
        self.assertTrue(callable(package_api.verify_bundle))

    def test_zero_value_accepted_work_is_not_a_collection_gap(self):
        doc = base_doc()
        op = doc["opportunities"][0]
        op["reference_amount_cents"] = 0
        next(row for row in op["events"] if row["kind"] == "PROPOSAL_SENT")["amount_cents"] = 0
        compiled = next(row for row in compile_portfolio(doc)["opportunities"] if row["id"] == "workshare-1")
        self.assertEqual(compiled["settlement_target_cents"], 0)
        self.assertEqual(compiled["next_action"], "DONE_ZERO_VALUE")
        self.assertFalse(compiled["economically_unfinished"])
        self.assertFalse(compiled["micro_batch_candidate"])

    def test_same_time_conflicting_invoice_amounts_fail_closed(self):
        doc = base_doc()
        op = doc["opportunities"][1]
        payment_index = next(i for i, row in enumerate(op["events"]) if row["kind"] == "PAYMENT_RECEIVED")
        op["events"].insert(
            payment_index,
            event("invoice-a", "INVOICE_ISSUED", "2026-09-16T13:30:00Z", source="SPONSOR_MESSAGE", amount=9000, sha=SHA_F),
        )
        op["events"].insert(
            payment_index + 1,
            event("invoice-b", "INVOICE_ISSUED", "2026-09-16T13:30:00Z", source="SPONSOR_MESSAGE", amount=10000, sha="1" * 64),
        )
        with self.assertRaises(FunnelError):
            compile_portfolio(doc)

    def test_same_time_equal_invoice_amounts_are_deterministic(self):
        doc = base_doc()
        op = doc["opportunities"][1]
        payment_index = next(i for i, row in enumerate(op["events"]) if row["kind"] == "PAYMENT_RECEIVED")
        op["events"].insert(
            payment_index,
            event("z-invoice", "INVOICE_ISSUED", "2026-09-16T13:30:00Z", source="SPONSOR_MESSAGE", amount=9000, sha=SHA_F),
        )
        op["events"].insert(
            payment_index + 1,
            event("a-invoice", "INVOICE_ISSUED", "2026-09-16T13:30:00Z", source="SPONSOR_MESSAGE", amount=9000, sha="1" * 64),
        )
        compiled = next(row for row in compile_portfolio(doc)["opportunities"] if row["id"] == "bounty-1")
        self.assertEqual(compiled["settlement_target_cents"], 9000)
        self.assertEqual(compiled["stage"], "PAID")

    def test_direct_python_non_string_keys_fail_cleanly(self):
        doc = base_doc()
        doc[1] = "foreign"
        with self.assertRaises(FunnelError):
            compile_portfolio(doc)

    def test_cli_rejects_float_and_oversized_integer_tokens(self):
        cases = [
            '{"schema":"TJL_REVENUE_FUNNEL_V1","evaluation_at":"2026-09-17T06:50:00Z","micro_batch_threshold_cents":1.5,"opportunities":[]}',
            '{"schema":"TJL_REVENUE_FUNNEL_V1","evaluation_at":"2026-09-17T06:50:00Z","micro_batch_threshold_cents":123456789012345678901234567890,"opportunities":[]}',
        ]
        for raw in cases:
            with self.subTest(raw=raw):
                with tempfile.TemporaryDirectory() as td:
                    root = Path(td)
                    inp = root / "input.json"
                    out = root / "output.json"
                    inp.write_text(raw, encoding="utf-8")
                    cp = subprocess.run(
                        [sys.executable, "-m", "revenue.revenue_funnel_control.engine", "compile", str(inp), str(out)],
                        check=False,
                        capture_output=True,
                        text=True,
                    )
                    self.assertEqual(cp.returncode, 2, cp.stderr + cp.stdout)
                    self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
