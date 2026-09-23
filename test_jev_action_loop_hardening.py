import copy
import hashlib
import json
import unittest

from integrations.command_center import jev_action_loop as loop
from test_jev_action_loop import decision, obs, target


class JevActionLoopHardeningTests(unittest.TestCase):
    def test_newer_uncertain_read_after_known_state_blocks_action(self):
        rows = [
            obs(event_id="known", status="OPEN"),
            obs(
                event_id="uncertain",
                status="DELIVERY_UNCERTAIN",
                provider_event_at="2026-09-20T18:05:00Z",
                observed_at="2026-09-20T18:05:01Z",
            ),
        ]
        got = loop.compile_action(rows, decision(), target())
        self.assertEqual(got["disposition"], "HOLD_PROVIDER_STATE")
        self.assertEqual(got["effective_status"], "OPEN")

    def test_make_receipt_rejects_tampered_plan(self):
        plan = loop.compile_action([obs()], decision(), target())
        mutated = copy.deepcopy(plan)
        mutated["target"]["destination_id"] = "COTHER"
        with self.assertRaises(loop.ActionLoopError):
            loop.make_readback_receipt(
                mutated,
                provider_resource_id="message-1",
                provider_observed_operation_id=mutated["operation_id"],
                source_url="https://example.test/readback",
                outcome="CONFIRMED",
                attempted_at="2026-09-20T18:15:00Z",
                observed_at="2026-09-20T18:15:01Z",
            )

    def test_operation_id_tamper_rejected_even_with_rehashed_plan(self):
        plan = loop.compile_action([obs()], decision(), target())
        mutated = copy.deepcopy(plan)
        mutated["operation_id"] = "jev16537-" + ("0" * 40)
        core_keys = {
            "schema", "resource_key", "effective_status", "effective_event_key",
            "decision_sha256", "target", "selected_action", "operation_id",
            "provider_disposition", "confidence_ppm", "min_confidence_ppm",
        }
        canonical = json.dumps(
            {key: mutated[key] for key in core_keys},
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode()
        mutated["plan_sha256"] = hashlib.sha256(canonical).hexdigest()
        result = {key: value for key, value in mutated.items() if key != "result_sha256"}
        mutated["result_sha256"] = hashlib.sha256(
            json.dumps(
                result,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode()
        ).hexdigest()
        with self.assertRaises(loop.ActionLoopError):
            loop.verify_plan(mutated)


if __name__ == "__main__":
    unittest.main()
