import copy
import hashlib
import json
import unittest

from integrations.command_center import jev_action_loop as loop


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def obs(
    event_id="e1",
    status="OPEN",
    provider_event_at="2026-09-20T18:00:00Z",
    observed_at="2026-09-20T18:00:01Z",
    resource_id="woahwhattheheck/commons#16537",
):
    return {
        "provider": "github",
        "scope": "woahwhattheheck/commons",
        "resource_id": resource_id,
        "event_id": event_id,
        "status": status,
        "provider_event_at": provider_event_at,
        "observed_at": observed_at,
        "source_url": "https://github.com/woahwhattheheck/commons/issues/16537",
    }


def decision(action="ROUTE_SLACK", confidence=900_000):
    return {
        "model": "jev-1.13.0",
        "surface": "triage",
        "selected_action": action,
        "confidence_ppm": confidence,
        "answers_sha256": sha("typed-answers"),
        "decided_at": "2026-09-20T18:10:00Z",
    }


def target():
    return {
        "provider": "slack",
        "destination_id": "C0BU51F1PL3",
        "thread_id": "1789928286.342349",
    }


class StrictIngressTests(unittest.TestCase):
    def test_duplicate_key_rejected(self):
        with self.assertRaises(loop.ActionLoopError):
            loop.strict_loads('{"a":1,"a":2}')

    def test_nonfinite_rejected(self):
        with self.assertRaises(loop.ActionLoopError):
            loop.strict_loads('{"a":NaN}')

    def test_float_rejected(self):
        with self.assertRaises(loop.ActionLoopError):
            loop.strict_loads('{"a":0.5}')

    def test_future_provider_event_rejected(self):
        row = obs(provider_event_at="2026-09-20T18:00:02Z", observed_at="2026-09-20T18:00:01Z")
        with self.assertRaises(loop.ActionLoopError):
            loop.event_key(row)


class IdentityTests(unittest.TestCase):
    def test_event_key_is_immutable_provider_identity(self):
        a = obs(observed_at="2026-09-20T18:00:01Z")
        b = obs(observed_at="2026-09-20T18:05:01Z")
        self.assertEqual(loop.event_key(a), loop.event_key(b))

    def test_resource_key_joins_distinct_events(self):
        self.assertEqual(loop.resource_key(obs(event_id="one")), loop.resource_key(obs(event_id="two")))

    def test_event_identity_collision_rejected(self):
        a = obs(event_id="same", status="OPEN")
        b = obs(event_id="same", status="MERGED", provider_event_at="2026-09-20T18:05:00Z",
                observed_at="2026-09-20T18:05:01Z")
        with self.assertRaises(loop.ActionLoopError):
            loop.reconcile_observations([a, b])

    def test_multiple_resources_rejected(self):
        with self.assertRaises(loop.ActionLoopError):
            loop.reconcile_observations([obs(), obs(event_id="e2", resource_id="other#1")])


