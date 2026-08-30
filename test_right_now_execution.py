from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "right_now_revenue", ROOT / "host" / "right_now_revenue.py"
)
assert SPEC and SPEC.loader
control = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(control)


class RightNowExecutionTests(unittest.TestCase):
    def test_committed_snapshot_is_exact_compiler_output(self) -> None:
        expected = control.build_control()
        actual = control.read_object(
            ROOT / "revenue" / "right_now" / "control.json"
        )
        self.assertEqual(actual, expected)

    def test_truth_never_promotes_internal_activity(self) -> None:
        value = control.build_control()
        self.assertEqual(value["truth"]["collected_cash_usd"], 0)
        self.assertEqual(value["truth"]["verified_positive_replies"], 0)
        self.assertEqual(value["truth"]["accepted_scopes"], 0)
        self.assertEqual(value["truth"]["transport_actions"], 0)
        self.assertFalse(value["truth"]["active_chargeable_checkout"])

    def test_queue_reuses_collision_and_research_decisions(self) -> None:
        queue = {row["prospect_id"]: row for row in control.build_control()["execution_queue"]}
        self.assertEqual(queue["anythingllm-mintplex"]["decision"], "HOLD_DO_NOT_RESEND")
        self.assertEqual(queue["metaforms"]["decision"], "HOLD_DO_NOT_RESEND")
        self.assertEqual(queue["signoz"]["decision"], "RESEARCH_REQUIRED")
        self.assertTrue(queue["anythingllm-mintplex"]["collision_receipts"])
        self.assertFalse(any(row["transport_authorized"] for row in queue.values()))

    def test_offer_prices_are_owned_by_canonical_catalogs(self) -> None:
        value = control.build_control()
        self.assertEqual(
            {row["id"]: row["price_usd"] for row in value["offers"]},
            {
                "ho-agent-failure-diagnostic": 199,
                "same-day-agent-survival-proof": 2500,
                "ho-pixel-pack": 800,
                "ho-meeting-packet": 1200,
                "ho-issue-to-pr": 2500,
            },
        )

    def test_source_receipts_cover_every_composed_root(self) -> None:
        receipts = control.build_control()["source_receipts"]
        self.assertEqual(
            {row["path"] for row in receipts},
            {
                "revenue/right_now/catalog.json",
                "revenue/right_now/diagnostic_offer.json",
                "revenue/smart_outreach/candidates.json",
                "revenue/payment_ready/current_receipt.json",
                "revenue/human_outcomes/offers.json",
                "revenue/production_survival/offer.json",
            },
        )
        self.assertTrue(all(len(row["sha256"]) == 64 for row in receipts))

    def test_cash_disagreement_fails_closed(self) -> None:
        original = control.read_object

        def read_with_drift(path: Path):
            value = original(path)
            if path == control.PAYMENT_PATH:
                value = copy.deepcopy(value)
                value["facts"]["collected_cash_usd"] = 1
                value["cash_claimed"] = True
            return value

        control.read_object = read_with_drift
        try:
            with self.assertRaises(control.ControlError):
                control.build_control()
        finally:
            control.read_object = original

    def test_price_drift_fails_closed(self) -> None:
        catalog = control.read_object(control.CATALOG_PATH)
        catalog["offers"][0]["price_usd"] += 1
        with self.assertRaises(control.ControlError):
            control.validate_catalog(catalog)

    def test_validate_detects_snapshot_drift(self) -> None:
        drift = control.build_control()
        drift["truth"]["ready_to_draft"] = 99
        with self.assertRaises(control.ControlError):
            control.validate_control(drift)

    def test_cli_is_deterministic_and_read_only(self) -> None:
        command = [sys.executable, str(ROOT / "host" / "right_now_revenue.py"), "compile"]
        first = subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)
        second = subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)
        self.assertEqual(first.stdout, second.stdout)
        self.assertEqual(json.loads(first.stdout), control.build_control())

    def test_cli_validates_committed_projection(self) -> None:
        result = subprocess.run(
            [sys.executable, str(ROOT / "host" / "right_now_revenue.py"), "validate"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.stdout.strip(), "VALID 5 offers 4 opportunities 0 transports USD 0 cash")

    def test_cli_rejects_drifted_projection(self) -> None:
        drift = control.build_control()
        drift["truth"]["collected_cash_usd"] = 5
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "drift.json")
            path.write_text(json.dumps(drift), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(ROOT / "host" / "right_now_revenue.py"), "validate", "--snapshot", str(path)],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 2)
        self.assertIn("committed control snapshot differs", result.stderr)

    def test_browser_projection_is_data_driven_and_has_fallback(self) -> None:
        script = (ROOT / "right-now.js").read_text(encoding="utf-8")
        page = (ROOT / "right-now.html").read_text(encoding="utf-8")
        self.assertIn("./revenue/right_now/control.json", script)
        self.assertIn('id="revenue-control"', page)
        self.assertIn("right-now.js", page)
        self.assertIn("JavaScript-off truth", page)


if __name__ == "__main__":
    unittest.main()
