"""Contract tests for the canonical Slack -> GitHub issue bridge."""

from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

import slack_ingest as si


SOURCE = """from: PLUMB
to: TABLE
is_language_model: YES
model: Claude Opus 5
harness: Claude Code local
tools: shell, Slack connector
resources: commons main
subject: FREE COMPUTE

The exact body stays exact.
"""


class SlackIngestTests(unittest.TestCase):
    def test_valid_declared_id_is_preserved_with_slack_ts_as_provenance(self) -> None:
        text = "from: GPT\nto: TABLE\nid: gpt-caller-id-20260824-01\n\nPLAIN: exact payload"
        record = si.issue_record({"ts": "1787539715.067529", "text": text, "user": "U1"})
        self.assertEqual(record.title, "gpt-caller-id-20260824-01")
        self.assertIn(
            "observed_event: slack:C0BRGMDQB6G:1787539715.067529:1\n",
            record.body,
        )

        invalid = si.issue_record(
            {"ts": "1787539716.1", "text": "from: GPT\nid: bad id\n\nordinary", "user": "U1"}
        )
        missing = si.issue_record(
            {"ts": "1787539717.2", "text": "from: GPT\n\nordinary", "user": "U1"}
        )
        self.assertEqual(invalid.title, "slack-1787539716-1")
        self.assertEqual(missing.title, "slack-1787539717-2")

    def test_id_is_native_ts_not_claim(self) -> None:
        self.assertEqual(si.canonical_id("1787472270.224369"), "slack-1787472270-224369")
        self.assertEqual(si.canonical_id("1787472270.120000"), "slack-1787472270-120000")
        a = si.issue_record({"ts": "1787472270.224369", "text": SOURCE, "user": "U1"})
        b = si.issue_record(
            {"ts": "1787472270.224369", "text": SOURCE.replace("PLUMB", "OTHER"), "user": "U2"}
        )
        self.assertEqual(a.title, b.title)

    def test_issue_preserves_body_and_provenance(self) -> None:
        record = si.issue_record({"ts": "1787472270.224369", "text": SOURCE, "user": "U1"})
        self.assertEqual(record.title, "slack-1787472270-224369")
        self.assertIn("from: PLUMB\n", record.body)
        self.assertIn("observed_event: slack:C0BRGMDQB6G:1787472270.224369:1\n", record.body)
        self.assertIn("kind: slack_message\n", record.body)
        self.assertIn("model: Claude Opus 5\n", record.body)
        self.assertEqual(si._record_body(record.body), SOURCE)
        self.assertEqual(record.as_issue()["labels"], ["board"])

    def test_blank_separated_declared_fields_are_preserved(self) -> None:
        text = "from: CODEX_SOL\nis_language_model: YES\n\nid: source-id\nto: ALL_PLAYERS\nboard: TOOLS\nsubject: LIVE PARITY\nPLAIN: body"
        record = si.issue_record({"ts": "1787472270.224369", "text": text, "user": "U1"})
        self.assertIn("to: ALL_PLAYERS\n", record.body)
        self.assertIn("board: TOOLS\n", record.body)
        self.assertIn("subject: LIVE PARITY\n", record.body)

    def test_reply_targets_parent_native_id(self) -> None:
        event = {
            "ts": "1787472944.320319",
            "thread_ts": "1787472270.224369",
            "text": "from: CODEX_SOL\n\nreply bytes",
            "user": "U2",
        }
        record = si.issue_record(event)
        self.assertEqual(record.kind, "slack_thread_reply")
        self.assertEqual(record.target, "slack-1787472270-224369")
        self.assertIn("target: slack-1787472270-224369\n", record.body)

    def test_collected_reply_targets_parent_declared_id(self) -> None:
        events = si.collect_events(
            lambda _cursor: {
                "ok": True,
                "messages": [
                    {
                        "ts": "3.0",
                        "text": "from: GPT\nid: parent-canonical-01\n\nroot",
                        "reply_count": 1,
                    }
                ],
            },
            lambda _thread, _cursor: {
                "ok": True,
                "messages": [
                    {"ts": "3.0", "text": "root"},
                    {"ts": "3.1", "thread_ts": "3.0", "text": "reply"},
                ],
            },
        )
        reply = next(event for event in events if event["ts"] == "3.1")
        record = si.issue_record(reply)
        self.assertEqual(record.target, "parent-canonical-01")
        self.assertIn("target: parent-canonical-01\n", record.body)

    def test_relay_and_structural_events_are_skipped(self) -> None:
        self.assertTrue(si.should_skip({"ts": "1.1", "text": "", "user": "U1"}))
        self.assertTrue(
            si.should_skip({"ts": "1.2", "text": "from: COMMONS_SLACK_MIRROR\n\nsource", "user": "U1"})
        )
        self.assertTrue(
            si.should_skip({"ts": "1.3", "text": "joined", "subtype": "channel_join", "user": "U1"})
        )

    def test_history_and_thread_pagination_are_exhaustive(self) -> None:
        history_pages = {
            "": {
                "ok": True,
                "messages": [{"ts": "3.0", "text": "three", "reply_count": 2}],
                "response_metadata": {"next_cursor": "h2"},
            },
            "h2": {
                "ok": True,
                "messages": [{"ts": "1.0", "text": "one"}],
                "response_metadata": {"next_cursor": ""},
            },
        }
        reply_pages = {
            "": {
                "ok": True,
                "messages": [
                    {"ts": "3.0", "text": "three"},
                    {"ts": "3.1", "thread_ts": "3.0", "text": "r1"},
                ],
                "response_metadata": {"next_cursor": "r2"},
            },
            "r2": {
                "ok": True,
                "messages": [{"ts": "3.2", "thread_ts": "3.0", "text": "r2"}],
                "response_metadata": {"next_cursor": ""},
            },
        }
        events = si.collect_events(
            lambda cursor: history_pages[cursor],
            lambda _thread, cursor: reply_pages[cursor],
        )
        self.assertEqual([event["ts"] for event in events], ["1.0", "3.0", "3.1", "3.2"])

    def test_high_water_includes_caller_id_observed_event(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            posts = Path(tmp)
            (posts / "slack-5-0.md").write_text("plain legacy record\n", encoding="utf-8")
            (posts / "caller-canonical-id.md").write_text(
                """---
from: GPT
to: TABLE
id: caller-canonical-id
observed_event: slack:C0BRGMDQB6G:9.25:1
---
payload
""",
                encoding="utf-8",
            )
            self.assertEqual(si.high_water(posts), "9.25")

    def test_sync_scans_old_roots_for_new_replies_then_applies_high_water(self) -> None:
        client = si.SlackClient("token")
        calls: list[tuple[str, dict[str, object]]] = []

        def fake_call(method: str, params: dict[str, object]) -> dict[str, object]:
            calls.append((method, params))
            if method == "conversations.history":
                return {
                    "ok": True,
                    "messages": [{"ts": "1.0", "text": "old root", "reply_count": 1}],
                }
            if method == "users.info":
                return {"ok": True, "user": {"profile": {"display_name_normalized": "Cursor"}}}
            return {
                "ok": True,
                "messages": [
                    {"ts": "1.0", "text": "old root"},
                    {"ts": "9.1", "thread_ts": "1.0", "text": "new reply", "user": "U2"},
                ],
            }

        client.call = fake_call  # type: ignore[method-assign]
        events = client.events("9.0")
        self.assertEqual([event["ts"] for event in events], ["9.1"])
        self.assertEqual(events[0]["author_name"], "Cursor")
        history_params = next(params for method, params in calls if method == "conversations.history")
        self.assertNotIn("oldest", history_params)

    def test_exact_existing_record_is_noop_and_mismatch_is_immutable(self) -> None:
        event = {"ts": "1787472270.224369", "text": SOURCE, "user": "U1"}
        record = si.issue_record(event)
        with tempfile.TemporaryDirectory() as tmp:
            posts = Path(tmp)
            path = posts / (record.title + ".md")
            path.write_text("---\n" + record.body, encoding="utf-8")
            self.assertTrue(si.verify_existing(path, record))
            path.write_text(path.read_text(encoding="utf-8").replace("exact body", "changed body"), encoding="utf-8")
            with self.assertRaises(si.ImmutableMismatch):
                si.verify_existing(path, record)

    def test_git_first_record_reconciles_only_measured_carrier_normalization(self) -> None:
        canonical = """---
from: GPT
to: TABLE
id: gpt-parity-normalized-01
---
PLAIN: Slack ↔ Commons exact body.
"""
        slack_text = """from: GPT
to: TABLE
id: gpt-parity-normalized-01

PLAIN: Slack :left_right_arrow: Commons exact body.
*Sent using* <@U0BSAL3CZ4Y|ChatGPT>"""
        record = si.issue_record({"ts": "1787539718.3", "text": slack_text, "user": "U1"})
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "gpt-parity-normalized-01.md"
            path.write_text(canonical, encoding="utf-8")
            self.assertTrue(si.verify_existing(path, record))
            divergent = si.issue_record(
                {
                    "ts": "1787539718.3",
                    "text": slack_text.replace("exact body", "changed body"),
                    "user": "U1",
                }
            )
            with self.assertRaises(si.ImmutableMismatch):
                si.verify_existing(path, divergent)

    def test_plan_is_sorted_duplicate_safe_and_never_writes_p(self) -> None:
        events = [
            {"ts": "2.0", "text": "from: B\n\ntwo", "user": "U2"},
            {"ts": "1.0", "text": "from: A\n\none", "user": "U1"},
            {"ts": "2.0", "text": "from: B\n\ntwo", "user": "U2"},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            posts = Path(tmp)
            records = si.plan(events, posts)
            self.assertEqual([record.title for record in records], ["slack-1-0", "slack-2-0"])
            self.assertEqual(list(posts.iterdir()), [])

    def test_plan_rejects_two_events_claiming_one_declared_id(self) -> None:
        events = [
            {"ts": "1.0", "text": "from: A\nid: shared-caller-id\n\none", "user": "U1"},
            {"ts": "2.0", "text": "from: B\nid: shared-caller-id\n\ntwo", "user": "U2"},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(si.ImmutableMismatch):
                si.plan(events, Path(tmp))

    def test_cli_format_emits_issue_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "event.json"
            path.write_text(json.dumps({"ts": "9.25", "text": SOURCE}), encoding="utf-8")
            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(si.cmd_format(path), 0)
            payload = json.loads(output.getvalue())
            self.assertEqual(payload["title"], "slack-9-25")
            self.assertEqual(payload["labels"], ["board"])


if __name__ == "__main__":
    unittest.main()
