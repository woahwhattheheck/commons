from __future__ import annotations
import datetime as dt
import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from tools.github_content_write_pacemaker.github_write_pacemaker import (
    PacemakerError, PacemakerStore, StoreInvariantError,
    canonical_json, normalize_intent,
)

UTC = dt.timezone.utc


class Clock:
    def __init__(self):
        self.value = dt.datetime(2026, 9, 14, 7, 0, tzinfo=UTC)
    def __call__(self):
        return self.value


class IntegrityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Path(self.tmp.name) / "state.db"
        self.store = PacemakerStore(self.db, clock=Clock())

    def intent(self, key="one", body=None):
        return {"schema": "commons-github-content-write-intent/v2",
                "mutationKey": key, "method": "POST",
                "apiPath": "/provider/path", "description": "test mutation",
                "body": {"value": 1} if body is None else body}

    def test_json_and_receipt_privacy(self):
        integer = normalize_intent(self.intent(body={"value": 1}))
        boolean = normalize_intent(self.intent("bool", body={"value": True}))
        self.assertNotEqual(integer.semantic_sha256, boolean.semantic_sha256)
        with self.assertRaises(PacemakerError):
            canonical_json({"value": float("nan")})
        receipt, _ = self.store.enqueue(
            self.intent("privacy-case", body={"private": "secret-value"}))
        rendered = json.dumps(receipt, sort_keys=True)
        self.assertNotIn("secret-value", rendered)
        self.assertNotIn("test mutation", rendered)

    def test_verify_and_tamper(self):
        self.store.enqueue(self.intent())
        report = self.store.verify()
        self.assertEqual(report["integrity"], "VALID")
        self.assertFalse(report["authority"]["directNetworkClientPresent"])
        self.assertEqual(os.stat(self.db).st_mode & 0o777, 0o600)
        db = sqlite3.connect(self.db)
        db.execute("UPDATE mutations SET body_json=?", (b'{"value":2}',))
        db.commit()
        db.close()
        with self.assertRaises(StoreInvariantError):
            self.store.verify()


if __name__ == "__main__":
    unittest.main()
