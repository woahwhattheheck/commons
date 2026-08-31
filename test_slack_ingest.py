"""Contract tests for the canonical Slack -> GitHub issue bridge."""

from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock

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
            "observed_event: slack:UNKNOWN_WORKSPACE:C0BRGMDQB6G:1787539715.067529:1\n",
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
        self.assertIn(
            "observed_event: slack:UNKNOWN_WORKSPACE:C0BRGMDQB6G:1787472270.224369:1\n",
            record.body,
        )
        self.assertIn("carrier_ts: 1787472270.224369\n", record.body)
        self.assertIn("event_ts: 1787472270.224369\n", record.body)
        self.assertIn("revision: 1\n", record.body)
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


    def test_other_channel_is_not_an_allowlist_reject(self) -> None:
        record = si.issue_record(
            {
                "ts": "1787539718.3",
                "channel": "C0SOMEOTHER1",
                "text": "from: BRYCE\n\nhello from another channel",
                "user": "U1",
            }
        )
        self.assertIn(
            "observed_event: slack:UNKNOWN_WORKSPACE:C0SOMEOTHER1:1787539718.3:1\n",
            record.body,
        )
        self.assertEqual(record.title, "slack-1787539718-3")

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
            (posts / "foreign-channel-id.md").write_text(
                """---
from: GPT
to: TABLE
id: foreign-channel-id
observed_event: slack:COTHER:99.0:7
---
payload
""",
                encoding="utf-8",
            )
            (posts / "edited-revision.md").write_text(
                """---
from: GPT
to: TABLE
id: edited-revision
observed_event: slack:T0TEAM:COTHER:10.0:25.5
event_ts: 25.5
revision: 25.5
---
edited payload
""",
                encoding="utf-8",
            )
            self.assertEqual(si.high_water(posts), "99.0")

    def test_posts_json_bootstraps_fallback_declared_and_edit_clocks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "posts.json"
            path.write_text(
                json.dumps(
                    [
                        {"id": "slack-5-25"},
                        {
                            "id": "caller-canonical-id",
                            "observed_event": "slack:T0TEAM:C0BRGMDQB6G:9.75:1",
                        },
                        {"id": "caller-edit-id", "event_ts": "12.5"},
                    ]
                ),
                encoding="utf-8",
            )
            self.assertEqual(si.posts_json_high_water(path), "12.5")

    def test_state_round_trip_is_exact_and_zero_is_a_valid_cursor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            self.assertEqual(si.read_state(path), "0")
            self.assertEqual(si._cursor_decimal("0"), 0)
            si.write_state(path, "1787987663.666409")
            self.assertEqual(si.read_state(path), "1787987663.666409")

    def test_sync_uses_newest_baseline_and_advances_to_edit_clock(self) -> None:
        event = {
            "ts": "10.1",
            "edited": {"ts": "12.5"},
            "text": "from: GPT\n\nnew",
            "user": "U1",
        }

        class FakeSlack:
            def __init__(self, _token: str):
                pass

            def events(self, oldest: str) -> list[dict[str, object]]:
                SlackSeen.append(oldest)
                return [event]

        class FakeGitHub:
            def __init__(self, _token: str):
                pass

            def issue_exists(self, _title: str) -> bool:
                return False

            def create_issue(self, record: si.IssueRecord) -> str:
                Created.append(record.title)
                return "https://example.invalid/issues/1"

        SlackSeen: list[str] = []
        Created: list[str] = []
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "state.json"
            state.write_text('{"cursor":"11.25"}\n', encoding="utf-8")
            with (
                mock.patch.object(si, "SlackClient", FakeSlack),
                mock.patch.object(si, "GitHubClient", FakeGitHub),
                mock.patch.object(si, "high_water", return_value="10.0"),
                mock.patch.dict(si.os.environ, {"SLACK_BOT_TOKEN": "x", "GITHUB_TOKEN": "y"}),
                redirect_stdout(StringIO()),
            ):
                self.assertEqual(si.cmd_sync("9.0", state), 0)
            self.assertEqual(SlackSeen, ["11.25"])
            self.assertEqual(Created, ["slack-10-1-r12-5"])
            self.assertEqual(si.read_state(state), "12.5")

    def test_sync_does_not_advance_cursor_when_issue_creation_fails(self) -> None:
        event = {"ts": "12.5", "text": "from: GPT\n\nnew", "user": "U1"}

        class FakeSlack:
            def __init__(self, _token: str):
                pass

            def events(self, _oldest: str) -> list[dict[str, str]]:
                return [event]

        class FakeGitHub:
            def __init__(self, _token: str):
                pass

            def issue_exists(self, _title: str) -> bool:
                return False

            def create_issue(self, _record: si.IssueRecord) -> str:
                raise si.IngestError("measured write failure")

        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "state.json"
            state.write_text('{"cursor":"11.25"}\n', encoding="utf-8")
            with (
                mock.patch.object(si, "SlackClient", FakeSlack),
                mock.patch.object(si, "GitHubClient", FakeGitHub),
                mock.patch.object(si, "high_water", return_value="10.0"),
                mock.patch.dict(si.os.environ, {"SLACK_BOT_TOKEN": "x", "GITHUB_TOKEN": "y"}),
            ):
                with self.assertRaises(si.IngestError):
                    si.cmd_sync(None, state)
            self.assertEqual(si.read_state(state), "11.25")

    def test_sync_scans_old_roots_for_new_replies_then_applies_high_water(self) -> None:
        client = si.SlackClient("token")
        calls: list[tuple[str, dict[str, object]]] = []

        def fake_call(method: str, params: dict[str, object]) -> dict[str, object]:
            calls.append((method, params))
            if method == "auth.test":
                return {"ok": True, "team_id": "T0BRETUB5TK"}
            if method == "conversations.list":
                return {"ok": True, "channels": [{"id": "C0BRGMDQB6G", "is_im": False}]}
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
        self.assertEqual(events[0]["_team_id"], "T0BRETUB5TK")
        history_params = next(params for method, params in calls if method == "conversations.history")
        self.assertNotIn("oldest", history_params)

    def test_list_channel_ids_is_workspace_not_allowlist_and_skips_ims(self) -> None:
        client = si.SlackClient("token")

        def fake_call(method: str, params: dict[str, object]) -> dict[str, object]:
            self.assertEqual(method, "conversations.list")
            self.assertIn("public_channel,private_channel", str(params.get("types") or ""))
            return {
                "ok": True,
                "channels": [
                    {"id": "C0BRGMDQB6G"},
                    {"id": "C0SOMEOTHER1"},
                ],
            }

        client.call = fake_call  # type: ignore[method-assign]
        ids = client.list_channel_ids()
        self.assertEqual(ids, ["C0BRGMDQB6G", "C0SOMEOTHER1"])

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

    def test_same_declared_id_and_body_dedupes_across_carrier_timestamps(self) -> None:
        text = "from: GPT\nid: same-object-20260824-01\n\nPLAIN: same bytes"
        first_event = {"ts": "10.1", "text": text, "user": "U1"}
        second_event = {"ts": "10.2", "text": text, "user": "U1"}
        with tempfile.TemporaryDirectory() as tmp:
            posts = Path(tmp)
            records = si.plan([first_event, second_event], posts)
            self.assertEqual([record.title for record in records], ["same-object-20260824-01"])

            first = si.issue_record(first_event)
            path = posts / (first.title + ".md")
            path.write_text("---\n" + first.body, encoding="utf-8")
            self.assertTrue(si.verify_existing(path, si.issue_record(second_event)))

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

    def test_edited_history_message_mints_append_only_revision(self) -> None:
        event = {
            "team_id": "T0BRETUB5TK",
            "channel": "C0BRGMDQB6G",
            "ts": "10.1",
            "text": "from: GPT\nid: durable-object-01\n\ncorrected bytes",
            "edited": {"user": "U1", "ts": "12.5"},
            "user": "U1",
        }
        record = si.issue_record(event)
        self.assertEqual(record.title, "durable-object-01-r12-5")
        self.assertEqual(record.kind, "slack_message_edit")
        self.assertEqual(record.target, "durable-object-01")
        self.assertIn("revision: 12.5\n", record.body)
        self.assertIn("event_ts: 12.5\n", record.body)
        self.assertIn(
            "observed_event: slack:T0BRETUB5TK:C0BRGMDQB6G:10.1:12.5\n",
            record.body,
        )
        self.assertTrue(record.body.endswith("corrected bytes"))

    def test_delete_event_mints_tombstone_without_overwriting_or_republishing_body(self) -> None:
        event = {
            "team_id": "T0BRETUB5TK",
            "channel": "C0BRGMDQB6G",
            "subtype": "message_deleted",
            "deleted_ts": "10.1",
            "event_ts": "13.6",
            "ts": "13.6",
            "previous_message": {
                "ts": "10.1",
                "text": "from: GPT\nid: durable-object-01\n\nprivate old bytes",
                "user": "U1",
            },
        }
        record = si.issue_record(event)
        self.assertEqual(record.title, "durable-object-01-r13-6")
        self.assertEqual(record.kind, "slack_message_delete")
        self.assertEqual(record.target, "durable-object-01")
        self.assertIn("revision: 13.6\n", record.body)
        self.assertNotIn("private old bytes", record.body)
        self.assertTrue(record.body.endswith("prior canonical record remains immutable.\n"))

    def test_original_and_edit_are_both_planned_in_event_clock_order(self) -> None:
        original = {
            "team_id": "T0BRETUB5TK",
            "channel": "C0BRGMDQB6G",
            "ts": "10.1",
            "text": "from: GPT\nid: durable-object-01\n\noriginal",
            "user": "U1",
        }
        edited = {
            **original,
            "text": "from: GPT\nid: durable-object-01\n\ncorrected",
            "edited": {"user": "U1", "ts": "12.5"},
        }
        with tempfile.TemporaryDirectory() as tmp:
            records = si.plan([edited, original], Path(tmp))
        self.assertEqual(
            [record.title for record in records],
            ["durable-object-01", "durable-object-01-r12-5"],
        )

    def test_sync_uses_edit_clock_so_old_message_revision_crosses_high_water(self) -> None:
        client = si.SlackClient("token")

        def fake_call(method: str, params: dict[str, object]) -> dict[str, object]:
            if method == "auth.test":
                return {"ok": True, "team_id": "T0BRETUB5TK"}
            if method == "conversations.list":
                return {"ok": True, "channels": [{"id": "C0BRGMDQB6G"}]}
            if method == "conversations.history":
                return {
                    "ok": True,
                    "messages": [
                        {
                            "ts": "1.0",
                            "text": "edited now",
                            "edited": {"user": "U1", "ts": "9.1"},
                            "user": "U1",
                        }
                    ],
                }
            if method == "users.info":
                return {"ok": True, "user": {"profile": {"display_name": "GPT"}}}
            raise AssertionError(method)

        client.call = fake_call  # type: ignore[method-assign]
        events = client.events("9.0")
        self.assertEqual(len(events), 1)
        self.assertEqual(si.event_native_ts(events[0]), "1.0")
        self.assertEqual(si.event_clock(events[0]), "9.1")

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
