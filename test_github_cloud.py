#!/usr/bin/env python3
"""Regression: private GitHub history batches stay immutable without wedging intake."""
from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "host" / "history"))

import github_cloud  # noqa: E402


ACCOUNT = "woahwhattheheck"
BATCH_NAME = "github-woahwhattheheck-notifications-00001.json"
BATCH_KEY = github_cloud.private_path(ACCOUNT, BATCH_NAME)
CHECKPOINT_KEY = github_cloud.private_path(ACCOUNT, "checkpoint.json")
FIRST = b'{"source":"github","coverage":{"page":1},"records":[{"id":"1"}]}'
LIVE = b'{"source":"github","coverage":{"page":1},"records":[{"id":"2"}]}'
OLD_CURSOR = b'{"schema":"github-history-checkpoint-v1","roads":{"notifications":{"pages":0}}}'
NEW_CURSOR = b'{"schema":"github-history-checkpoint-v1","roads":{"notifications":{"pages":1}}}'


class MemoryStore:
    def __init__(self, files=None):
        self.files = dict(files or {})
        self.writes = []

    def read(self, path):
        if path not in self.files:
            return None, None
        return self.files[path], "sha-" + path

    def write(self, path, raw, old_sha=None):
        self.writes.append((path, raw, old_sha))
        self.files[path] = raw


class FakeReader:
    def __init__(self, account, budget, payload=LIVE, cursor=NEW_CURSOR, extra=None):
        self.account = account
        self.budget = budget
        self.payload = payload
        self.cursor = cursor
        self.extra = extra or []
        self.home = github_cloud.collector.ROOT / account
        self.home.mkdir(parents=True, exist_ok=True)

    def run(self):
        (self.home / BATCH_NAME).write_bytes(self.payload)
        for name, raw in self.extra:
            (self.home / name).write_bytes(raw)
        (self.home / "checkpoint.json").write_bytes(self.cursor)
        return {"requests": 1, "queued_details": 0, "queued_repositories": 0, "gaps": 0}


class PutImmutableBatchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="github-cloud-batch-")
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / BATCH_NAME
        self.path.write_bytes(LIVE)
        self.store = MemoryStore()

    def test_missing_private_batch_is_written_once(self):
        with patch.object(github_cloud, "read_private", self.store.read), patch.object(
            github_cloud, "write_private", self.store.write
        ):
            self.assertEqual(github_cloud.put_immutable_batch(ACCOUNT, self.path), "written")
        self.assertEqual(self.store.files[BATCH_KEY], LIVE)
        self.assertEqual(self.store.writes, [(BATCH_KEY, LIVE, None)])

    def test_byte_identical_retry_does_not_rewrite(self):
        self.store.files[BATCH_KEY] = LIVE
        with patch.object(github_cloud, "read_private", self.store.read), patch.object(
            github_cloud, "write_private", self.store.write
        ):
            self.assertEqual(github_cloud.put_immutable_batch(ACCOUNT, self.path), "matched")
        self.assertEqual(self.store.writes, [])
        self.assertEqual(self.path.read_bytes(), LIVE)

    def test_live_page_refetch_keeps_first_snapshot(self):
        self.store.files[BATCH_KEY] = FIRST
        with patch.object(github_cloud, "read_private", self.store.read), patch.object(
            github_cloud, "write_private", self.store.write
        ):
            self.assertEqual(github_cloud.put_immutable_batch(ACCOUNT, self.path), "kept")
        self.assertEqual(self.store.files[BATCH_KEY], FIRST)
        self.assertEqual(self.store.writes, [])
        self.assertEqual(self.path.read_bytes(), FIRST)


