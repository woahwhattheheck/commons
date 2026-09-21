import copy
import math
import unittest

from integrations.command_center import jev_action_loop as action_loop
from integrations.command_center import jev_connector_projection as projection
from integrations.command_center import jev_event_ledger as ledger
from integrations.command_center import jev_routing_pipeline as pipeline

OBS = "2026-09-20T21:30:00Z"
EVENT = "2026-09-20T21:25:00Z"
START = "2026-09-20T21:00:00Z"


def packet(*, complete=True, has_more=False, status="OK"):
    return {
        "schema": projection.SCHEMA,
        "snapshot_id": "radar-20260920T2130Z",
        "max_source_age_seconds": 600,
        "sources": [{
            "source_id": "slack-coordination",
            "connector": "slack-history",
            "provider": "slack",
            "scope": ["C0BU51F1PL3"],
            "cursor": "cursor-1",
            "high_water_mark": "1789941055.269939",
            "observed_at": OBS,
            "last_successful_read": OBS,
            "status": status,
            "cooldown_until": None,
            "coverage": {
                "window_start": START,
                "window_end": OBS,
                "complete": complete,
                "has_more": has_more,
                "pages_read": 1,
                "items_read": 1,
            },
            "source_url": "https://tokenjunkielabs.slack.com/archives/C0BU51F1PL3",
            "records": [{
                "provider_event_id": "1789941055.269939",
                "provider_event_time": EVENT,
                "observed_at": OBS,
                "resource_scope": "C0BU51F1PL3",
                "event_type": "MESSAGE",
                "actor_id": "U0BR9670G2H",
                "work_id": "commons#16537",
                "operation_id": None,
                "source_url": "https://tokenjunkielabs.slack.com/archives/C0BU51F1PL3/p1789941055269939",
            }],
        }],
    }


def ref():
    return {
        "source_id": "slack-coordination",
        "provider_event_id": "1789941055.269939",
        "resource_scope": "C0BU51F1PL3",
        "event_type": "MESSAGE",
    }


def jev(*, lane="coordination", confidence=0.91, error=None):
    return {
        "surface": "triage",
        "model": "jev-1.13.0",
        "answers": {
            "lane": {"choice": lane, "confidence": confidence},
            "needs_response": {"noul": 0.97, "confidence": 0.93},
        },
        "error": error,
        "decided_at": "2026-09-20T21:30:01Z",
    }


def routes():
    return {
        "coordination": {
            "action": "ROUTE_SLACK",
            "provider": "slack",
            "destination_id": "C0BU51F1PL3",
            "thread_id": None,
        },
        "commons_control": {
            "action": "ROUTE_SLACK",
            "provider": "slack",
            "destination_id": "C0BRGMDQB6G",
            "thread_id": None,
        },
    }