class ReconciliationTests(unittest.TestCase):
    def test_later_merged_supersedes_delivery_uncertain(self):
        rows = [
            obs(event_id="e1", status="DELIVERY_UNCERTAIN"),
            obs(event_id="e2", status="MERGED", provider_event_at="2026-09-20T18:05:00Z",
                observed_at="2026-09-20T18:05:01Z"),
        ]
        got = loop.reconcile_observations(rows)
        self.assertEqual(got["effective_status"], "MERGED")
        self.assertEqual(got["disposition"], "CURRENT")

    def test_terminal_held_over_later_unknown(self):
        rows = [
            obs(event_id="m", status="MERGED"),
            obs(event_id="u", status="UNKNOWN", provider_event_at="2026-09-20T18:05:00Z",
                observed_at="2026-09-20T18:05:01Z"),
        ]
        got = loop.reconcile_observations(rows)
        self.assertEqual(got["effective_status"], "MERGED")
        self.assertEqual(got["disposition"], "DEFINITIVE_STATE_HELD_OVER_UNCERTAIN_READ")

    def test_terminal_held_over_later_open(self):
        rows = [
            obs(event_id="m", status="MERGED"),
            obs(event_id="stale-search", status="OPEN", provider_event_at="2026-09-20T18:05:00Z",
                observed_at="2026-09-20T18:05:01Z"),
        ]
        got = loop.reconcile_observations(rows)
        self.assertEqual(got["effective_status"], "MERGED")
        self.assertEqual(got["disposition"], "HOLD_IMPOSSIBLE_PROVIDER_REGRESSION")
        self.assertIn(loop.event_key(rows[1]), got["suppressed_event_keys"])

    def test_closed_unmerged_can_reopen(self):
        rows = [
            obs(event_id="c", status="CLOSED_UNMERGED"),
            obs(event_id="r", status="OPEN", provider_event_at="2026-09-20T18:05:00Z",
                observed_at="2026-09-20T18:05:01Z"),
        ]
        got = loop.reconcile_observations(rows)
        self.assertEqual(got["effective_status"], "OPEN")
        self.assertEqual(got["disposition"], "CURRENT")

    def test_ci_failure_can_enter_rerun(self):
        a = obs(event_id="f", status="FAILURE")
        b = obs(event_id="q", status="QUEUED", provider_event_at="2026-09-20T18:05:00Z",
                observed_at="2026-09-20T18:05:01Z")
        a["provider"] = b["provider"] = "ci"
        a["scope"] = b["scope"] = "woahwhattheheck/commons/actions"
        a["resource_id"] = b["resource_id"] = "run:123"
        got = loop.reconcile_observations([a, b])
        self.assertEqual(got["effective_status"], "QUEUED")
        self.assertEqual(got["disposition"], "CURRENT")

    def test_newer_terminal_wins(self):
        rows = [
            obs(event_id="o", status="OPEN"),
            obs(event_id="c", status="CLOSED_UNMERGED", provider_event_at="2026-09-20T18:05:00Z",
                observed_at="2026-09-20T18:05:01Z"),
        ]
        got = loop.reconcile_observations(rows)
        self.assertEqual(got["effective_status"], "CLOSED_UNMERGED")
        self.assertEqual(got["disposition"], "CURRENT")

    def test_same_provider_time_conflict_holds(self):
        rows = [
            obs(event_id="a", status="OPEN"),
            obs(event_id="b", status="MERGED", observed_at="2026-09-20T18:00:02Z"),
        ]
        got = loop.reconcile_observations(rows)
        self.assertEqual(got["disposition"], "HOLD_CONTRADICTORY_PROVIDER_TIME")
        self.assertIsNone(got["effective_status"])

    def test_uncertain_only_holds(self):
        got = loop.reconcile_observations([obs(status="DELIVERY_UNCERTAIN")])
        self.assertEqual(got["disposition"], "HOLD_LATEST_PROVIDER_STATE_UNCERTAIN")


class PlanningTests(unittest.TestCase):
    def test_stable_operation_id(self):
        first = loop.compile_action([obs()], decision(), target())
        second = loop.compile_action([obs()], decision(), target())
        self.assertEqual(first["operation_id"], second["operation_id"])
        self.assertEqual(first["plan_sha256"], second["plan_sha256"])
        self.assertEqual(first["result_sha256"], second["result_sha256"])
        self.assertEqual(first["disposition"], "ACTION_READY")

    def test_low_confidence_holds(self):
        got = loop.compile_action([obs()], decision(confidence=699_999), target())
        self.assertEqual(got["disposition"], "HOLD_LOW_CONFIDENCE")

    def test_no_action_is_noop(self):
        got = loop.compile_action([obs()], decision(action="NO_ACTION"), target())
        self.assertEqual(got["disposition"], "NO_ACTION")

    def test_bool_confidence_rejected(self):
        bad = decision()
        bad["confidence_ppm"] = True
        with self.assertRaises(loop.ActionLoopError):
            loop.compile_action([obs()], bad, target())

    def test_provider_uncertain_blocks_action(self):
        got = loop.compile_action([obs(status="DELIVERY_UNCERTAIN")], decision(), target())
        self.assertEqual(got["disposition"], "HOLD_PROVIDER_STATE")

    def _receipt(self, plan, outcome="CONFIRMED"):
        marker = plan["operation_id"] if outcome == "CONFIRMED" else None
        resource = "1789930434.874059" if outcome == "CONFIRMED" else None
        return loop.make_readback_receipt(
            plan,
            provider_resource_id=resource,
            provider_observed_operation_id=marker,
            source_url="https://tokenjunkielabs.slack.com/archives/C0BU51F1PL3/p1789930434874059",
            outcome=outcome,
            attempted_at="2026-09-20T18:15:00Z",
            observed_at="2026-09-20T18:15:01Z",
        )

    def test_confirmed_receipt_makes_action_idempotent(self):
        plan = loop.compile_action([obs()], decision(), target())
        receipt = self._receipt(plan)
        got = loop.compile_action([obs()], decision(), target(), [receipt])
        self.assertEqual(got["operation_id"], plan["operation_id"])
        self.assertEqual(got["plan_sha256"], plan["plan_sha256"])
        self.assertEqual(got["disposition"], "ALREADY_APPLIED")

    def test_delivery_uncertain_never_replays(self):
        plan = loop.compile_action([obs()], decision(), target())
        receipt = self._receipt(plan, "DELIVERY_UNCERTAIN")
        got = loop.compile_action([obs()], decision(), target(), [receipt])
        self.assertEqual(got["disposition"], "HOLD_DELIVERY_UNCERTAIN")
        self.assertEqual(got["operation_id"], plan["operation_id"])

    def test_rejected_retry_reuses_operation_id(self):
        plan = loop.compile_action([obs()], decision(), target())
        receipt = self._receipt(plan, "REJECTED")
        got = loop.compile_action([obs()], decision(), target(), [receipt])
        self.assertEqual(got["disposition"], "RETRY_SAME_OPERATION_ID")
        self.assertEqual(got["operation_id"], plan["operation_id"])
        self.assertEqual(got["plan_sha256"], plan["plan_sha256"])


