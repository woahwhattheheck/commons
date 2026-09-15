import copy
import json
import os
import tempfile
import unittest

from host.swarm_channel_coverage.cli import main as cli_main
from host.swarm_channel_coverage.router import (
    ValidationError,
    compile_report,
    loads_strict,
    verify_report,
)

SHA_A = "a" * 64
SHA_B = "b" * 64


def base_packet():
    return {
        "schema": "swarm-channel-coverage/v1",
        "inventory": {
            "source_ref": "inventory-1",
            "source_sha256": SHA_A,
            "captured_at": "2026-09-15T07:20:00Z",
            "channels": [
                {"channel_id": "central", "label": "central-builds"},
                {"channel_id": "special", "label": "specialist-queue"},
                {"channel_id": "quiet", "label": "quiet-no-demand"},
            ],
        },
        "events": [],
        "policy": {
            "active_window_minutes": 180,
            "stale_after_minutes": 360,
            "max_inventory_age_minutes": 30,
            "saturation_worker_share_bps": 6000,
            "undercovered_max_active_actors": 1,
            "max_inspect": 10,
        },
    }


def event(event_id, channel_id, actor, kind, minute, work_key=None):
    return {
        "event_id": event_id,
        "channel_id": channel_id,
        "actor_ref": actor,
        "kind": kind,
        "observed_at": f"2026-09-15T07:{minute:02d}:00Z",
        "source_ref": f"src-{event_id}",
        "source_sha256": SHA_B,
        "work_key": work_key,
    }


def row(report, channel_id):
    return next(x for x in report["report"]["channels"] if x["channel_id"] == channel_id)


