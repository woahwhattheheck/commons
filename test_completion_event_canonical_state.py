#!/usr/bin/env python3
"""Completion reconciliation follows the canonical issue for every event name."""

from __future__ import annotations

import importlib.util
import os
import unittest
from pathlib import Path
from unittest import mock

MODULE_PATH = Path(
    os.environ.get("BOARD_INGEST_UNDER_TEST", "board_ingest.py")
).resolve()


def load_module():
    name = "board_ingest_completion_event_" + str(abs(hash(str(MODULE_PATH))))
    spec = importlib.util.spec_from_file_location(name, MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load %s" % MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CompletionEventCanonicalStateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.subject = load_module()

    def test_labeled_event_clears_markers_when_canonical_issue_is_open(self):
        subject = self.subject
        canonical = {"number": 16289, "state": "open"}
        with (
            mock.patch.object(subject, "_gh_api", return_value=canonical) as api,
            mock.patch.object(
                subject.completion_projection,
                "remove_markers_for_issue",
                return_value=("op-16289",),
            ) as remove,
        ):
            result = subject._handle_completion_issue_event(
                {"action": "labeled", "issue": {"number": 16289}}
            )
        self.assertEqual(result, 0)
        api.assert_called_once()
        remove.assert_called_once_with(subject.ROOT, 16289)

    def test_closed_event_still_clears_markers_when_canonical_issue_is_open(self):
        subject = self.subject
        canonical = {"number": 16289, "state": "open"}
        with (
            mock.patch.object(subject, "_gh_api", return_value=canonical),
            mock.patch.object(
                subject.completion_projection,
                "remove_markers_for_issue",
                return_value=(),
            ) as remove,
            mock.patch.object(subject, "_completion_marker_for_closed_issue") as marker,
        ):
            result = subject._handle_completion_issue_event(
                {"action": "closed", "issue": {"number": 16289, "state": "closed"}}
            )
        self.assertEqual(result, 0)
        remove.assert_called_once_with(subject.ROOT, 16289)
        marker.assert_not_called()

    def test_reopened_event_follows_completed_canonical_issue(self):
        subject = self.subject
        canonical = {
            "number": 42,
            "state": "closed",
            "state_reason": "completed",
        }
        with (
            mock.patch.object(subject, "_gh_api", return_value=canonical),
            mock.patch.object(
                subject, "_completion_marker_for_closed_issue", return_value=None
            ) as marker,
            mock.patch.object(
                subject.completion_projection, "remove_markers_for_issue"
            ) as remove,
        ):
            result = subject._handle_completion_issue_event(
                {"action": "reopened", "issue": {"number": 42, "state": "open"}}
            )
        self.assertEqual(result, 0)
        remove.assert_not_called()
        marker.assert_called_once_with(canonical)

    def test_edited_event_reads_completed_canonical_issue(self):
        subject = self.subject
        canonical = {
            "number": 42,
            "state": "closed",
            "state_reason": "completed",
        }
        with (
            mock.patch.object(subject, "_gh_api", return_value=canonical),
            mock.patch.object(
                subject, "_completion_marker_for_closed_issue", return_value=None
            ) as marker,
            mock.patch.object(
                subject.completion_projection, "remove_markers_for_issue"
            ) as remove,
        ):
            result = subject._handle_completion_issue_event(
                {"action": "edited", "issue": {"number": 42, "state": "open"}}
            )
        self.assertEqual(result, 0)
        remove.assert_not_called()
        marker.assert_called_once_with(canonical)

    def test_missing_canonical_issue_does_not_clear_markers(self):
        subject = self.subject
        with (
            mock.patch.object(subject, "_gh_api", return_value=None),
            mock.patch.object(
                subject.completion_projection, "remove_markers_for_issue"
            ) as remove,
        ):
            result = subject._handle_completion_issue_event(
                {"action": "labeled", "issue": {"number": 42}}
            )
        self.assertEqual(result, 0)
        remove.assert_not_called()


if __name__ == "__main__":
    unittest.main()
