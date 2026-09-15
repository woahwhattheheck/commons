import copy
import json
import os
import random
import subprocess
import sys
import tempfile
import unittest

from host import swarm_channel_dispatch as scd


def snapshot():
    return {
        "schema": scd.SNAPSHOT_SCHEMA,
        "snapshot_id": "census-20260914T2042Z",
        "channels": [
            {
                "channel_id": "C_BUILD",
                "name": "build-demand",
                "specialty_tags": ["integration", "math", "data-science", "feature"],
                "active_claims": 9,
                "messages_15m": 42,
                "capacity": 10,
                "verified_targets": 100,
                "paused": False,
            },
            {
                "channel_id": "C_MATH",
                "name": "math-bounties",
                "specialty_tags": ["math"],
                "active_claims": 0,
                "messages_15m": 1,
                "capacity": 2,
                "verified_targets": 4,
                "paused": False,
            },
            {
                "channel_id": "C_INTEGRATION",
                "name": "integration-bounties",
                "specialty_tags": ["integration"],
                "active_claims": 0,
                "messages_15m": 0,
                "capacity": 2,
                "verified_targets": 3,
                "paused": False,
            },
            {
                "channel_id": "C_DATA",
                "name": "data-science-bounties",
                "specialty_tags": ["data-science"],
                "active_claims": 1,
                "messages_15m": 2,
                "capacity": 3,
                "verified_targets": 5,
                "paused": False,
            },
            {
                "channel_id": "C_QUIET_WRONG",
                "name": "social",
                "specialty_tags": ["marketing"],
                "active_claims": 0,
                "messages_15m": 0,
                "capacity": 50,
                "verified_targets": 50,
                "paused": False,
            },
            {
                "channel_id": "C_ZERO_TARGET",
                "name": "dead-integrations",
                "specialty_tags": ["integration"],
                "active_claims": 0,
                "messages_15m": 0,
                "capacity": 100,
                "verified_targets": 0,
                "paused": False,
            },
        ],
        "work_items": [
            {"work_id": "W_MATH_A", "tags": ["math"], "priority": 90},
            {"work_id": "W_MATH_B", "tags": ["math"], "priority": 80},
            {"work_id": "W_MATH_C", "tags": ["math"], "priority": 70},
            {"work_id": "W_INTEGRATION", "tags": ["integration"], "priority": 95},
            {"work_id": "W_DATA", "tags": ["data-science"], "priority": 85},
            {"work_id": "W_UNKNOWN", "tags": ["legal"], "priority": 100},
        ],
    }


class RoutingTests(unittest.TestCase):
    def test_routes_relevant_work_away_from_saturated_generic_feed(self):
        out = scd.compile_dispatch(snapshot())
        by_work = {row["work_id"]: row for row in out["assignments"]}
        self.assertEqual(by_work["W_INTEGRATION"]["channel_name"], "integration-bounties")
        self.assertEqual(by_work["W_DATA"]["channel_name"], "data-science-bounties")
        self.assertEqual(by_work["W_MATH_A"]["channel_name"], "math-bounties")
        self.assertEqual(by_work["W_MATH_B"]["channel_name"], "math-bounties")
        self.assertEqual(by_work["W_MATH_C"]["channel_name"], "build-demand")

    def test_quiet_but_irrelevant_and_zero_target_channels_never_steal_work(self):
        out = scd.compile_dispatch(snapshot())
        used = {row["channel_name"] for row in out["assignments"]}
        self.assertNotIn("social", used)
        self.assertNotIn("dead-integrations", used)

    def test_unmatched_work_holds_fail_closed(self):
        out = scd.compile_dispatch(snapshot())
        holds = {row["work_id"]: row["reason"] for row in out["holds"]}
        self.assertEqual(holds["W_UNKNOWN"], "NO_ELIGIBLE_RELEVANT_HEADROOM")

    def test_capacity_is_hard_and_summary_matches(self):
        out = scd.compile_dispatch(snapshot())
        summary = {row["channel_name"]: row for row in out["channel_summary"]}
        self.assertEqual(summary["math-bounties"]["assigned"], 2)
        self.assertEqual(summary["math-bounties"]["remaining_headroom"], 0)
        self.assertEqual(summary["build-demand"]["assigned"], 1)
        self.assertEqual(summary["build-demand"]["remaining_headroom"], 0)

    def test_input_order_does_not_change_receipt(self):
        a = snapshot()
        b = copy.deepcopy(a)
        random.Random(991).shuffle(b["channels"])
        random.Random(442).shuffle(b["work_items"])
        for channel in b["channels"]:
            channel["specialty_tags"].reverse()
        for work in b["work_items"]:
            work["tags"].reverse()
        self.assertEqual(scd.compile_dispatch(a), scd.compile_dispatch(b))

    def test_authority_is_explicitly_false(self):
        out = scd.compile_dispatch(snapshot())
        self.assertTrue(out["advisory_only"])
        self.assertTrue(out["authority"])
        self.assertTrue(all(value is False for value in out["authority"].values()))