class ReceiptTests(unittest.TestCase):
    def setUp(self):
        self.plan = loop.compile_action([obs()], decision(), target())

    def test_confirmed_requires_exact_operation_marker(self):
        with self.assertRaises(loop.ActionLoopError):
            loop.make_readback_receipt(
                self.plan,
                provider_resource_id="message-1",
                provider_observed_operation_id="jev16537-wrong",
                source_url="https://example.test/readback",
                outcome="CONFIRMED",
                attempted_at="2026-09-20T18:15:00Z",
                observed_at="2026-09-20T18:15:01Z",
            )

    def test_confirmed_receipt_verifies(self):
        receipt = loop.make_readback_receipt(
            self.plan,
            provider_resource_id="message-1",
            provider_observed_operation_id=self.plan["operation_id"],
            source_url="https://example.test/readback",
            outcome="CONFIRMED",
            attempted_at="2026-09-20T18:15:00Z",
            observed_at="2026-09-20T18:15:01Z",
        )
        got = loop.verify_receipt(receipt)
        self.assertTrue(got["confirmed"])

    def test_receipt_tamper_rejected(self):
        receipt = loop.make_readback_receipt(
            self.plan,
            provider_resource_id="message-1",
            provider_observed_operation_id=self.plan["operation_id"],
            source_url="https://example.test/readback",
            outcome="CONFIRMED",
            attempted_at="2026-09-20T18:15:00Z",
            observed_at="2026-09-20T18:15:01Z",
        )
        receipt["destination_id"] = "COTHER"
        with self.assertRaises(loop.ActionLoopError):
            loop.verify_receipt(receipt)

    def test_receipt_for_other_operation_is_not_replayed(self):
        receipt = loop.make_readback_receipt(
            self.plan,
            provider_resource_id="message-1",
            provider_observed_operation_id=self.plan["operation_id"],
            source_url="https://example.test/readback",
            outcome="CONFIRMED",
            attempted_at="2026-09-20T18:15:00Z",
            observed_at="2026-09-20T18:15:01Z",
        )
        different = loop.compile_action([obs()], decision("POST_DIGEST"), target(), [receipt])
        self.assertNotEqual(different["operation_id"], self.plan["operation_id"])
        self.assertEqual(different["disposition"], "ACTION_READY")

    def test_receipt_transplant_by_operation_id_tamper_rejected(self):
        receipt = loop.make_readback_receipt(
            self.plan,
            provider_resource_id="message-1",
            provider_observed_operation_id=self.plan["operation_id"],
            source_url="https://example.test/readback",
            outcome="CONFIRMED",
            attempted_at="2026-09-20T18:15:00Z",
            observed_at="2026-09-20T18:15:01Z",
        )
        different = loop.compile_action([obs()], decision("POST_DIGEST"), target())
        receipt["operation_id"] = different["operation_id"]
        receipt["provider_observed_operation_id"] = different["operation_id"]
        with self.assertRaises(loop.ActionLoopError):
            loop.compile_action([obs()], decision("POST_DIGEST"), target(), [receipt])

    def test_plan_tamper_rejected(self):
        mutated = copy.deepcopy(self.plan)
        mutated["selected_action"] = "POST_DIGEST"
        with self.assertRaises(loop.ActionLoopError):
            loop.verify_plan(mutated)

    def test_result_disposition_tamper_rejected(self):
        mutated = copy.deepcopy(self.plan)
        mutated["disposition"] = "ALREADY_APPLIED"
        with self.assertRaises(loop.ActionLoopError):
            loop.verify_plan(mutated)


if __name__ == "__main__":
    unittest.main()