class CoverageRouterTests(unittest.TestCase):
    AS_OF = "2026-09-15T07:30:00Z"

    def test_herding_routes_zero_coverage_specialist_before_saturated_central(self):
        p = base_packet()
        for i in range(6):
            key = f"central-job-{i}"
            p["events"].append(event(f"d-c-{i}", "central", "dispatcher", "DEMAND", 0 + i, key))
            p["events"].append(event(f"t-c-{i}", "central", f"worker-{i}", "TAKE", 10 + i, key))
        p["events"].append(event("d-s-1", "special", "dispatcher", "DEMAND", 8, "special-job"))
        compiled = compile_report(p, self.AS_OF)
        self.assertEqual(row(compiled, "central")["state"], "SATURATED")
        self.assertEqual(row(compiled, "special")["state"], "UNDERCOVERED_DEMAND")
        self.assertEqual(compiled["report"]["inspect_next"][0]["channel_id"], "special")
        self.assertNotIn("central", [x["channel_id"] for x in compiled["report"]["inspect_next"]])

    def test_resolved_demand_is_not_queued(self):
        p = base_packet()
        p["events"] = [
            event("d1", "special", "dispatcher", "DEMAND", 1, "job-1"),
            event("t1", "special", "worker-1", "TAKE", 2, "job-1"),
            event("s1", "central", "shipper", "SHIP", 3, "job-1"),
        ]
        compiled = compile_report(p, self.AS_OF)
        self.assertEqual(row(compiled, "special")["unresolved_demand"], 0)
        self.assertEqual(compiled["report"]["inspect_next"], [])

    def test_quiet_without_demand_never_queues(self):
        compiled = compile_report(base_packet(), self.AS_OF)
        self.assertEqual(row(compiled, "quiet")["state"], "QUIET")
        self.assertEqual(compiled["report"]["inspect_next"], [])

    def test_aggregate_injection_fails_closed(self):
        p = base_packet()
        p["inventory"]["channels"][0]["coverage_score"] = 999
        with self.assertRaises(ValidationError):
            compile_report(p, self.AS_OF)

    def test_duplicate_channel_and_event_ids_fail(self):
        p = base_packet()
        p["inventory"]["channels"].append({"channel_id": "central", "label": "dup"})
        with self.assertRaises(ValidationError):
            compile_report(p, self.AS_OF)
        p = base_packet()
        p["events"] = [
            event("same", "central", "d", "DEMAND", 1, "a"),
            event("same", "special", "d", "DEMAND", 2, "b"),
        ]
        with self.assertRaises(ValidationError):
            compile_report(p, self.AS_OF)

    def test_orphan_channel_fails(self):
        p = base_packet()
        p["events"] = [event("d1", "missing", "dispatcher", "DEMAND", 1, "job")]
        with self.assertRaises(ValidationError):
            compile_report(p, self.AS_OF)

    def test_ship_before_demand_fails(self):
        p = base_packet()
        p["events"] = [
            event("d1", "special", "dispatcher", "DEMAND", 5, "job"),
            event("s1", "central", "shipper", "SHIP", 4, "job"),
        ]
        with self.assertRaises(ValidationError):
            compile_report(p, self.AS_OF)

    def test_saturation_exact_boundary(self):
        p = base_packet()
        p["policy"]["saturation_worker_share_bps"] = 8000
        p["policy"]["undercovered_max_active_actors"] = 0
        for i in range(4):
            key = f"c{i}"
            p["events"].append(event(f"dc{i}", "central", "d", "DEMAND", i, key))
            p["events"].append(event(f"tc{i}", "central", f"w{i}", "TAKE", 10 + i, key))
        p["events"].extend([
            event("ds", "special", "d", "DEMAND", 5, "s"),
            event("ts", "special", "ws", "TAKE", 15, "s"),
        ])
        compiled = compile_report(p, self.AS_OF)
        self.assertEqual(row(compiled, "central")["worker_share_bps"], 8000)
        self.assertEqual(row(compiled, "central")["state"], "SATURATED")

    def test_input_order_invariance(self):
        p = base_packet()
        p["events"] = [
            event("d1", "special", "d", "DEMAND", 1, "job1"),
            event("d2", "central", "d", "DEMAND", 2, "job2"),
            event("t2", "central", "w", "TAKE", 3, "job2"),
        ]
        a = compile_report(p, self.AS_OF)
        q = copy.deepcopy(p)
        q["inventory"]["channels"].reverse()
        q["events"].reverse()
        b = compile_report(q, self.AS_OF)
        self.assertEqual(a, b)

    def test_future_event_fails(self):
        p = base_packet()
        bad = event("d1", "special", "d", "DEMAND", 1, "job")
        bad["observed_at"] = "2026-09-15T07:31:00Z"
        p["events"] = [bad]
        with self.assertRaises(ValidationError):
            compile_report(p, self.AS_OF)

    def test_stale_inventory_holds_all_and_clears_queue(self):
        p = base_packet()
        p["inventory"]["captured_at"] = "2026-09-15T06:00:00Z"
        p["events"] = [event("d1", "special", "d", "DEMAND", 1, "job")]
        compiled = compile_report(p, self.AS_OF)
        self.assertEqual(compiled["report"]["status"], "HOLD")
        self.assertEqual(compiled["report"]["hold_reasons"], ["STALE_INVENTORY"])
        self.assertEqual(compiled["report"]["inspect_next"], [])
        self.assertTrue(all(x["state"] == "HOLD" for x in compiled["report"]["channels"]))

    def test_bool_int_alias_and_bad_hash_time_fail(self):
        p = base_packet()
        p["policy"]["max_inspect"] = True
        with self.assertRaises(ValidationError):
            compile_report(p, self.AS_OF)
        p = base_packet()
        p["inventory"]["source_sha256"] = "A" * 64
        with self.assertRaises(ValidationError):
            compile_report(p, self.AS_OF)
        p = base_packet()
        p["inventory"]["captured_at"] = "2026-09-15T07:20:00+00:00"
        with self.assertRaises(ValidationError):
            compile_report(p, self.AS_OF)

    def test_strict_json_duplicate_key_and_float_fail(self):
        with self.assertRaises(ValidationError):
            loads_strict('{"a":1,"a":2}')
        with self.assertRaises(ValidationError):
            loads_strict('{"a":1.0}')

    def test_tamper_and_time_drift_fail_verification(self):
        p = base_packet()
        p["events"] = [event("d1", "special", "d", "DEMAND", 1, "job")]
        compiled = compile_report(p, self.AS_OF)
        self.assertTrue(verify_report(p, compiled, self.AS_OF))
        tampered = copy.deepcopy(compiled)
        tampered["report"]["inspect_next"][0]["rank"] = 7
        self.assertFalse(verify_report(p, tampered, self.AS_OF))
        self.assertFalse(verify_report(p, compiled, "2026-09-15T07:31:00Z"))

    def test_authority_is_always_false_except_inspection_guidance(self):
        compiled = compile_report(base_packet(), self.AS_OF)
        auth = compiled["report"]["authority"]
        self.assertTrue(auth["inspection_guidance_only"])
        self.assertFalse(auth["take_authorized"])
        self.assertFalse(auth["slack_mutation_authorized"])
        self.assertFalse(auth["external_send_authorized"])

    def test_cli_compile_is_create_exclusive_and_verify_recompiles(self):
        p = base_packet()
        p["events"] = [event("d1", "special", "d", "DEMAND", 1, "job")]
        with tempfile.TemporaryDirectory() as td:
            source = os.path.join(td, "packet.json")
            output = os.path.join(td, "report.json")
            with open(source, "w", encoding="utf-8") as fh:
                json.dump(p, fh)
            self.assertEqual(cli_main(["compile", "--input", source, "--as-of", self.AS_OF, "--output", output]), 0)
            self.assertEqual(cli_main(["verify", "--input", source, "--report", output, "--as-of", self.AS_OF]), 0)
            self.assertEqual(cli_main(["compile", "--input", source, "--as-of", self.AS_OF, "--output", output]), 2)


if __name__ == "__main__":
    unittest.main()