class ValidationTests(unittest.TestCase):
    def test_duplicate_channel_and_work_ids_rejected(self):
        for mutation in ("channel", "work"):
            data = snapshot()
            if mutation == "channel":
                data["channels"][1]["channel_id"] = data["channels"][0]["channel_id"]
            else:
                data["work_items"][1]["work_id"] = data["work_items"][0]["work_id"]
            with self.subTest(mutation=mutation):
                with self.assertRaises(scd.DispatchInputError):
                    scd.compile_dispatch(data)

    def test_bool_does_not_pass_integer_validation(self):
        data = snapshot()
        data["channels"][0]["capacity"] = True
        with self.assertRaises(scd.DispatchInputError):
            scd.compile_dispatch(data)

    def test_unknown_fields_fail_closed(self):
        data = snapshot()
        data["channels"][0]["trust_me"] = True
        with self.assertRaises(scd.DispatchInputError):
            scd.compile_dispatch(data)

    def test_paused_channel_is_ineligible(self):
        data = snapshot()
        data["channels"][2]["paused"] = True
        out = scd.compile_dispatch(data)
        used_for_integration = [row for row in out["assignments"] if row["work_id"] == "W_INTEGRATION"]
        self.assertEqual(used_for_integration[0]["channel_name"], "build-demand")


class ReceiptTests(unittest.TestCase):
    def test_receipt_verifies_and_tamper_fails(self):
        data = snapshot()
        out = scd.compile_dispatch(data)
        verified = scd.verify_dispatch(data, out)
        self.assertTrue(verified["ok"])
        self.assertEqual(verified["verdict"], "RECEIPT_MATCHES_SNAPSHOT")

        tampered = copy.deepcopy(out)
        tampered["assignments"][0]["channel_name"] = "sales"
        bad = scd.verify_dispatch(data, tampered)
        self.assertFalse(bad["ok"])
        self.assertEqual(bad["verdict"], "RECEIPT_MISMATCH")

    def test_source_change_invalidates_receipt(self):
        data = snapshot()
        out = scd.compile_dispatch(data)
        changed = copy.deepcopy(data)
        changed["channels"][1]["active_claims"] = 1
        self.assertFalse(scd.verify_dispatch(changed, out)["ok"])

    def test_cli_compile_and_verify(self):
        data = snapshot()
        root = os.path.dirname(os.path.dirname(__file__))
        script = os.path.join(root, "host", "swarm_channel_dispatch.py")
        with tempfile.TemporaryDirectory() as tmp:
            snap_path = os.path.join(tmp, "snapshot.json")
            receipt_path = os.path.join(tmp, "receipt.json")
            with open(snap_path, "w", encoding="utf-8") as handle:
                json.dump(data, handle)
            compiled = subprocess.run(
                [sys.executable, script, "compile", snap_path],
                check=True, capture_output=True, text=True,
            )
            receipt = json.loads(compiled.stdout)
            with open(receipt_path, "w", encoding="utf-8") as handle:
                json.dump(receipt, handle)
            verified = subprocess.run(
                [sys.executable, script, "verify", snap_path, receipt_path],
                check=True, capture_output=True, text=True,
            )
            self.assertTrue(json.loads(verified.stdout)["ok"])


if __name__ == "__main__":
    unittest.main()
