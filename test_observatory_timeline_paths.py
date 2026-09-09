"""Regression coverage for all per-event Observatory timeline paths."""
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from protocol.projector import project

NOW = "2026-09-06T23:00:00Z"


def event(event_id: str, paths: list[str], **extra: object) -> dict:
    return {
        "event_id": event_id,
        "kind": "CHECKPOINT",
        "ts": NOW,
        "session_id": "timeline-path-regression",
        "task_id": "multi-file-work",
        "claimed_paths": paths,
        **extra,
    }


class TimelinePathsTest(unittest.TestCase):
    def test_all_paths_are_retained_with_legacy_first_path(self):
        paths = ["src/first.py", "tests/secondary.py", "docs/third.md"]
        row = project([event("paths-multi", paths)], now=NOW)["timeline"][0]
        self.assertEqual(row.get("claimed_paths"), paths)
        self.assertEqual(row["path"], paths[0])

    def test_single_path_remains_compatible(self):
        row = project([event("paths-single", ["src/first.py"])], now=NOW)["timeline"][0]
        self.assertEqual(row.get("claimed_paths"), ["src/first.py"])
        self.assertEqual(row["path"], "src/first.py")

    def test_empty_paths_preserve_unknown_alias(self):
        row = project([event("paths-empty", [])], now=NOW)["timeline"][0]
        self.assertEqual(row.get("claimed_paths"), [])
        self.assertEqual(row["path"], "UNKNOWN")

    def test_paths_belong_to_each_event_not_latest_task_state(self):
        rows = project([
            event("paths-earlier", ["old/a.py", "old/b.py"], ts="2026-09-06T22:58:00Z"),
            event("paths-later", ["new/c.py", "new/d.py"]),
        ], now=NOW)["timeline"]
        by_id = {row["event_id"]: row for row in rows}
        self.assertEqual(by_id["paths-earlier"].get("claimed_paths"), ["old/a.py", "old/b.py"])
        self.assertEqual(by_id["paths-later"].get("claimed_paths"), ["new/c.py", "new/d.py"])

    def test_timeline_paths_are_not_shared_with_other_projections(self):
        source = event("paths-independent", ["src/a.py", "tests/b.py"])
        snap = project([source], now=NOW)
        row = snap["timeline"][0]
        self.assertIsInstance(row.get("claimed_paths"), list)
        row["claimed_paths"].append("not-a-real-event-path")
        self.assertEqual(source["claimed_paths"], ["src/a.py", "tests/b.py"])
        self.assertNotIn("not-a-real-event-path", snap["sessions"][0]["claimed_paths"])
        self.assertNotIn("not-a-real-event-path", snap["work_map"][0]["claimed_paths"])

    def test_projection_is_deterministic_and_does_not_mutate_events(self):
        source = [event("paths-stable", ["src/a.py", "tests/b.py"])]
        original = copy.deepcopy(source)
        self.assertEqual(project(source, now=NOW), project(source, now=NOW))
        self.assertEqual(source, original)


if __name__ == "__main__":
    unittest.main()
