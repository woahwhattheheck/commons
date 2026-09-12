import io
import json
import os
import subprocess
import sys
import tempfile
import unittest

from claim_liveness import (
    AuditError,
    DEFAULT_CANONICAL_ROOT,
    audit_events,
    load_jsonl,
)

NOW = 2_000.0


def e(ts, lane="L", session="A", event="CLAIM", **kw):
    return {"ts": ts, "lane": lane, "session": session, "event": event, **kw}


class ClaimLivenessTests(unittest.TestCase):
    def audit(self, events, **kw):
        return audit_events(events, as_of=NOW, ttl_seconds=100, **kw)

    def row(self, report, lane="L"):
        return next(r for r in report["lanes"] if r["lane"] == lane)

    def test_fresh_claim_active(self):
        r = self.audit([e(1950)])
        self.assertEqual("ACTIVE", self.row(r)["status"])

    def test_stale_claim_is_recovery_candidate_not_authority(self):
        r = self.audit([e(1800)])
        row = self.row(r)
        self.assertEqual("STALE_CLAIM", row["status"])
        self.assertEqual(["A"], row["recovery_candidates"])
        self.assertFalse(r["policy"]["stale_is_overwrite_authority"])

    def test_fresh_owner_blocks_stale_recovery(self):
        r = self.audit([e(1800, session="A"), e(1950, session="B")])
        row = self.row(r)
        self.assertEqual("ACTIVE_WITH_STALE_OWNER", row["status"])
        self.assertEqual([], row["recovery_candidates"])

    def test_two_fresh_owners_collision(self):
        r = self.audit([e(1950, session="A"), e(1960, session="B")])
        self.assertEqual("COLLISION", self.row(r)["status"])
        self.assertEqual(1, r["summary"]["collisions"])

    def test_heartbeat_extends_claim(self):
        r = self.audit([e(1800), e(1990, event="HEARTBEAT")])
        self.assertEqual("ACTIVE", self.row(r)["status"])

    def test_heartbeat_without_claim_is_anomaly(self):
        r = self.audit([e(1990, event="HEARTBEAT")])
        self.assertIn("heartbeat_without_active_claim", {a["kind"] for a in r["anomalies"]})

    def test_complete_closes_claim(self):
        r = self.audit([e(1800), e(1900, event="COMPLETE", artifact="pr#1")])
        self.assertEqual("CLOSED", self.row(r)["status"])
        self.assertEqual({"A": "COMPLETE"}, self.row(r)["terminal_owners"])

    def test_blocked_is_terminal_not_stale(self):
        r = self.audit([e(1700), e(1750, event="BLOCKED")])
        self.assertEqual("CLOSED", self.row(r)["status"])

    def test_required_artifact_is_enforced(self):
        r = self.audit([e(1900, requires_artifact=True), e(1950, event="COMPLETE")])
        self.assertIn("completion_without_required_artifact", {a["kind"] for a in r["anomalies"]})

    def test_terminal_without_claim_is_anomaly(self):
        r = self.audit([e(1950, event="RELEASED")])
        self.assertIn("terminal_without_claim", {a["kind"] for a in r["anomalies"]})

    def test_noncanonical_root_is_anomaly(self):
        r = self.audit([e(1950, canonical_root="main:other/v4")])
        self.assertIn("noncanonical_root", {a["kind"] for a in r["anomalies"]})

    def test_repo_write_requires_root_binding(self):
        r = self.audit([e(1950, writes_repo=True)])
        self.assertIn("repo_write_without_root", {a["kind"] for a in r["anomalies"]})

    def test_duplicate_event_id_is_anomaly(self):
        r = self.audit([e(1900, event_id="x"), e(1950, event="HEARTBEAT", event_id="x")])
        self.assertIn("duplicate_event_id", {a["kind"] for a in r["anomalies"]})

    def test_timezone_aware_iso_timestamp(self):
        r = audit_events(
            [e("1970-01-01T00:30:00+00:00")],
            as_of="1970-01-01T00:31:00Z",
            ttl_seconds=100,
        )
        self.assertEqual("ACTIVE", self.row(r)["status"])

    def test_boolean_timestamp_rejected(self):
        with self.assertRaises(AuditError):
            self.audit([e(True)])

    def test_future_event_is_anomaly(self):
        r = self.audit([e(2100)])
        self.assertIn("future_event", {a["kind"] for a in r["anomalies"]})

    def test_jsonl_comments_and_blank_lines(self):
        rows = load_jsonl(io.StringIO('\n# comment\n{"ts":1,"lane":"L","session":"A","event":"CLAIM"}\n'))
        self.assertEqual(1, len(rows))

    def test_output_is_deterministic_under_lane_input_permutation(self):
        a = self.audit([e(1950, lane="Z"), e(1940, lane="A")])
        b = self.audit([e(1940, lane="A"), e(1950, lane="Z")])
        self.assertEqual(
            json.dumps(a, sort_keys=True, separators=(",", ":")),
            json.dumps(b, sort_keys=True, separators=(",", ":")),
        )

    def test_cli_emits_canonical_json(self):
        here = os.path.dirname(__file__)
        payload = json.dumps(e(1950, canonical_root=DEFAULT_CANONICAL_ROOT)) + "\n"
        proc = subprocess.run(
            [sys.executable, os.path.join(here, "claim_liveness.py"),
             "--as-of", str(NOW), "--ttl-seconds", "100"],
            input=payload, text=True, capture_output=True, check=False,
        )
        self.assertEqual(0, proc.returncode, proc.stderr)
        parsed = json.loads(proc.stdout)
        self.assertEqual("titan-v4-claim-liveness/v1", parsed["schema"])
        self.assertEqual("ACTIVE", parsed["lanes"][0]["status"])


if __name__ == "__main__":
    unittest.main()
