import unittest

from host import swarm_channel_dispatch as scd


def channel(*, channel_id, name, active_claims=0, messages_15m=0, capacity=10, verified_targets=1):
    return {
        "channel_id": channel_id,
        "name": name,
        "specialty_tags": ["math"],
        "active_claims": active_claims,
        "messages_15m": messages_15m,
        "capacity": capacity,
        "verified_targets": verified_targets,
        "paused": False,
    }


def work(work_id, priority):
    return {"work_id": work_id, "tags": ["math"], "priority": priority}


def snapshot(snapshot_id, channels, work_items):
    return {
        "schema": scd.SNAPSHOT_SCHEMA,
        "snapshot_id": snapshot_id,
        "channels": channels,
        "work_items": work_items,
    }


class VerifiedTargetCardinalityTests(unittest.TestCase):
    def test_one_verified_target_cannot_authorize_multiple_assignments(self):
        data = snapshot(
            "one-target-many-work",
            [channel(channel_id="C_ONE", name="one-target")],
            [work("W_A", 90), work("W_B", 80)],
        )
        out = scd.compile_dispatch(data)
        self.assertEqual([row["work_id"] for row in out["assignments"]], ["W_A"])
        self.assertEqual([row["work_id"] for row in out["holds"]], ["W_B"])
        summary = out["channel_summary"][0]
        self.assertEqual(summary["eligible_target_count"], 1)
        self.assertEqual(summary["assigned"], 1)
        self.assertEqual(summary["remaining_headroom"], 0)

    def test_existing_claims_consume_verified_target_pool(self):
        data = snapshot(
            "claimed-target",
            [channel(channel_id="C_ONE", name="one-target", active_claims=1)],
            [work("W_A", 90)],
        )
        out = scd.compile_dispatch(data)
        self.assertEqual(out["assignments"], [])
        self.assertEqual([row["work_id"] for row in out["holds"]], ["W_A"])
        self.assertEqual(out["channel_summary"][0]["remaining_headroom"], 0)

    def test_target_limited_channel_spills_to_another_verified_channel(self):
        data = snapshot(
            "target-spill",
            [
                channel(channel_id="C_A", name="alpha-math"),
                channel(channel_id="C_B", name="beta-math", messages_15m=1),
            ],
            [work("W_A", 90), work("W_B", 80)],
        )
        out = scd.compile_dispatch(data)
        self.assertEqual(len(out["assignments"]), 2)
        self.assertEqual({row["channel_name"] for row in out["assignments"]}, {"alpha-math", "beta-math"})
        self.assertEqual(out["holds"], [])


if __name__ == "__main__":
    unittest.main()