class RunContinuationTests(unittest.TestCase):
    def exercise(self, store, reader_factory):
        def make_reader(account, budget):
            return reader_factory(account, budget)

        with patch.object(github_cloud, "read_private", store.read), patch.object(
            github_cloud, "write_private", store.write
        ), patch.object(github_cloud.collector, "Reader", make_reader):
            return github_cloud.run(ACCOUNT)

    def test_predecessor_raises_when_live_bytes_differ(self):
        """Pin the measured hosted failure: compare-and-abort never advances the cursor."""
        store = MemoryStore({BATCH_KEY: FIRST, CHECKPOINT_KEY: OLD_CURSOR})
        raised = []

        def predecessor(account, path):
            raw = path.read_bytes()
            key = github_cloud.private_path(account, path.name)
            existing, _ = store.read(key)
            if existing is None:
                store.write(key, raw)
                return "written"
            if existing != raw:
                raised.append(raw)
                raise RuntimeError("immutable_batch_differs")
            return "matched"

        with patch.object(github_cloud, "put_immutable_batch", predecessor):
            with self.assertRaisesRegex(RuntimeError, "immutable_batch_differs"):
                self.exercise(store, FakeReader)
        self.assertEqual(raised, [LIVE])
        self.assertNotIn(CHECKPOINT_KEY, [path for path, _, _ in store.writes])
        self.assertEqual(store.files[CHECKPOINT_KEY], OLD_CURSOR)
        self.assertEqual(store.files[BATCH_KEY], FIRST)

    def test_live_refetch_keeps_first_batch_and_writes_checkpoint(self):
        store = MemoryStore({BATCH_KEY: FIRST, CHECKPOINT_KEY: OLD_CURSOR})
        result = self.exercise(store, FakeReader)
        self.assertEqual(result["kept"], 1)
        self.assertEqual(result["written"], 0)
        self.assertEqual(result["matched"], 0)
        self.assertEqual(result["batches"], 1)
        self.assertEqual(store.files[BATCH_KEY], FIRST)
        self.assertEqual(store.files[CHECKPOINT_KEY], NEW_CURSOR)
        self.assertEqual(
            store.writes,
            [(CHECKPOINT_KEY, NEW_CURSOR, "sha-" + CHECKPOINT_KEY)],
        )

    def test_new_batch_is_put_before_checkpoint(self):
        store = MemoryStore({CHECKPOINT_KEY: OLD_CURSOR})
        result = self.exercise(store, FakeReader)
        self.assertEqual(result["written"], 1)
        self.assertEqual(result["kept"], 0)
        self.assertEqual(store.files[BATCH_KEY], LIVE)
        self.assertEqual(store.files[CHECKPOINT_KEY], NEW_CURSOR)
        self.assertEqual([path for path, _, _ in store.writes], [BATCH_KEY, CHECKPOINT_KEY])

    def test_second_new_page_writes_while_first_name_stays(self):
        extra_name = "github-woahwhattheheck-notifications-00002.json"
        extra_key = github_cloud.private_path(ACCOUNT, extra_name)
        extra = b'{"source":"github","coverage":{"page":2},"records":[{"id":"9"}]}'
        store = MemoryStore({BATCH_KEY: FIRST, CHECKPOINT_KEY: OLD_CURSOR})

        def factory(account, budget):
            return FakeReader(account, budget, extra=[(extra_name, extra)])

        result = self.exercise(store, factory)
        self.assertEqual(result["kept"], 1)
        self.assertEqual(result["written"], 1)
        self.assertEqual(store.files[BATCH_KEY], FIRST)
        self.assertEqual(store.files[extra_key], extra)
        self.assertEqual(store.files[CHECKPOINT_KEY], NEW_CURSOR)


class CollectEmitTests(unittest.TestCase):
    def test_emit_does_not_replace_an_existing_local_batch(self):
        import github_collect

        with tempfile.TemporaryDirectory(prefix="github-collect-emit-") as temporary:
            github_collect.ROOT = Path(temporary) / "github"
            home = github_collect.ROOT / ACCOUNT
            home.mkdir(parents=True)
            target = home / "github-woahwhattheheck-notifications-00001.json"
            target.write_bytes(FIRST)
            with patch.object(github_collect, "token_for", return_value="synthetic-token"):
                reader = github_collect.Reader(ACCOUNT, budget=1)
            out = reader.emit("notifications", "00001", [{"id": "live"}], {"count": 1})
            self.assertEqual(Path(out), target)
            self.assertEqual(target.read_bytes(), FIRST)


if __name__ == "__main__":
    unittest.main()