class RoutingPipelineTests(unittest.TestCase):
    def compile(self, connector_packet=None, **kwargs):
        args = {
            "selected_record": ref(),
            "jev_result": jev(),
            "route_map": routes(),
            "provider_status": "OPEN",
            "evaluated_at": OBS,
        }
        args.update(kwargs)
        return pipeline.compile_bundle(connector_packet or packet(), **args)

    def receipt(self, bundle, *, outcome="CONFIRMED"):
        operation_id = bundle["plan"]["operation_id"]
        return pipeline.make_receipt(
            bundle,
            provider_resource_id="1789942000.000001" if outcome == "CONFIRMED" else None,
            provider_observed_operation_id=operation_id if outcome == "CONFIRMED" else None,
            source_url="https://example.invalid/readback",
            outcome=outcome,
            attempted_at="2026-09-20T21:30:02Z",
            observed_at="2026-09-20T21:30:03Z",
        )

    def test_happy_path_composes_all_landed_slices(self):
        out = self.compile()
        self.assertTrue(pipeline.verify_bundle(out))
        self.assertEqual(out["disposition"], "ACTION_READY")
        self.assertEqual(out["jev"]["selected_lane"], "coordination")
        self.assertEqual(out["jev"]["confidence_ppm"], 910000)
        self.assertEqual(out["plan"]["selected_action"], "ROUTE_SLACK")
        self.assertEqual(out["plan"]["target"]["destination_id"], "C0BU51F1PL3")
        self.assertEqual(out["observation"]["resource_id"], "commons#16537")
        self.assertTrue(ledger.verify_report(out["ledger_report"]))
        action_loop.verify_plan(out["plan"])

    def test_partial_source_fails_closed(self):
        out = self.compile(packet(complete=False, has_more=True, status="PARTIAL"))
        self.assertEqual(out["selected_source_freshness"], "PARTIAL")
        self.assertEqual(out["ledger_report"]["windows"][0]["coverage"]["state"], "LOWER_BOUND")
        self.assertEqual(out["disposition"], "HOLD_SOURCE_COVERAGE")
        self.assertIsNone(out["plan"])
        self.assertTrue(pipeline.verify_bundle(out))

    def test_error_source_fails_closed(self):
        out = self.compile(packet(status="ERROR"))
        self.assertEqual(out["disposition"], "HOLD_SOURCE_COVERAGE")
        self.assertIsNone(out["plan"])

    def test_low_confidence_is_not_executable(self):
        out = self.compile(jev_result=jev(confidence=0.699999))
        self.assertEqual(out["disposition"], "HOLD_LOW_CONFIDENCE")
        with self.assertRaises(pipeline.RoutingPipelineError):
            self.receipt(out)

    def test_jev_error_retains_ledger_but_builds_no_plan(self):
        out = self.compile(jev_result=jev(error="NO_KEY"))
        self.assertEqual(out["disposition"], "HOLD_JEV_ERROR")
        self.assertIsNone(out["plan"])
        self.assertTrue(ledger.verify_report(out["ledger_report"]))

    def test_unknown_lane_holds_without_transport_plan(self):
        out = self.compile(jev_result=jev(lane="build_floor"))
        self.assertEqual(out["disposition"], "HOLD_NO_ROUTE")
        self.assertIsNone(out["plan"])

    def test_selected_record_must_match_exact_native_identity(self):
        bad = ref()
        bad["provider_event_id"] = "other"
        with self.assertRaises(pipeline.RoutingPipelineError):
            self.compile(selected_record=bad)

    def test_projection_privacy_contract_is_inherited(self):
        p = packet()
        p["sources"][0]["records"][0]["text"] = "raw private message"
        with self.assertRaises(projection.ProjectionError):
            self.compile(p)

    def test_route_slack_cannot_target_non_slack_provider(self):
        bad = routes()
        bad["coordination"]["provider"] = "github"
        with self.assertRaises(pipeline.RoutingPipelineError):
            self.compile(route_map=bad)

    def test_invalid_provider_status_is_rejected_even_on_hold(self):
        with self.assertRaises(action_loop.ActionLoopError):
            self.compile(packet(complete=False, has_more=True, status="PARTIAL"), provider_status="NOT_A_STATE")

    def test_nonfinite_confidence_rejected(self):
        with self.assertRaises(pipeline.RoutingPipelineError):
            self.compile(jev_result=jev(confidence=math.nan))

    def test_projection_digest_tamper_fails_even_with_outer_rehash(self):
        out = self.compile()
        bad = copy.deepcopy(out)
        bad["connector_projection_sha256"] = "0" * 64
        body = dict(bad)
        body.pop("bundle_sha256")
        bad["bundle_sha256"] = pipeline._digest(body)
        self.assertFalse(pipeline.verify_bundle(bad))

    def test_nested_ledger_tamper_fails_even_with_outer_rehash(self):
        out = self.compile()
        bad = copy.deepcopy(out)
        bad["ledger_report"]["snapshot_id"] = "tampered"
        body = dict(bad)
        body.pop("bundle_sha256")
        bad["bundle_sha256"] = pipeline._digest(body)
        self.assertFalse(pipeline.verify_bundle(bad))

    def test_confirmed_provider_readback_receipt(self):
        out = self.compile()
        receipt = self.receipt(out)
        self.assertTrue(action_loop.verify_receipt(receipt)["confirmed"])

    def test_uncertain_receipt_holds_same_operation_generation(self):
        first = self.compile()
        receipt = self.receipt(first, outcome="DELIVERY_UNCERTAIN")
        second = self.compile(prior_receipts=[receipt])
        self.assertEqual(second["plan"]["operation_id"], first["plan"]["operation_id"])
        self.assertEqual(second["disposition"], "HOLD_DELIVERY_UNCERTAIN")

    def test_confirmed_receipt_makes_generation_already_applied(self):
        first = self.compile()
        second = self.compile(prior_receipts=[self.receipt(first)])
        self.assertEqual(second["disposition"], "ALREADY_APPLIED")

    def test_route_target_change_changes_operation_not_event_identity(self):
        first = self.compile()
        changed = routes()
        changed["coordination"]["destination_id"] = "C0BRGMDQB6G"
        second = self.compile(route_map=changed)
        self.assertEqual(first["selected_event_id"], second["selected_event_id"])
        self.assertNotEqual(first["plan"]["operation_id"], second["plan"]["operation_id"])

    def test_authority_ceiling_is_hard_false(self):
        out = self.compile()
        self.assertEqual(out["authority"], pipeline.AUTHORITY)
        self.assertFalse(any(out["authority"].values()))


if __name__ == "__main__":
    unittest.main()
