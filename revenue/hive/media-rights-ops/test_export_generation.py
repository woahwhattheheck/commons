import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

import rights_export as e
import rights_store as s


def manifest():
    return {
        "schema": "content-rights-ops-manifest/v1",
        "assets": [
            {"asset_id": "master-a", "sha256": "a" * 64, "parent_asset_id": None},
            {"asset_id": "cut-a-15s", "sha256": "b" * 64, "parent_asset_id": "master-a"},
        ],
        "grants": [
            {
                "grant_id": "grant-child",
                "asset_id": "cut-a-15s",
                "authority_ref": "owner-normalized/row-1",
                "valid_from": "2026-09-01T00:00:00Z",
                "valid_until": "2026-12-31T23:59:59Z",
                "channels": ["instagram"],
                "territories": ["US"],
            }
        ],
    }


def placement():
    return {
        "request_id": "placement-001",
        "asset_id": "cut-a-15s",
        "channel": "instagram",
        "territory": "US",
        "starts_at": "2026-10-01T12:00:00Z",
        "ends_at": "2026-10-15T12:00:00Z",
    }


class ExportGenerationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.db = self.root / "desk.sqlite3"
        s.import_manifest(self.db, manifest(), "2026-09-15T06:00:00Z")
        result = s.record_placement(self.db, placement(), "2026-09-15T06:01:00Z")
        self.assertEqual(result["status"], "RECORDED")

    def tearDown(self):
        self.tmp.cleanup()

    def test_revoke_cannot_commit_between_snapshot_and_queue_generation(self):
        real_snapshot = e.snapshot
        started = threading.Event()
        finished = threading.Event()
        errors = []
        worker = None

        def revoke_worker():
            started.set()
            try:
                s.revoke_grant(self.db, "grant-child", "2026-10-05T00:00:00Z")
            except Exception as exc:  # pragma: no cover - surfaced below
                errors.append(exc)
            finally:
                finished.set()

        def snapshot_then_race(path):
            nonlocal worker
            result = real_snapshot(path)
            worker = threading.Thread(target=revoke_worker, daemon=True)
            worker.start()
            self.assertTrue(started.wait(2), "writer thread did not start")
            return result

        with mock.patch.object(e, "snapshot", side_effect=snapshot_then_race):
            files = e.export_files(self.db, "2026-10-05T00:00:00Z", 30)

        self.assertIsNotNone(worker)
        worker.join(5)
        self.assertTrue(finished.is_set(), "writer remained blocked after export guard release")
        self.assertEqual(errors, [])

        exported_snapshot = json.loads(files["snapshot.json"])
        exported_queues = json.loads(files["queues.json"])
        self.assertIsNone(exported_snapshot["grants"][0]["revoked_at"])
        self.assertEqual(exported_queues["retraction_review"], [])

        live = s.snapshot(self.db)
        self.assertEqual(live["grants"][0]["revoked_at"], "2026-10-05T00:00:00Z")
        self.assertEqual(s.queues(self.db, "2026-10-05T00:00:00Z", 30)["retraction_review"][0]["request_id"], "placement-001")


if __name__ == "__main__":
    unittest.main(verbosity=2)
