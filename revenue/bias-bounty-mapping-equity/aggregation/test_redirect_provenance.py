from __future__ import annotations

import hashlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import aggregate as a


class _FakeResponse(io.BytesIO):
    def __init__(self, body: bytes, final_url: str) -> None:
        super().__init__(body)
        self._final_url = final_url

    def geturl(self) -> str:
        return self._final_url


def _opener(final_url: str, body: bytes = b"canonical-public-object"):
    def open_one(requested_url: str, timeout: int = 0) -> _FakeResponse:
        if timeout != 300:
            raise AssertionError(f"unexpected timeout: {timeout}")
        return _FakeResponse(body, final_url)

    return open_one


class RedirectIdentityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.uri = a.source_registry("northern-ca")["sample"]

    def test_external_https_redirect_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(a.AggregationError, "public challenge product"):
                a._materialize_one(
                    "sample",
                    self.uri,
                    Path(td),
                    _opener=_opener("https://example.com/public/sample-submission.csv"),
                )

    def test_same_root_different_object_redirect_is_rejected(self) -> None:
        other = a.source_registry("northern-ca")["cbp"]
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(a.AggregationError, "changed canonical source identity"):
                a._materialize_one("sample", self.uri, Path(td), _opener=_opener(other))

    def test_exact_response_url_is_accepted_and_bound_in_generation(self) -> None:
        body = b"exact-response-generation"
        with tempfile.TemporaryDirectory() as td:
            fd, path, generation = a._materialize_one(
                "sample",
                self.uri,
                Path(td),
                _opener=_opener(self.uri, body),
            )
            try:
                self.assertEqual(self.uri, generation["uri"])
                self.assertEqual(self.uri, generation["resolved_url"])
                self.assertEqual(hashlib.sha256(body).hexdigest(), generation["sha256"])
                with open(path, "rb") as retained:
                    self.assertEqual(body, retained.read())
            finally:
                os.close(fd)

    def test_final_receipt_input_generations_include_resolved_url(self) -> None:
        region = "northern-ca"
        public = a.source_registry(region)
        registry = {
            key: f"/proc/self/fd/{100 + index}"
            for index, key in enumerate(public)
        }
        generations = {
            key: {
                "uri": uri,
                "resolved_url": uri,
                "sha256": hashlib.sha256(key.encode("utf-8")).hexdigest(),
                "bytes": 1,
                "generation": "sha256:" + hashlib.sha256(key.encode("utf-8")).hexdigest(),
            }
            for key, uri in public.items()
        }

        class Materialized:
            def __init__(self) -> None:
                self.registry = registry
                self.generations = generations
                self.closed = False

            def close(self) -> None:
                self.closed = True

        materialized = Materialized()
        rows = [
            (f"{index:011d}", *([0.0] * (len(a.OUTPUT_COLUMNS) - 1)))
            for index in range(a.REGIONS[region])
        ]

        class Cursor:
            description = [(name,) for name in a.OUTPUT_COLUMNS]

            def fetchall(self):
                return rows

        class Connection:
            def execute(self, sql: str):
                return Cursor()

            def close(self) -> None:
                pass

        with tempfile.TemporaryDirectory() as td:
            output = Path(td) / "out.csv"
            receipt = Path(td) / "receipt.json"
            with mock.patch.object(a._legacy, "run_preflight", return_value={"ok": True}):
                a.execute_region(
                    region,
                    output,
                    receipt,
                    _materializer=lambda _: materialized,
                    _connector=Connection,
                    _query_builder=lambda _region, _registry: "SELECT 1",
                )
            envelope = json.loads(receipt.read_text(encoding="utf-8"))
            recorded = envelope["payload"]["input_generations"]
            self.assertEqual(self.uri, recorded["sample"]["uri"])
            self.assertEqual(self.uri, recorded["sample"]["resolved_url"])
            self.assertTrue(materialized.closed)


if __name__ == "__main__":
    unittest.main()
