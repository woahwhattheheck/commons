import importlib.util
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).parent / "integrations/gemini_slack/slack_operation_audit.py"
SPEC = importlib.util.spec_from_file_location("slack_operation_audit_boundary", MODULE_PATH)
audit = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(audit)

SCHEMA_SQL = """
CREATE TABLE tool_calls(
    request_id TEXT NOT NULL,
    call_id TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    arguments_sha256 TEXT NOT NULL,
    state TEXT NOT NULL CHECK(state IN ('started','completed','error')),
    result_json TEXT,
    updated_at REAL NOT NULL,
    PRIMARY KEY(request_id, call_id)
)
"""

def row(request_id, call_id, channel, ts, updated_at):
    result = {"isError": False, "result": {"ok": True, "channel": channel, "ts": ts}, "uncertain": False}
    return (request_id, call_id, "slack_post_message", "0"*64, "completed",
            json.dumps(result, separators=(",", ":")), updated_at)

class SlackOperationAuditBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "calls.sqlite3"
        db = sqlite3.connect(self.path)
        db.execute(SCHEMA_SQL)
        db.executemany("INSERT INTO tool_calls VALUES(?,?,?,?,?,?,?)", [
            row("equipment-return:req-a", "call-a:1788824940.900000:1",
                "C0AAAA", "1788824940.990139", 1.0),
            row("equipment-return:req-b", "call-b:1788824941.300000:1",
                "C0AAAA", "1788824941.412599", 2.0),
            row("equipment-return:req-c", "call-c:1788824941.300001:1",
                "C0BBBB", "1788824941.412599", 3.0),
            row("equipment-return:secret body from message", "call-secret\nmessage",
                "C0AAAA", "1788824999.000000", 4.0),
        ])
        db.commit(); db.close()

    def tearDown(self):
        self.tmp.cleanup()

    def test_identifier_payloads_are_not_emitted_raw(self):
        bad = audit.slack_post_receipts(self.path)[-1]
        self.assertIsNone(bad["journal_request_id"])
        self.assertIsNone(bad["journal_call_id"])
        self.assertIsNone(bad["carrier_request_id"])
        encoded = json.dumps(bad, sort_keys=True)
        self.assertNotIn("secret body", encoded)
        self.assertNotIn("message", encoded)
        self.assertRegex(bad["journal_request_id_sha256"], r"^[0-9a-f]{64}$")
        self.assertRegex(bad["journal_call_id_sha256"], r"^[0-9a-f]{64}$")
        self.assertRegex(bad["carrier_request_id_sha256"], r"^[0-9a-f]{64}$")

    def test_existing_generated_identifiers_remain_visible(self):
        first = audit.slack_post_receipts(self.path)[0]
        self.assertEqual(first["journal_request_id"], "equipment-return:req-a")
        self.assertEqual(first["journal_call_id"], "call-a:1788824940.900000:1")
        self.assertEqual(first["carrier_request_id"], "req-a")

    def test_timestamp_only_cross_channel_collision_is_ambiguous(self):
        result = audit.correlate(self.path, ["1788824941.412599"])
        obs = result["observations"][0]
        self.assertEqual(obs["receipts"], [])
        self.assertEqual(obs["ambiguous_channels"], ["C0AAAA", "C0BBBB"])
        self.assertEqual(result["ambiguous_slack_ts"], ["1788824941.412599"])
        self.assertNotIn("1788824941.412599", result["unmatched_slack_ts"])

    def test_exact_channel_and_timestamp_selects_only_that_message(self):
        result = audit.correlate(
            self.path, ["1788824941.412599"], channel_id="C0BBBB"
        )
        obs = result["observations"][0]
        self.assertEqual(obs["ambiguous_channels"], [])
        self.assertEqual(len(obs["receipts"]), 1)
        self.assertEqual(obs["receipts"][0]["journal_request_id"],
                         "equipment-return:req-c")

    def test_timestamp_only_unique_channel_preserves_compatibility(self):
        result = audit.correlate(self.path, ["1788824940.990139"])
        obs = result["observations"][0]
        self.assertEqual(obs["channel_id"], "C0AAAA")
        self.assertEqual(len(obs["receipts"]), 1)
        self.assertEqual(obs["receipts"][0]["carrier_request_id"], "req-a")

    def test_invalid_channel_fails_closed(self):
        with self.assertRaises(audit.AuditError):
            audit.correlate(self.path, ["1788824940.990139"], channel_id="not-a-channel")

if __name__ == "__main__":
    unittest.main()
