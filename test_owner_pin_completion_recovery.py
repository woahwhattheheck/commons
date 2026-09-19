"""Completion must not be resurrected by owner-pin's stale-recent input.

The production module is imported normally. Synthetic records exercise both
entry roads: candidate rescue from posts.json and carry-forward from recent.json.
"""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import owner_pin


DONE = "COMPLETION-M7R4-DONE-20260918"
OPEN = "COMPLETION-M7R4-OPEN-20260918"
OWNER = "BRYCE-COMPLETION-M7R4-20260918"


def row(ident, **changes):
    value = {
        "id": ident, "from": "UNSEATED", "to": "TABLE",
        "ts": "2026-09-18T12:00:00Z", "body": "retained history for " + ident,
    }
    value.update(changes)
    return value


def ids(rows):
    return [value["id"] for value in rows]


class OwnerPinCompletionRecoveryTests(unittest.TestCase):
    def test_completed_post_is_not_rescued_into_empty_recent(self):
        posts = [row(DONE, completed="1"), row(OPEN)]
        self.assertEqual([OPEN], ids(owner_pin.pin_recent(posts, [])))

    def test_completed_post_removes_stale_recent_without_completion_field(self):
        posts = [row(DONE, completed="1"), row(OPEN)]
        recent = [row(DONE), row(OPEN)]
        self.assertEqual([OPEN], ids(owner_pin.pin_recent(posts, recent)))

    def test_completion_on_recent_itself_is_not_carried_forward(self):
        recent = [row(DONE, completed="1"), row(OPEN)]
        self.assertEqual([OPEN], ids(owner_pin.pin_recent([], recent)))

    def test_reopened_canonical_post_is_rescued_again(self):
        self.assertEqual([], owner_pin.pin_recent([row(DONE, completed="1")], []))
        self.assertEqual([DONE], ids(owner_pin.pin_recent([row(DONE)], [])))

    def test_reopened_canonical_post_replaces_old_completed_recent_generation(self):
        reopened = row(DONE, body="open again")
        output = owner_pin.pin_recent([reopened], [row(DONE, completed="1")])
        self.assertEqual([DONE], ids(output))
        self.assertEqual("open again", output[0]["body"])

    def test_owner_label_does_not_rescue_completed_work(self):
        posts = [row(DONE, **{"from": "BRYCE", "completed": "1"}), row(OPEN)]
        output = owner_pin.pin_recent(posts, [row(DONE, **{"from": "BRYCE"})])
        self.assertEqual([OPEN], ids(output))

    def test_ordinary_owner_pin_survives_completion_filter(self):
        posts = [row(DONE, completed="1"), row(OPEN), row(OWNER, **{"from": "BRYCE"})]
        output = owner_pin.pin_recent(posts, [row(DONE), row(OPEN)])
        self.assertEqual(OWNER, output[0]["id"])
        self.assertEqual({OWNER, OPEN}, set(ids(output)))

    def test_unknown_recent_record_is_not_inferred_complete(self):
        unknown = row("COMPLETION-M7R4-UNKNOWN-20260918")
        output = owner_pin.pin_recent([row(DONE, completed="1")], [unknown])
        self.assertEqual([unknown["id"]], ids(output))

    def test_inputs_and_historical_bodies_are_not_mutated(self):
        posts = [row(DONE, completed="1"), row(OPEN)]
        recent = [row(DONE), row(OPEN)]
        original = copy.deepcopy((posts, recent))
        owner_pin.pin_recent(posts, recent)
        self.assertEqual(original, (posts, recent))
        self.assertEqual("retained history for " + DONE, posts[0]["body"])

    def test_completion_filter_is_idempotent(self):
        posts = [row(DONE, completed="1"), row(OPEN)]
        first = owner_pin.pin_recent(posts, [row(DONE), row(OPEN)])
        self.assertEqual(first, owner_pin.pin_recent(posts, first))
        self.assertNotIn(DONE, ids(first))

    def test_explicit_noncompleted_row_remains_eligible(self):
        self.assertEqual([OPEN], ids(owner_pin.pin_recent([row(OPEN, completed="0")], [])))

    def test_actual_file_entrypoint_preserves_posts_and_removes_stale_recent(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            posts = root / "posts.json"
            recent = root / "recent.json"
            posts.write_text(json.dumps([row(DONE, completed="1"), row(OPEN)]), encoding="utf-8")
            recent.write_text(json.dumps([row(DONE), row(OPEN)]), encoding="utf-8")
            retained = posts.read_bytes()
            with patch.object(owner_pin, "ROOT", temp):
                self.assertEqual(0, owner_pin.main())
                self.assertEqual(0, owner_pin.main())
            self.assertEqual(retained, posts.read_bytes())
            self.assertEqual([OPEN], ids(json.loads(recent.read_text(encoding="utf-8"))))


if __name__ == "__main__":
    unittest.main()
