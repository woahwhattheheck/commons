import json
import pathlib
import subprocess
import unittest

ROOT = pathlib.Path(__file__).resolve().parent


class RepairBookingPreflightTests(unittest.TestCase):
    def test_machine_contract_is_bounded_and_synthetic_only(self):
        contract = json.loads((ROOT / "revenue/repair_booking_preflight/contract.json").read_text())
        self.assertEqual(contract["id"], "repair-booking-exactly-once-v1")
        self.assertEqual(contract["acceptance"]["fixture_count"], 20)
        self.assertEqual(contract["acceptance"]["duplicate_appointments"], 0)
        self.assertTrue(contract["scope"]["public_runner"] == "synthetic_only")
        self.assertFalse(contract["scope"]["creates_real_appointments"])
        self.assertFalse(contract["scope"]["customer_data_allowed"])
        self.assertEqual(contract["offer"]["diagnostic_price_usd"], 199)
        self.assertEqual(contract["offer"]["proof_price_usd"], 2500)

    def test_runtime_accepts_safe_suite_and_fails_closed_on_duplicate(self):
        script = """
const api = require('./repair-booking-preflight.js');
const safe = api.runSuite('safe');
const fault = api.runSuite('duplicate');
if (safe.fixture_count !== 20 || safe.passed !== 20 || safe.failed !== 0) process.exit(2);
if (safe.duplicate_appointments !== 0 || safe.first_unsafe_edge !== null) process.exit(3);
if (fault.fixture_count !== 20 || fault.passed !== 19 || fault.failed !== 1) process.exit(4);
if (fault.duplicate_appointments !== 1) process.exit(5);
if (!fault.first_unsafe_edge || fault.first_unsafe_edge.fixture_id !== 'RB-008') process.exit(6);
if (fault.first_unsafe_edge.reason !== 'duplicate_booking') process.exit(7);
console.log(JSON.stringify({safe:safe.passed,fault:fault.first_unsafe_edge}));
"""
        result = subprocess.run(
            ["node", "-e", script],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_public_page_exposes_runner_receipt_and_contact(self):
        page = (ROOT / "repair-booking-preflight.html").read_text()
        self.assertIn('id="run-safe"', page)
        self.assertIn('id="run-fault"', page)
        self.assertIn('id="export"', page)
        self.assertIn("./repair-booking-preflight.js", page)
        self.assertIn("tokenjunkielabs@gmail.com", page)
        self.assertIn("Synthetic-only public tool", page)
        self.assertNotIn("login", page.lower().replace("no login", ""))


if __name__ == "__main__":
    unittest.main()
