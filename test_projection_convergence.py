#!/usr/bin/env python3
"""Deterministic source-to-projection receipt regression tests."""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import board_ingest


class ProjectionConvergenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.old_root = board_ingest.ROOT
        self.old_projection = dict(board_ingest.PROJECTION_STATUS)
        board_ingest.ROOT = self.tmp.name
        (self.root / "p").mkdir()

    def tearDown(self):
        board_ingest.ROOT = self.old_root
        board_ingest.PROJECTION_STATUS.clear()
        board_ingest.PROJECTION_STATUS.update(self.old_projection)
        self.tmp.cleanup()

    def write(self, rel, text):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")

    def test_converged_receipt_is_source_stable_and_state_tracks_surface(self):
        self.write("p/b.md", "post b\n")
        self.write("p/a.md", "post a\n")
        self.write("p/a.html", "page a\n")
        self.write("board.html", "board one\n")

        first = board_ingest.write_projection_convergence()
        source_sha = first["source"]["sha256"]
        marker = (
            self.root / "projection" / "converged" /
            board_ingest.PROJECTION_PROTOCOL / (source_sha + ".json")
        )
        state_path = self.root / "projection_state.json"
        marker_bytes = marker.read_bytes()
        first_state = json.loads(state_path.read_text(encoding="utf-8"))

        self.write("board.html", "board two\n")
        second = board_ingest.write_projection_convergence()
        second_state = json.loads(state_path.read_text(encoding="utf-8"))

        self.assertEqual(first["source"], second["source"])
        self.assertEqual(marker.read_bytes(), marker_bytes)
        self.assertNotEqual(first_state["projection"], second_state["projection"])
        self.assertEqual(second_state["pages_deployment"], "UNVERIFIED")

    def test_pending_receipt_is_append_only_for_unconverged_head(self):
        self.write("p/a.md", "post a\n")
        source = board_ingest.write_projection_pending()
        pending = (
            self.root / "projection" / "pending" /
            board_ingest.PROJECTION_PROTOCOL / (source["sha256"] + ".json")
        )
        row = json.loads(pending.read_text(encoding="utf-8"))

        self.assertEqual(row["state"], "PENDING_REBAKE")
        self.assertEqual(row["source"], source)
        self.assertEqual(row["pages_deployment"], "UNVERIFIED")
        self.assertEqual(row["protocol"], board_ingest.PROJECTION_PROTOCOL)

    def test_health_requires_matching_state_surface_and_head_receipt(self):
        self.write("p/a.md", "post a\n")
        self.write("p/a.html", "page a\n")
        self.write("board.html", "board\n")
        board_ingest.write_projection_convergence()

        with mock.patch.object(board_ingest, "_head_has", return_value=True):
            healthy = board_ingest.refresh_projection_status(os.environ.copy())
        self.assertEqual(healthy["state"], "CONVERGED_IN_GIT")

        self.write("p/b.md", "post b\n")
        with mock.patch.object(board_ingest, "_head_has", return_value=False):
            pending = board_ingest.refresh_projection_status(os.environ.copy())
        self.assertEqual(pending["state"], "PENDING_REBAKE")
        self.assertEqual(pending["projection_sha256"], "")


if __name__ == "__main__":
    unittest.main()
