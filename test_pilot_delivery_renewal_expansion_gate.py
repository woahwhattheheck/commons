import unittest
from datetime import datetime, timedelta, timezone

from revenue.pilot_delivery_renewal_expansion_gate.test_gate import *  # noqa: F401,F403
from revenue.pilot_delivery_renewal_expansion_gate import common as common_module
from revenue.pilot_delivery_renewal_expansion_gate import engine
from revenue.pilot_delivery_renewal_expansion_gate import model as model_module


class CurrentSemanticGenerationTests(unittest.TestCase):
    def test_current_generation_ignores_ordinary_semantic_global_rebinding(self):
        dnr_packet = current_packet()
        dnr_packet["route_control"]["state"] = "DNR"
        before = engine.compile_current(dnr_packet)
        self.assertEqual(before["state"], "DNR")

        sentinel = object()
        mutations = [
            (engine, "DNR", "READY_FOR_RENEWAL_REVIEW"),
            (engine, "READY", "DNR"),
            (engine, "HOLD_ACCEPTANCE", "READY_FOR_RENEWAL_REVIEW"),
            (engine, "HOLD_PAYMENT", "READY_FOR_RENEWAL_REVIEW"),
            (engine, "HOLD_WINDOW", "READY_FOR_RENEWAL_REVIEW"),
            (engine, "HOLD_EVIDENCE", "READY_FOR_RENEWAL_REVIEW"),
            (engine, "_decision", lambda *_args, **_kwargs: ("READY_FOR_RENEWAL_REVIEW", [])),
            (engine, "_normalize", lambda value, _now: value),
            (engine, "_compile", lambda *_args, **_kwargs: {"state": "READY_FOR_RENEWAL_REVIEW"}),
            (engine, "authority_flags", lambda: {"external_send_authorized": True}),
            (model_module, "_age", lambda *_args, **_kwargs: 0),
            (model_module, "_source", lambda value, *_args, **_kwargs: value),
            (model_module, "PAYMENT_MAX_AGE_SECONDS", 10**18),
            (model_module, "ROUTE_MAX_AGE_SECONDS", 10**18),
            (model_module, "ROUTE_STATES", {"CLEAR", "UNASSESSED", "ACTIVE_OTHER_OWNER", "DNR", "READY_FOR_RENEWAL_REVIEW"}),
            (common_module, "_age", lambda *_args, **_kwargs: 0),
            (common_module, "_dt", lambda _value: datetime(2000, 1, 1, tzinfo=timezone.utc)),
            (common_module, "_source", lambda value, *_args, **_kwargs: value),
            (common_module, "canonical_json", lambda _value: b"{}\n"),
            (common_module, "digest", lambda _value: "0" * 64),
        ]
        previous = []
        try:
            for owner, name, replacement in mutations:
                previous.append((owner, name, getattr(owner, name, sentinel)))
                setattr(owner, name, replacement)
            after = engine.compile_current(dnr_packet)
        finally:
            for owner, name, old in reversed(previous):
                if old is sentinel:
                    delattr(owner, name)
                else:
                    setattr(owner, name, old)

        self.assertEqual(after["state"], "DNR")
        self.assertEqual(after["reasons"], ["ROUTE_DNR"])
        self.assertTrue(all(value is False for value in after["authority"].values()))
        self.assertNotEqual(after["receipt_digest"], "0" * 64)

    def test_rebinding_freshness_helpers_cannot_revive_stale_payment(self):
        stale = current_packet()
        old = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(days=200)
        old_text = old.strftime("%Y-%m-%dT%H:%M:%SZ")
        stale["payment"]["observed_at"] = old_text
        stale["payment"]["source"]["observed_at"] = old_text
        error_type = engine.GateError

        previous = [
            (model_module, "_age", model_module._age),
            (model_module, "PAYMENT_MAX_AGE_SECONDS", model_module.PAYMENT_MAX_AGE_SECONDS),
            (common_module, "_age", common_module._age),
        ]
        try:
            model_module._age = lambda *_args, **_kwargs: 0
            model_module.PAYMENT_MAX_AGE_SECONDS = 10**18
            common_module._age = lambda *_args, **_kwargs: 0
            with self.assertRaisesRegex(error_type, "stale evidence"):
                engine.compile_current(stale)
        finally:
            for owner, name, old_value in reversed(previous):
                setattr(owner, name, old_value)


if __name__ == "__main__":
    unittest.main()
