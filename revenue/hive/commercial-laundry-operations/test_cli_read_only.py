from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from laundry_desk import LaundryDesk


HERE = Path(__file__).resolve().parent
CLI = HERE / "cli.py"


class ReadOnlyCliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.db = self.root / "desk.sqlite3"
        desk = LaundryDesk(self.db)
        created = desk.add_customer("op-customer", "cust-alpha", "Alpha Laundry Account")
        self.assertFalse(created.replayed)

    def tearDown(self):
        self.tmp.cleanup()

    def run_cli(self, database: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(CLI), str(database), *args],
            cwd=str(HERE),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def test_missing_database_does_not_create_parent_or_database(self):
        missing = self.root / "must-not-exist" / "nested" / "desk.sqlite3"
        self.assertFalse(missing.parent.exists())
        result = self.run_cli(missing, "integrity")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(missing.exists())
        self.assertFalse(missing.parent.exists())

    def test_incomplete_database_is_not_initialized_or_migrated(self):
        incomplete = self.root / "incomplete.sqlite3"
        conn = sqlite3.connect(incomplete)
        conn.execute("CREATE TABLE sentinel(value TEXT NOT NULL)")
        conn.execute("INSERT INTO sentinel(value) VALUES ('keep')")
        conn.commit()
        conn.close()
        before = incomplete.read_bytes()

        result = self.run_cli(incomplete, "integrity")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(incomplete.read_bytes(), before)

        conn = sqlite3.connect(f"file:{incomplete.resolve().as_posix()}?mode=ro", uri=True)
        names = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        value = conn.execute("SELECT value FROM sentinel").fetchone()[0]
        conn.close()
        self.assertEqual(names, {"sentinel"})
        self.assertEqual(value, "keep")

    def test_snapshot_and_integrity_leave_source_database_byte_identical(self):
        before = self.db.read_bytes()

        snapshot = self.run_cli(self.db, "customer-snapshot", "cust-alpha")
        self.assertEqual(snapshot.returncode, 0, snapshot.stderr)
        payload = json.loads(snapshot.stdout)
        self.assertEqual(payload["customer_id"], "cust-alpha")
        self.assertTrue(all(value is False for value in payload["authority"].values()))
        self.assertEqual(self.db.read_bytes(), before)

        integrity = self.run_cli(self.db, "integrity")
        self.assertEqual(integrity.returncode, 0, integrity.stderr)
        proof = json.loads(integrity.stdout)
        self.assertEqual(proof["status"], "PASS")
        self.assertEqual(self.db.read_bytes(), before)

    def test_export_writes_only_requested_handoff_bundle_not_source_database(self):
        before = self.db.read_bytes()
        out = self.root / "handoff"

        result = self.run_cli(self.db, "export-customer", "cust-alpha", str(out))
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        created = {Path(path) for path in payload["created"].values()}
        self.assertEqual({path.suffix for path in created}, {".json", ".csv", ".md"})
        self.assertEqual(set(out.iterdir()), created)
        self.assertEqual(self.db.read_bytes(), before)
        self.assertTrue(all(value is False for value in payload["authority"].values()))

    def test_public_read_only_handle_fails_closed_on_mutation(self):
        desk = LaundryDesk.open_read_only(self.db)
        before = self.db.read_bytes()
        with self.assertRaises(sqlite3.OperationalError):
            desk.add_customer("op-should-fail", "cust-beta", "Beta")
        self.assertEqual(self.db.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
