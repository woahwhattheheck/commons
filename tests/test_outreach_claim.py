from __future__ import annotations
import datetime as dt
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("outreach_claim", ROOT / "host/outreach_claim.py")
assert spec and spec.loader
lease = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lease)
T0 = dt.datetime(2026, 9, 17, 23, 30, tzinfo=dt.timezone.utc)

class OutreachClaimTests(unittest.TestCase):
    def test_key_is_stable_casefolded_and_public_safe(self):
        a = lease.route_digest("MAILTO:Prospect@Example.COM ")
        b = lease.route_digest("prospect@example.com")
        self.assertEqual(a, b)
        result = lease.new_record("prospect@example.com", "Z-Sol", purpose="paid pilot", now=T0)
        blob = json.dumps(result)
        self.assertNotIn("prospect@", blob)
        self.assertNotIn("example.com", blob)
        self.assertNotIn("paid pilot", blob)
        self.assertRegex(result["target_digest"], r"^[0-9a-f]{64}$")

    def test_url_normalization(self):
        self.assertEqual(lease.route_digest("HTTPS://Example.COM/path/"), lease.route_digest("https://example.com/path"))

    def test_consume_is_owner_only_and_terminal(self):
        record = lease.new_record("a@example.com", "Z-Sol", now=T0)
        with self.assertRaises(lease.LeaseError):
            lease.consume(record, "Other", now=T0 + dt.timedelta(minutes=1))
        consumed = lease.consume(record, "Z-Sol", now=T0 + dt.timedelta(minutes=1))
        self.assertEqual(consumed["status"], lease.CONSUMED)
        with self.assertRaises(lease.LeaseError):
            lease.reclaim(consumed, "Z-Sol", now=T0 + dt.timedelta(hours=1))

    def test_expiry_and_release_reclaim_increment_generation(self):
        record = lease.new_record("a@example.com", "Z-Sol", ttl_minutes=1, now=T0)
        self.assertEqual(lease.effective_state(record, at=T0 + dt.timedelta(seconds=59)), lease.ACTIVE)
        self.assertEqual(lease.effective_state(record, at=T0 + dt.timedelta(minutes=1)), "EXPIRED")
        renewed = lease.reclaim(record, "Z-Rook", now=T0 + dt.timedelta(minutes=1))
        self.assertEqual(renewed["generation"], 2)
        self.assertEqual(renewed["claimant"], "Z-Rook")
        released = lease.release(renewed, "Z-Rook", now=T0 + dt.timedelta(minutes=2))
        self.assertEqual(released["status"], lease.RELEASED)
        third = lease.reclaim(released, "Z-Ferro", now=T0 + dt.timedelta(minutes=3))
        self.assertEqual(third["generation"], 3)

    def test_consumed_reopen_requires_evidence_and_hashes_it(self):
        record = lease.new_record("a@example.com", "Z-Sol", now=T0)
        consumed = lease.consume(record, "Z-Sol", now=T0 + dt.timedelta(minutes=1))
        with self.assertRaises(lease.LeaseError):
            lease.reopen(consumed, "Z-Sol", evidence="", now=T0 + dt.timedelta(minutes=2))
        reopened = lease.reopen(consumed, "Z-Sol", evidence="gmail:message-123", purpose="reply follow-up", now=T0 + dt.timedelta(minutes=2))
        self.assertEqual(reopened["status"], lease.ACTIVE)
        self.assertEqual(reopened["generation"], 2)
        blob = json.dumps(reopened)
        self.assertNotIn("gmail:message-123", blob)
        self.assertNotIn("reply follow-up", blob)
        self.assertIsNotNone(reopened["evidence_digest"])

    def test_cli_new_consume(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / "lease.json"
            proc = subprocess.run([sys.executable, str(ROOT / "host/outreach_claim.py"), "new", "prospect@example.com", "--claimant", "Z-Sol", "--at", "2026-09-17T23:30:00Z"], text=True, capture_output=True, cwd=ROOT)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            p.write_text(proc.stdout, encoding="utf-8")
            proc = subprocess.run([sys.executable, str(ROOT / "host/outreach_claim.py"), "consume", str(p), "--claimant", "Z-Sol", "--at", "2026-09-17T23:31:00Z"], text=True, capture_output=True, cwd=ROOT)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(json.loads(proc.stdout)["status"], lease.CONSUMED)

if __name__ == "__main__":
    raise SystemExit(unittest.main())
