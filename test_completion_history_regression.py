"""Behavioral acceptance for the completed-work projection recovery.

Run in a real Commons checkout. These tests import the production renderer,
completion marker implementation and owner pin. Only the provider metadata and
Git ancestry boundary are mocked; output files are actually rendered in a
TemporaryDirectory, and any unexpected network attempt fails immediately.

Credits: #15622 / #15801 / #15875 and Z-Sol's original completion feature;
ZZ-QUARTZ-M7R4 adds retained history, stale-recent and close/reopen regressions.
"""
import contextlib
import copy
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import board_ingest as board
import completion_projection as completion
import owner_pin


DONE = "COMPLETION-M7R4-DONE-20260918"
OPEN = "COMPLETION-M7R4-OPEN-20260918"
BODY = "M7R4 unique retained body: completed work remains historical evidence."
MERGE = "c" * 40
ISSUE = 15130
PR = 15138
API = "https://api.github.com/repos/woahwhattheheck/commons"


def ids(records):
    return {record["id"] for record in records}


class CompletionHistoryRegressionTests(unittest.TestCase):
    def setUp(self):
        self.resources = contextlib.ExitStack()
        self.addCleanup(self.resources.close)
        self.temp = self.resources.enter_context(tempfile.TemporaryDirectory())
        self.root = Path(self.temp)
        for directory in ("p", "by", "to"):
            (self.root / directory).mkdir()
        self.root.joinpath("index.html").write_text(
            '<!doctype html><html><head><meta charset="utf-8"></head><body>'
            '<div id="feed" class="compact" data-limit="8">'
            '<p><a href="./board.html">open board.html</a></p></div></body></html>',
            encoding="utf-8",
        )
        for name, value in {
            "ROOT": self.temp, "POSTS": str(self.root / "p"),
            "BY": str(self.root / "by"), "TO": str(self.root / "to"),
        }.items():
            self.resources.enter_context(patch.object(board, name, value))
        self.resources.enter_context(patch.object(owner_pin, "ROOT", self.temp))
        self.ancestry = self.resources.enter_context(patch.object(
            board, "_completion_merge_is_ancestor", side_effect=lambda sha: sha == MERGE,
            create=True,
        ))
        # Exercise the stopped legacy monkeypatch on the same fixture root too.
        # These names are unused in the restored implementation; they are not a
        # production interface or a substitute for the real mod_state function.
        self.resources.enter_context(patch.object(board.publication_policy, "_ROOT", self.temp, create=True))
        self.resources.enter_context(patch.object(
            board.publication_policy, "_completion_merge_is_ancestor",
            side_effect=lambda sha: sha == MERGE, create=True,
        ))
        self.resources.enter_context(patch(
            "urllib.request.urlopen", side_effect=AssertionError("unexpected network access")
        ))
        self.rows = []
        for ident, body in ((DONE, BODY), (OPEN, "M7R4 still-open work")):
            meta = {"id": ident, "from": "UNSEATED", "to": "TABLE", "ts": "2026-09-18T12:00:00Z"}
            self.rows.append((meta["ts"], meta, body))
            self.root.joinpath("p", ident + ".md").write_text(
                "---\nfrom: UNSEATED\nto: TABLE\nid: " + ident + "\n---\n" + body + "\n",
                encoding="utf-8",
            )
        self.source_bytes = self.root.joinpath("p", DONE + ".md").read_bytes()
        self.issue = {
            "number": ISSUE, "title": DONE, "body": "Operation: " + DONE,
            "state": "closed", "state_reason": "completed", "closed_at": "2026-09-18T12:00:01Z",
            "html_url": f"https://github.com/woahwhattheheck/commons/issues/{ISSUE}",
        }
        self.pull = {
            "number": PR, "merged": True, "merged_at": "2026-09-18T12:00:00Z",
            "merge_commit_sha": MERGE, "base": {"ref": "main"}, "body": f"Closes #{ISSUE}.",
            "html_url": f"https://github.com/woahwhattheheck/commons/pull/{PR}",
        }

    def complete(self):
        marker = completion.build_marker(self.temp, DONE, self.issue, self.pull)
        completion.write_marker(self.temp, marker, lambda sha: sha == MERGE)
        return marker

    def rendered(self, rows=None):
        values = copy.deepcopy(self.rows if rows is None else rows)
        captured = []
        original_chunks = board.chunk_board.write_chunks

        def retain_chunks(records, root):
            captured.extend(copy.deepcopy(records))
            return original_chunks(records, root)

        with patch.object(board.chunk_board, "write_chunks", side_effect=retain_chunks):
            feed = board.rebuild_board(values)
        return feed, captured

    def assert_history_retained(self, feed):
        record = next(record for record in feed if record["id"] == DONE)
        self.assertEqual(BODY, record["body"])
        self.assertNotEqual("1", record.get("hidden"))
        persisted = json.loads(self.root.joinpath("posts.json").read_text(encoding="utf-8"))
        self.assertEqual(BODY, next(record for record in persisted if record["id"] == DONE)["body"])
        for name in ("board.md", "export.txt"):
            self.assertIn(BODY, self.root.joinpath(name).read_text(encoding="utf-8"))
        self.assertEqual(self.source_bytes, self.root.joinpath("p", DONE + ".md").read_bytes())

    def test_completed_history_remains_full_while_actionable_views_exclude_it(self):
        self.complete()
        feed, chunks = self.rendered()
        self.assert_history_retained(feed)
        record = next(record for record in feed if record["id"] == DONE)
        self.assertEqual("1", record.get("completed"))
        self.assertEqual(completion.marker_rel(DONE), record.get("completion_marker"))
        self.assertNotIn(DONE, ids(chunks))
        self.assertIn(OPEN, ids(chunks))
        recent = json.loads(self.root.joinpath("recent.json").read_text(encoding="utf-8"))
        self.assertNotIn(DONE, ids(recent))
        self.assertIn(OPEN, ids(recent))
        for name in ("board.html", "index.html"):
            self.assertNotIn(BODY, self.root.joinpath(name).read_text(encoding="utf-8"))
        self.assertNotIn(DONE, board.hub_pages.mod_state(copy.deepcopy(self.rows))["hidden"])

    def test_by_and_to_projection_exclude_only_completed_actionable_record(self):
        self.complete()
        rows = copy.deepcopy(self.rows)
        board.rebuild_by(rows)
        board.rebuild_to(rows)
        for directory in ("by", "to"):
            text = "\n".join(path.read_text(encoding="utf-8") for path in (self.root / directory).glob("*.html"))
            self.assertNotIn(BODY, text)
            self.assertIn("M7R4 still-open work", text)
        self.assertEqual(self.source_bytes, self.root.joinpath("p", DONE + ".md").read_bytes())

    def test_reopen_restores_live_views_without_rewriting_source_history(self):
        self.complete()
        self.rendered()
        self.assertEqual((DONE,), completion.remove_markers_for_issue(self.temp, ISSUE))
        feed, chunks = self.rendered()
        self.assert_history_retained(feed)
        self.assertIn(DONE, ids(chunks))
        self.assertNotEqual("1", next(record for record in feed if record["id"] == DONE).get("completed"))
        self.assertIn(BODY, self.root.joinpath("board.html").read_text(encoding="utf-8"))
        self.assertIn(BODY, self.root.joinpath("index.html").read_text(encoding="utf-8"))

    def test_completion_changes_source_digest_and_reopen_restores_it(self):
        before = board.post_source_snapshot()
        self.complete()
        after = board.post_source_snapshot()
        self.assertNotEqual(before["sha256"], after["sha256"])
        self.assertEqual(before["files"] + 1, after["files"])
        completion.remove_markers_for_issue(self.temp, ISSUE)
        self.assertEqual(before, board.post_source_snapshot())

    def test_nonancestor_or_truthy_nonboolean_proof_keeps_work_visible(self):
        self.complete()
        for result in (False, 1):
            with self.subTest(result=result), patch.object(board, "_completion_merge_is_ancestor", return_value=result):
                feed, chunks = self.rendered()
                self.assert_history_retained(feed)
                self.assertIn(DONE, ids(chunks))
                self.assertNotEqual("1", next(record for record in feed if record["id"] == DONE).get("completed"))

    def test_source_drift_does_not_suppress_work(self):
        self.complete()
        self.root.joinpath("p", DONE + ".md").write_bytes(self.source_bytes + b"\nnew evidence\n")
        feed, chunks = self.rendered()
        self.assertIn(DONE, ids(chunks))
        self.assertEqual(BODY, next(record for record in feed if record["id"] == DONE)["body"])

    def test_marker_does_not_hide_another_route_or_named_sender(self):
        self.complete()
        for key, value in (("to", "COURT"), ("from", "PLAYER1")):
            with self.subTest(key=key):
                rows = copy.deepcopy(self.rows)
                rows[0][1][key] = value
                feed, chunks = self.rendered(rows)
                self.assertIn(DONE, ids(chunks))
                self.assertEqual(BODY, next(record for record in feed if record["id"] == DONE)["body"])

    def test_moderation_remains_distinct_from_completion(self):
        hidden = {DONE: {"reason": "synthetic moderation fixture"}}
        with patch.object(board.hub_pages, "mod_state", return_value={"hidden": hidden}):
            feed, _ = self.rendered()
        record = next(record for record in feed if record["id"] == DONE)
        self.assertEqual("1", record.get("hidden"))
        self.assertEqual("", record["body"])
        self.assertNotEqual("1", record.get("completed"))
        self.assertEqual(self.source_bytes, self.root.joinpath("p", DONE + ".md").read_bytes())

    def test_owner_pin_cannot_restore_completed_record_from_stale_recent(self):
        self.complete()
        feed, _ = self.rendered()
        stale = [{"id": DONE, "from": "UNSEATED", "to": "TABLE", "body": BODY, "ts": self.rows[0][0]}]
        pinned = owner_pin.pin_recent(feed, stale)
        self.assertNotIn(DONE, ids(pinned))
        self.assertIn(OPEN, ids(pinned))
        self.assert_history_retained(feed)

    def provider(self, url, *args, **kwargs):
        if url == f"{API}/issues/{ISSUE}":
            return copy.deepcopy(self.issue)
        if url == f"{API}/issues/{ISSUE}/timeline?per_page=100":
            return [{"event": "cross-referenced", "source": {"issue": {
                "number": PR, "repository_url": API, "pull_request": {"url": f"{API}/pulls/{PR}"}
            }}}]
        if url == f"{API}/pulls/{PR}":
            return copy.deepcopy(self.pull)
        raise AssertionError("unexpected provider read: " + url)

    def event(self, action, issue):
        path = self.root / "event.json"
        path.write_text(json.dumps({"action": action, "issue": issue}), encoding="utf-8")
        with patch.dict(os.environ, {"GITHUB_EVENT_PATH": str(path)}), \
             patch.object(board, "_gh_api", side_effect=self.provider), \
             patch.object(board, "write_post") as ordinary_write, \
             contextlib.redirect_stdout(io.StringIO()):
            board.ingest_github_event()
        ordinary_write.assert_not_called()

    def test_close_and_edited_identity_reopen_use_real_event_entry_without_new_post(self):
        before = sorted(path.name for path in (self.root / "p").iterdir())
        self.event("closed", {"number": ISSUE, "title": "stale webhook title"})
        self.assertIn(DONE, completion.completed_operation_ids(self.temp, lambda sha: sha == MERGE))
        self.event("reopened", {"number": ISSUE, "title": "identity edited away", "body": ""})
        self.assertEqual(frozenset(), completion.completed_operation_ids(self.temp, lambda sha: sha == MERGE))
        self.assertEqual(before, sorted(path.name for path in (self.root / "p").iterdir()))
        self.assertEqual(self.source_bytes, self.root.joinpath("p", DONE + ".md").read_bytes())

    def test_closed_without_merge_proof_does_not_create_post_or_completion(self):
        self.pull["merged"] = False
        self.event("closed", {"number": ISSUE})
        self.assertEqual(frozenset(), completion.completed_operation_ids(self.temp, lambda sha: sha == MERGE))
        _, chunks = self.rendered()
        self.assertIn(DONE, ids(chunks))


if __name__ == "__main__":
    unittest.main()
