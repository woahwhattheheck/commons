import json
from pathlib import Path
import tempfile
import unittest

import custody_collision_preflight as c

A = "a" * 40
B = "b" * 40
C = "c" * 40


def base(**overrides):
    snap = {
        "operation_id": "SWARM-CUSTODY-MULTIKEY-COLLISION-FENCE-20260913",
        "holder": "Z-Vector",
        "candidate": {
            "upstream_pr": {"repo": "Tarsnap/spiped", "number": 439},
            "paths": ["lib/dnsthread/dnsthread.c"],
            "donor_blobs": {"lib/dnsthread/dnsthread.c": A},
        },
        "complete": {"slack": True, "owner_prs": True, "owner_default": True},
        "slack": [],
        "owner_prs": [],
        "owner_default": {"blobs": {"lib/dnsthread/dnsthread.c": B}},
    }
    snap.update(overrides)
    return snap


class Classification(unittest.TestCase):
    def test_complete_no_collision_is_safe(self):
        got = c.classify(base())
        self.assertEqual(got["verdict"], "SAFE_TO_CLAIM")
        self.assertFalse(got["safety"]["takes_custody"])

    def test_owner_default_exact_donor_is_already_integrated(self):
        snap = base(owner_default={"blobs": {"lib/dnsthread/dnsthread.c": A}})
        self.assertEqual(c.classify(snap)["verdict"], "ALREADY_INTEGRATED")

    def test_exact_operation_take_by_other_holder_collides(self):
        snap = base(slack=[{
            "kind": "source_take",
            "operation_id": "SWARM-CUSTODY-MULTIKEY-COLLISION-FENCE-20260914",
            "holder": "Ariadne-Z",
        }])
        got = c.classify(snap)
        self.assertEqual(got["verdict"], "COLLISION")
        self.assertEqual(got["evidence"][-1]["kind"], "slack_exact_operation_custody")

    def test_exact_upstream_pr_take_by_other_holder_collides(self):
        snap = base(slack=[{
            "kind": "source_claim",
            "operation_id": "OTHER-OP-20260913",
            "holder": "Ariadne-Z",
            "upstream_pr": {"repo": "tarsnap/spiped", "number": 439},
        }])
        self.assertEqual(c.classify(snap)["verdict"], "COLLISION")

    def test_same_holder_take_is_not_collision(self):
        snap = base(slack=[{
            "kind": "source_take",
            "operation_id": "SWARM-CUSTODY-MULTIKEY-COLLISION-FENCE-20260913",
            "holder": "Z-Vector",
        }])
        self.assertEqual(c.classify(snap)["verdict"], "SAFE_TO_CLAIM")

    def test_build_order_is_source_neutral(self):
        snap = base(slack=[{
            "kind": "build_order",
            "operation_id": "SWARM-CUSTODY-MULTIKEY-COLLISION-FENCE-20260913",
            "holder": "Cobb-Z-Sable",
        }])
        got = c.classify(snap)
        self.assertEqual(got["verdict"], "SAFE_TO_CLAIM")
        self.assertEqual(got["evidence"][0]["kind"], "source_neutral_message")

    def test_owner_carrier_exact_operation_collides(self):
        snap = base(owner_prs=[{
            "number": 23,
            "state": "open",
            "holder": "Ariadne-Z",
            "operation_id": "SWARM-CUSTODY-MULTIKEY-COLLISION-FENCE-20260913",
            "paths": ["other.c"],
        }])
        self.assertEqual(c.classify(snap)["verdict"], "COLLISION")

    def test_owner_carrier_exact_upstream_pr_collides(self):
        snap = base(owner_prs=[{
            "number": 23,
            "state": "open",
            "holder": "Ariadne-Z",
            "upstream_pr": {"repo": "Tarsnap/spiped", "number": 439},
            "paths": ["other.c"],
        }])
        self.assertEqual(c.classify(snap)["verdict"], "COLLISION")

    def test_owner_carrier_exact_donor_blob_collides(self):
        snap = base(owner_prs=[{
            "number": 23,
            "state": "draft",
            "blobs": {"lib/dnsthread/dnsthread.c": A},
            "paths": ["lib/dnsthread/dnsthread.c"],
        }])
        got = c.classify(snap)
        self.assertEqual(got["verdict"], "COLLISION")
        self.assertEqual(got["evidence"][-1]["kind"], "owner_carrier_exact_donor_blob")

    def test_path_overlap_is_review_not_collision(self):
        snap = base(owner_prs=[{
            "number": 24,
            "state": "open",
            "holder": "Peer",
            "paths": ["lib/dnsthread/dnsthread.c"],
            "blobs": {"lib/dnsthread/dnsthread.c": C},
        }])
        got = c.classify(snap)
        self.assertEqual(got["verdict"], "OVERLAP_REVIEW")
        self.assertEqual(got["evidence"][-1]["kind"], "owner_carrier_path_overlap")

    def test_closed_carrier_does_not_block(self):
        snap = base(owner_prs=[{
            "number": 22,
            "state": "closed",
            "upstream_pr": {"repo": "Tarsnap/spiped", "number": 439},
            "paths": ["lib/dnsthread/dnsthread.c"],
        }])
        self.assertEqual(c.classify(snap)["verdict"], "SAFE_TO_CLAIM")

    def test_incomplete_slack_fails_closed(self):
        snap = base()
        snap["complete"]["slack"] = False
        got = c.classify(snap)
        self.assertEqual(got["verdict"], "UNKNOWN_HOLD")
        self.assertIn("slack", got["evidence"][-1]["inventories"])

    def test_incomplete_owner_prs_fails_closed(self):
        snap = base()
        snap["complete"]["owner_prs"] = False
        self.assertEqual(c.classify(snap)["verdict"], "UNKNOWN_HOLD")

    def test_incomplete_owner_default_fails_closed(self):
        snap = base()
        snap["complete"]["owner_default"] = False
        self.assertEqual(c.classify(snap)["verdict"], "UNKNOWN_HOLD")

    def test_positive_collision_beats_incomplete_inventory(self):
        snap = base(slack=[{
            "kind": "source_take",
            "operation_id": "SWARM-CUSTODY-MULTIKEY-COLLISION-FENCE-20260913",
            "holder": "Peer",
        }])
        snap["complete"] = {"slack": False, "owner_prs": False, "owner_default": False}
        self.assertEqual(c.classify(snap)["verdict"], "COLLISION")

    def test_already_integrated_beats_incomplete_inventory(self):
        snap = base(owner_default={"blobs": {"lib/dnsthread/dnsthread.c": A}})
        snap["complete"] = {"slack": False, "owner_prs": False, "owner_default": False}
        self.assertEqual(c.classify(snap)["verdict"], "ALREADY_INTEGRATED")

    def test_complete_owner_default_missing_candidate_path_is_unknown(self):
        snap = base(owner_default={"blobs": {}})
        got = c.classify(snap)
        self.assertEqual(got["verdict"], "UNKNOWN_HOLD")
        self.assertEqual(got["evidence"][-1]["kind"], "missing_owner_blob")

    def test_invalid_snapshot_is_unknown(self):
        self.assertEqual(c.classify([])["verdict"], "UNKNOWN_HOLD")

    def test_missing_holder_is_unknown(self):
        snap = base(holder="")
        self.assertEqual(c.classify(snap)["verdict"], "UNKNOWN_HOLD")

    def test_invalid_paths_do_not_create_overlap(self):
        snap = base(owner_prs=[{"number": 9, "state": "open", "paths": ["../escape"]}])
        self.assertEqual(c.classify(snap)["verdict"], "SAFE_TO_CLAIM")

    def test_operation_date_suffix_canonicalizes(self):
        a = c._canonical_operation("FOO-BAR-BAZ-20260913")
        b = c._canonical_operation("FOO-BAR-BAZ-20260914")
        self.assertEqual(a, b)


class Publication(unittest.TestCase):
    def test_output_is_create_exclusive(self):
        report = c.classify(base())
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "report.json"
            c._write_report(report, path)
            self.assertEqual(json.loads(path.read_text())["schema"], c.SCHEMA)
            with self.assertRaises(FileExistsError):
                c._write_report(report, path)


if __name__ == "__main__":
    unittest.main()
