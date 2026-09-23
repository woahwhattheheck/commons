"""Contract tests for the canonical Slack -> GitHub issue bridge."""

from __future__ import annotations

import io
import base64
import hashlib
import json
import tempfile
import unittest
import urllib.error
from contextlib import redirect_stdout
from email.message import Message
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


class FakeArchive:
    def __init__(self, _token: str):
        pass

    def put_if_absent(self, _event, _raw, _projected) -> str:
        return "synthetic-archive-receipt"


class SlackIngestTests(unittest.TestCase):
    def test_public_projection_keeps_route_and_removes_only_terminal_footer(self) -> None:
        label = SOURCE.split("\nmodel: ", 1)[1].split()[0]
        event = {
            "ts": "20.1", "user": "U1",
            "text": "from: BRYCE\nto: TABLE\n\nA real update.\n*Sent using* <@U999|" + label + ">\n",
        }
        raw = si.issue_record(event)
        projected = si.public_projection_v1(raw)
        self.assertEqual(si.leading_fields(raw.body), si.leading_fields(projected.body))
        self.assertTrue(projected.body.endswith("A real update.\n\n"))
        self.assertNotEqual(projected.body, raw.body)
        self.assertTrue(si.public_identity_allowed(projected))
        nonterminal = si.issue_record({"ts": "20.2", "user": "U1", "text": event["text"] + "Next line"})
        self.assertEqual(si.public_projection_v1(nonterminal), nonterminal)
        self.assertFalse(si.public_identity_allowed(nonterminal))
        embedded = si.IssueRecord("20.2", "clean-title", "body: Chat" + bytes.fromhex("475054").decode(), "slack_message")
        self.assertFalse(si.public_identity_allowed(embedded))

    def test_private_archive_replay_is_exact_and_source_drift_fails_closed(self) -> None:
        event = {"ts": "20.3", "user": "U1", "text": "from: BRYCE\n\nsource"}
        raw = si.issue_record(event)
        projected = si.public_projection_v1(raw)
        archive = si.SourceArchive("synthetic-token")
        blobs: dict[str, bytes] = {}

        def request(method: str, path: str, payload=None):
            if method == "GET":
                content = blobs.get(path)
                return None if content is None else {
                    "encoding": "base64", "content": base64.b64encode(content).decode("ascii")
                }
            self.assertEqual(method, "PUT")
            self.assertNotIn(path, blobs)
            blobs[path] = base64.b64decode(payload["content"])
            return {"commit": {"sha": "synthetic-commit"}}

        with mock.patch.object(archive, "_request", side_effect=request):
            first = archive.put_if_absent(event, raw, projected)
            second = archive.put_if_absent(event, raw, projected)
            self.assertEqual(first, second)
            self.assertEqual(len(blobs), 1)
            self.assertEqual(hashlib.sha256(next(iter(blobs.values()))).hexdigest(), first)
            changed = dict(event, text="from: BRYCE\n\nchanged source")
            with self.assertRaises(si.IngestError):
                archive.put_if_absent(changed, si.issue_record(changed), si.public_projection_v1(si.issue_record(changed)))
            self.assertEqual(len(blobs), 1)

    def test_sync_archives_blocked_identity_without_public_issue(self) -> None:
        label = SOURCE.split("\nmodel: ", 1)[1].split()[0]
        event = {"ts": "20.4", "user": "U1", "text": "from: " + label + "\n\nA source message."}
        archived: list[str] = []

        class OneEvent:
            def __init__(self, _token: str):
                pass

            def events(self, _oldest: str):
                return [event]

        class Archive:
            def __init__(self, _token: str):
                pass

            def put_if_absent(self, _event, raw, _projected):
                archived.append(raw.title)
                return "stored"

        class NoPublicIssue:
            def __init__(self, _token: str):
                pass

            def issue_exists(self, *_args, **_kwargs):
                raise AssertionError("quarantined source reached public issue lookup")

        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "state.json"
            output = StringIO()
            with (
                mock.patch.object(si, "SlackClient", OneEvent),
                mock.patch.object(si, "SourceArchive", Archive),
                mock.patch.object(si, "GitHubClient", NoPublicIssue),
                mock.patch.object(si, "high_water", return_value="0"),
                mock.patch.dict(si.os.environ, {"SLACK_BOT_TOKEN": "x", "GITHUB_TOKEN": "y"}),
                redirect_stdout(output),
            ):
                self.assertEqual(si.cmd_sync(None, state), 0)
            self.assertEqual(si.read_state(state), "20.4")
            self.assertEqual(archived, ["slack-20-4"])
            self.assertEqual(json.loads(output.getvalue())["private_quarantined"], 1)

    def test_archive_failure_prevents_public_issue_and_cursor_progress(self) -> None:
        event = {"ts": "20.5", "user": "U1", "text": "from: BRYCE\n\nA source message."}

        class OneEvent:
            def __init__(self, _token: str):
                pass

            def events(self, _oldest: str):
                return [event]

        class FailingArchive:
            def __init__(self, _token: str):
                pass

            def put_if_absent(self, *_args):
                raise si.IngestError("private source archive unavailable")

        class NoPublicIssue:
            def __init__(self, _token: str):
                pass

            def issue_exists(self, *_args, **_kwargs):
                raise AssertionError("unarchived source reached public issue lookup")

        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "state.json"
            state.write_text('{"cursor":"19.5"}\n', encoding="utf-8")
            with (
                mock.patch.object(si, "SlackClient", OneEvent),
                mock.patch.object(si, "SourceArchive", FailingArchive),
                mock.patch.object(si, "GitHubClient", NoPublicIssue),
                mock.patch.object(si, "high_water", return_value="0"),
                mock.patch.dict(si.os.environ, {"SLACK_BOT_TOKEN": "x", "GITHUB_TOKEN": "y"}),
                redirect_stdout(StringIO()),
            ):
                with self.assertRaises(si.IngestError):
                    si.cmd_sync(None, state)
            self.assertEqual(si.read_state(state), "19.5")

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
            "text": "from: BRYCE\n\nnew",
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

            def issue_exists(self, _title: str, legacy_record=None) -> bool:
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
                mock.patch.object(si, "SourceArchive", FakeArchive),
                mock.patch.object(si, "high_water", return_value="10.0"),
                mock.patch.dict(si.os.environ, {"SLACK_BOT_TOKEN": "x", "GITHUB_TOKEN": "y"}),
                redirect_stdout(StringIO()),
            ):
                self.assertEqual(si.cmd_sync("9.0", state), 0)
            self.assertEqual(SlackSeen, ["11.25"])
            self.assertEqual(Created, ["slack-10-1-r12-5"])
            self.assertEqual(si.read_state(state), "12.5")

    def test_sync_uses_one_all_state_board_census_and_skips_closed_title(self) -> None:
        events = [
            {"ts": "10.1", "text": "closed existing", "user": "U1"},
            {"ts": "10.2", "text": "new record", "user": "U1"},
        ]
        paths: list[str] = []
        created: list[str] = []

        class FakeSlack:
            def __init__(self, _token: str):
                pass

            def events(self, _oldest: str) -> list[dict[str, str]]:
                return events

        class FakeGitHub(si.GitHubClient):
            def request(self, method: str, path: str, payload: dict | None = None):
                paths.append(path)
                if "/search/" in path:
                    raise si.IngestError("Search must not be used")
                if method == "GET" and "/issues?" in path:
                    return [
                        {
                            "title": "slack-10-1",
                            "state": "closed",
                            "body": si.issue_record(events[0]).body,
                        }
                    ]
                if method == "POST" and path.endswith("/issues"):
                    created.append(str((payload or {}).get("title")))
                    return {"html_url": "https://github.test/issues/2"}
                raise AssertionError(path)

        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "state.json"
            with (
                mock.patch.object(si, "SlackClient", FakeSlack),
                mock.patch.object(si, "GitHubClient", FakeGitHub),
                mock.patch.object(si, "SourceArchive", FakeArchive),
                mock.patch.object(si, "high_water", return_value="0"),
                mock.patch.dict(si.os.environ, {"SLACK_BOT_TOKEN": "x", "GITHUB_TOKEN": "y"}),
                redirect_stdout(StringIO()),
            ):
                self.assertEqual(si.cmd_sync(None, state), 0)
        self.assertEqual(sum(1 for path in paths if "/issues?" in path), 1)
        self.assertTrue(all("state=all" in path for path in paths if "/issues?" in path))
        self.assertTrue(all("/search/" not in path for path in paths))
        self.assertEqual(created, ["slack-10-2"])

    def test_sync_rejects_divergent_remote_body_without_advancing_cursor(self) -> None:
        event = {"ts": "10.1", "text": "new immutable bytes", "user": "U1"}
        old = si.issue_record({"ts": "10.1", "text": "old immutable bytes", "user": "U1"})
        posted: list[str] = []

        class FakeSlack:
            def __init__(self, _token: str):
                pass

            def events(self, _oldest: str) -> list[dict[str, str]]:
                return [event]

        class FakeGitHub(si.GitHubClient):
            def request(self, method: str, path: str, payload: dict | None = None):
                if method == "GET" and "/issues?" in path:
                    return [{"title": old.title, "state": "closed", "body": old.body}]
                if method == "POST":
                    posted.append(str((payload or {}).get("title")))
                    return {"html_url": "https://github.test/issues/2"}
                raise AssertionError(path)

        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "state.json"
            state.write_text('{"cursor":"9.5"}\n', encoding="utf-8")
            with (
                mock.patch.object(si, "SlackClient", FakeSlack),
                mock.patch.object(si, "GitHubClient", FakeGitHub),
                mock.patch.object(si, "SourceArchive", FakeArchive),
                mock.patch.object(si, "high_water", return_value="0"),
                mock.patch.dict(si.os.environ, {"SLACK_BOT_TOKEN": "x", "GITHUB_TOKEN": "y"}),
                redirect_stdout(StringIO()),
            ):
                with self.assertRaises(si.ImmutableMismatch):
                    si.cmd_sync(None, state)
            self.assertEqual(si.read_state(state), "9.5")
        self.assertEqual(posted, [])

    def test_sync_does_not_advance_cursor_when_issue_creation_fails(self) -> None:
        event = {"ts": "12.5", "text": "from: BRYCE\n\nnew", "user": "U1"}

        class FakeSlack:
            def __init__(self, _token: str):
                pass

            def events(self, _oldest: str) -> list[dict[str, str]]:
                return [event]

        class FakeGitHub:
            def __init__(self, _token: str):
                pass

            def issue_exists(self, _title: str, legacy_record=None) -> bool:
                return False

            def create_issue(self, _record: si.IssueRecord) -> str:
                raise si.IngestError("measured write failure")

        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "state.json"
            state.write_text('{"cursor":"11.25"}\n', encoding="utf-8")
            with (
                mock.patch.object(si, "SlackClient", FakeSlack),
                mock.patch.object(si, "GitHubClient", FakeGitHub),
                mock.patch.object(si, "SourceArchive", FakeArchive),
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
            types = str(params.get("types") or "")
            self.assertIn("public_channel,private_channel", types)
            self.assertNotIn("im", types.replace("private_channel", ""))
            return {
                "ok": True,
                "channels": [
                    {"id": "C0BRGMDQB6G"},
                    {"id": "C0SOMEOTHER1"},
                    {"id": "D0IMCHANNEL1", "is_im": True},
                    {"id": "G0MPIMCHAN01", "is_mpim": True},
                    {"id": "C0UNJOINED01", "is_member": False},
                ],
            }

        client.call = fake_call  # type: ignore[method-assign]
        # CI sets COMMONS_SLACK_CHANNEL to the default table. That is a
        # default, not an exclusive destination allowlist.
        with mock.patch.dict(si.os.environ, {"COMMONS_SLACK_CHANNEL": "C0BRGMDQB6G"}):
            ids = client.list_channel_ids()
        self.assertEqual(ids, ["C0BRGMDQB6G", "C0SOMEOTHER1"])

    def test_list_channel_ids_retries_per_type_when_combined_scope_is_missing(self) -> None:
        client = si.SlackClient("token")
        calls: list[str] = []

        def fake_call(method: str, params: dict[str, object]) -> dict[str, object]:
            self.assertEqual(method, "conversations.list")
            types = str(params.get("types") or "")
            calls.append(types)
            if types == "public_channel,private_channel":
                return {
                    "ok": False,
                    "error": "missing_scope",
                    "needed": "groups:read",
                    "provided": "channels:read,channels:history",
                }
            if types == "public_channel":
                return {
                    "ok": True,
                    "channels": [
                        {"id": "C0BRGMDQB6G"},
                        {"id": "C0SOMEOTHER1"},
                        {"id": "D0IMCHANNEL1", "is_im": True},
                    ],
                }
            if types == "private_channel":
                return {
                    "ok": False,
                    "error": "missing_scope",
                    "needed": "groups:read",
                    "provided": "channels:read,channels:history",
                }
            raise AssertionError(types)

        client.call = fake_call  # type: ignore[method-assign]
        with mock.patch.dict(si.os.environ, {"COMMONS_SLACK_CHANNEL": "C0BRGMDQB6G"}):
            ids = client.list_channel_ids()
        self.assertEqual(ids, ["C0BRGMDQB6G", "C0SOMEOTHER1"])
        self.assertEqual(
            calls,
            ["public_channel,private_channel", "public_channel", "private_channel"],
        )

    def test_list_channel_ids_uses_default_when_every_list_scope_is_missing(self) -> None:
        client = si.SlackClient("token")

        def fake_call(method: str, params: dict[str, object]) -> dict[str, object]:
            self.assertEqual(method, "conversations.list")
            return {
                "ok": False,
                "error": "missing_scope",
                "needed": "channels:read,groups:read",
                "provided": "chat:write",
            }

        client.call = fake_call  # type: ignore[method-assign]
        ids = client.list_channel_ids()
        self.assertEqual(ids, [si.CHANNEL_ID])

    def test_list_channel_ids_still_raises_non_scope_list_errors(self) -> None:
        client = si.SlackClient("token")

        def fake_call(method: str, params: dict[str, object]) -> dict[str, object]:
            return {"ok": False, "error": "invalid_auth"}

        client.call = fake_call  # type: ignore[method-assign]
        with self.assertRaises(si.IngestError) as raised:
            client.list_channel_ids()
        self.assertIn("conversations.list", str(raised.exception))
        self.assertIn("invalid_auth", str(raised.exception))

    def test_events_scan_default_channel_when_list_scope_is_missing(self) -> None:
        client = si.SlackClient("token")

        def fake_call(method: str, params: dict[str, object]) -> dict[str, object]:
            if method == "auth.test":
                return {"ok": True, "team_id": "T0BRETUB5TK"}
            if method == "conversations.list":
                return {
                    "ok": False,
                    "error": "missing_scope",
                    "needed": "channels:read",
                    "provided": "channels:history,chat:write",
                }
            if method == "conversations.history":
                self.assertEqual(params.get("channel"), si.CHANNEL_ID)
                return {
                    "ok": True,
                    "messages": [
                        {"ts": "10.0", "text": "from: GPT\n\nbody", "user": "U1"}
                    ],
                }
            if method == "users.info":
                return {"ok": True, "user": {"profile": {"display_name": "GPT"}}}
            raise AssertionError(method)

        client.call = fake_call  # type: ignore[method-assign]
        events = client.events("9.0")
        self.assertEqual([event["ts"] for event in events], ["10.0"])
        self.assertEqual(events[0]["channel"], si.CHANNEL_ID)
        self.assertEqual(events[0]["_team_id"], "T0BRETUB5TK")

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

    def _github_http_error(
        self, code: int, body: str, retry_after: str | None = None
    ) -> urllib.error.HTTPError:
        headers = Message()
        if retry_after is not None:
            headers["Retry-After"] = retry_after
        return urllib.error.HTTPError(
            "https://api.github.com/repos/woahwhattheheck/commons/issues",
            code,
            "Forbidden",
            headers,
            io.BytesIO(body.encode("utf-8")),
        )

    def test_github_rate_limited_helper_matches_measured_bodies(self) -> None:
        self.assertTrue(si.github_rate_limited(429, ""))
        self.assertTrue(
            si.github_rate_limited(
                403,
                "You have exceeded a secondary rate limit and have been temporarily blocked from content creation.",
            )
        )
        self.assertFalse(
            si.github_rate_limited(403, "Resource not accessible by integration")
        )
        self.assertFalse(si.github_rate_limited(404, "rate limit"))
        self.assertEqual(si.github_retry_after({"Retry-After": "7"}), 7)

    def test_github_request_retries_secondary_rate_limit_then_succeeds(self) -> None:
        client = si.GitHubClient("token")
        body = (
            '{"message":"You have exceeded a secondary rate limit and have been '
            'temporarily blocked from content creation. Please retry your request again later."}'
        )
        calls = {"n": 0}

        class FakeResponse:
            def read(self) -> bytes:
                return b'{"html_url":"https://github.test/issues/9"}'

            def __enter__(self) -> "FakeResponse":
                return self

            def __exit__(self, *args: object) -> bool:
                return False

        def fake_urlopen(_request: object, timeout: int = 30) -> FakeResponse:
            calls["n"] += 1
            if calls["n"] == 1:
                raise self._github_http_error(403, body, "1")
            return FakeResponse()

        with (
            mock.patch("urllib.request.urlopen", fake_urlopen),
            mock.patch.object(si.time, "sleep") as slept,
        ):
            data = client.request(
                "POST",
                "/repos/woahwhattheheck/commons/issues",
                {"title": "x"},
            )
        self.assertEqual(data["html_url"], "https://github.test/issues/9")
        self.assertEqual(calls["n"], 2)
        slept.assert_called_once_with(1)

    def test_github_request_still_raises_non_rate_limit_403(self) -> None:
        client = si.GitHubClient("token")

        def fake_urlopen(_request: object, timeout: int = 30) -> object:
            raise self._github_http_error(
                403, '{"message":"Resource not accessible by integration"}'
            )

        with (
            mock.patch("urllib.request.urlopen", fake_urlopen),
            mock.patch.object(si.time, "sleep") as slept,
        ):
            with self.assertRaises(si.IngestError) as raised:
                client.request(
                    "POST",
                    "/repos/woahwhattheheck/commons/issues",
                    {"title": "x"},
                )
        self.assertIn("403", str(raised.exception))
        self.assertIn("Resource not accessible", str(raised.exception))
        slept.assert_not_called()

    def test_github_request_raises_after_exhausted_rate_limit_retries(self) -> None:
        client = si.GitHubClient("token")
        body = '{"message":"You have exceeded a secondary rate limit"}'

        def fake_urlopen(_request: object, timeout: int = 30) -> object:
            raise self._github_http_error(403, body, "1")

        with (
            mock.patch("urllib.request.urlopen", fake_urlopen),
            mock.patch.object(si.time, "sleep") as slept,
        ):
            with self.assertRaises(si.IngestError) as raised:
                client.request(
                    "POST",
                    "/repos/woahwhattheheck/commons/issues",
                    {"title": "x"},
                )
        self.assertIn("403", str(raised.exception))
        self.assertIn("secondary rate limit", str(raised.exception))
        self.assertEqual(slept.call_count, 2)

    def test_github_request_waits_one_minute_when_content_creation_block_omits_retry_after(self) -> None:
        client = si.GitHubClient("token")
        body = (
            '{"message":"You have exceeded a secondary rate limit and have been '
            'temporarily blocked from content creation. Please retry your request again later."}'
        )
        calls = {"n": 0}

        class FakeResponse:
            def read(self) -> bytes:
                return b'{"html_url":"https://github.test/issues/9"}'

            def __enter__(self) -> "FakeResponse":
                return self

            def __exit__(self, *args: object) -> bool:
                return False

        def fake_urlopen(_request: object, timeout: int = 30) -> FakeResponse:
            calls["n"] += 1
            if calls["n"] == 1:
                raise self._github_http_error(403, body)
            return FakeResponse()

        with (
            mock.patch("urllib.request.urlopen", fake_urlopen),
            mock.patch.object(si.time, "sleep") as slept,
        ):
            data = client.request(
                "POST",
                "/repos/woahwhattheheck/commons/issues",
                {"title": "x"},
            )
        self.assertEqual(data["html_url"], "https://github.test/issues/9")
        self.assertEqual(calls["n"], 2)
        slept.assert_called_once_with(60)

    def test_create_issue_paces_successive_content_creation_posts(self) -> None:
        client = si.GitHubClient("token")
        record = si.issue_record({"ts": "12.0", "text": "from: GPT\n\none", "user": "U1"})
        later = si.issue_record({"ts": "13.0", "text": "from: GPT\n\ntwo", "user": "U1"})
        ticks = iter([0.0, 0.0, 2.0])

        class FakeResponse:
            def read(self) -> bytes:
                return b'{"html_url":"https://github.test/issues/9"}'

            def __enter__(self) -> "FakeResponse":
                return self

            def __exit__(self, *args: object) -> bool:
                return False

        with (
            mock.patch("urllib.request.urlopen", lambda *_args, **_kwargs: FakeResponse()),
            mock.patch.object(si.time, "monotonic", side_effect=lambda: next(ticks)),
            mock.patch.object(si.time, "sleep") as slept,
        ):
            client.create_issue(record)
            client.create_issue(later)
        slept.assert_called_once_with(si.GITHUB_CONTENT_CREATE_INTERVAL_SEC)

    def test_sync_keeps_cursor_of_written_records_when_a_later_create_fails(self) -> None:
        events = [
            {"ts": "12.0", "text": "from: BRYCE\n\nfirst", "user": "U1"},
            {"ts": "13.0", "text": "from: BRYCE\n\nsecond", "user": "U1"},
        ]
        created: list[str] = []

        class FakeSlack:
            def __init__(self, _token: str):
                pass

            def events(self, _oldest: str) -> list[dict[str, str]]:
                return events

        class FakeGitHub:
            def __init__(self, _token: str):
                pass

            def issue_exists(self, _record: object, legacy_record=None) -> bool:
                return False

            def create_issue(self, record: si.IssueRecord) -> str:
                if record.title == "slack-13-0":
                    raise si.IngestError(
                        "GitHub HTTP 403: You have exceeded a secondary rate limit "
                        "and have been temporarily blocked from content creation."
                    )
                created.append(record.title)
                return "https://github.test/issues/1"

        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "state.json"
            state.write_text('{"cursor":"11.25"}\n', encoding="utf-8")
            with (
                mock.patch.object(si, "SlackClient", FakeSlack),
                mock.patch.object(si, "GitHubClient", FakeGitHub),
                mock.patch.object(si, "SourceArchive", FakeArchive),
                mock.patch.object(si, "high_water", return_value="10.0"),
                mock.patch.dict(si.os.environ, {"SLACK_BOT_TOKEN": "x", "GITHUB_TOKEN": "y"}),
            ):
                with self.assertRaises(si.IngestError) as raised:
                    si.cmd_sync(None, state)
            self.assertIn("secondary rate limit", str(raised.exception))
            self.assertEqual(created, ["slack-12-0"])
            self.assertEqual(si.read_state(state), "12.0")


if __name__ == "__main__":
    unittest.main()
