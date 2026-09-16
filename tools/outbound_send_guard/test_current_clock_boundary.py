from __future__ import annotations

import inspect
import unittest
from datetime import datetime, timezone

from tools.outbound_send_guard import current
from tools.outbound_send_guard.test_current import evidence, intent


class CurrentClockBoundaryTests(unittest.TestCase):
    def test_reviewed_explicit_time_authority_emitters_do_not_exist(self):
        self.assertFalse(hasattr(current, "_compile_at"))
        self.assertFalse(hasattr(current, "_verify_at"))

    def test_current_authority_emitters_accept_no_clock_or_mode_argument(self):
        forbidden = {"now", "verified_at", "historical_at", "mode", "verifier_time"}
        for name in (
            "compile_current",
            "compile_current_bytes",
            "verify_current",
            "verify_current_bytes",
            "_compile_current_owned_clock",
            "_verify_current_owned_clock",
        ):
            parameters = set(inspect.signature(getattr(current, name)).parameters)
            self.assertFalse(parameters & forbidden, f"{name} exposes {parameters & forbidden}")

    def test_explicit_time_api_emits_distinct_historical_schema_and_no_clear_bits(self):
        old = datetime(2025, 1, 1, 0, 0, 20, tzinfo=timezone.utc)
        result = current.compile_historical_at(
            intent(requested_at="2025-01-01T00:00:10Z"),
            evidence(generated_at="2025-01-01T00:00:00Z", max_age=604800),
            historical_at=old,
        )
        payload = result["payload"]
        self.assertEqual(payload["schema_version"], current.HISTORICAL_RECEIPT_SCHEMA)
        self.assertEqual(payload["mode"], current.MODE_HISTORICAL)
        self.assertEqual(payload["historical_decision"], "ALLOW_NEW")
        self.assertEqual(payload["decision"], "HOLD")
        self.assertFalse(payload["current_preflight_clear"])
        self.assertFalse(payload["net_new_send_preflight_clear"])
        self.assertFalse(payload["reply_preflight_clear"])
        self.assertNotIn("verified_at", payload)
        self.assertNotIn("valid_until", payload)

    def test_only_explicit_time_helper_projects_facts_not_authority(self):
        it, _ = current._snapshot(intent(), "intent")
        ev, _ = current._snapshot(evidence(), "evidence")
        core_receipt = current.guard.evaluate(it, ev)
        projection = current._temporal_projection(
            it,
            ev,
            core_receipt["payload"],
            datetime(2026, 9, 14, 4, 55, 0, tzinfo=timezone.utc),
        )
        self.assertIsInstance(projection, tuple)
        self.assertEqual(len(projection), 3)
        self.assertIsInstance(projection[0], list)
        self.assertIsInstance(projection[1], dict)
        self.assertIsInstance(projection[2], datetime)
        self.assertNotIn("schema_version", projection[1])
        self.assertNotIn("current_preflight_clear", projection[1])


if __name__ == "__main__":
    unittest.main()
