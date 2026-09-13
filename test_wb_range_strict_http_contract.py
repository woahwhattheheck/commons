#!/usr/bin/env python3
"""Hermetic transport-contract tests for host.wb_range.RangeReader."""

from __future__ import annotations

import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from host import wb_range


class _FakeResponse:
    def __init__(self, *, body: bytes, status: int = 206,
                 content_range: str = "bytes 2-5/10",
                 content_encoding: str | None = None,
                 url: str = "https://example.test/model.bin"):
        self._stream = io.BytesIO(body)
        self.status = status
        self.headers = {"Content-Range": content_range}
        if content_encoding is not None:
            self.headers["Content-Encoding"] = content_encoding
        self._url = url

    def read(self, amount: int = -1) -> bytes:
        return self._stream.read(amount)

    def getcode(self) -> int:
        return self.status

    def geturl(self) -> str:
        return self._url

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class StrictHttpRangeContractTests(unittest.TestCase):
    def _reader(self, root: Path, url: str = "https://example.test/model.bin"):
        return wb_range.RangeReader(url, root / "cache")

    def _assert_cache_empty(self, reader: wb_range.RangeReader) -> None:
        self.assertFalse(reader.manifest_path.exists())
        self.assertEqual([], list(reader.chunks_dir.iterdir()))
        self.assertEqual({}, reader.manifest["entries"])

    def _read_with(self, reader: wb_range.RangeReader, response: _FakeResponse,
                   *, offset: int = 2, length: int = 4) -> bytes:
        with mock.patch.object(wb_range.urllib.request, "urlopen",
                               return_value=response):
            return reader.read(offset, length)

    def test_valid_206_exact_interval_is_cached(self):
        with tempfile.TemporaryDirectory() as tmp:
            reader = self._reader(Path(tmp))
            data = self._read_with(
                reader,
                _FakeResponse(body=b"cdef", content_range="bytes 2-5/10"),
            )
            self.assertEqual(b"cdef", data)
            self.assertTrue(reader.manifest_path.is_file())
            self.assertEqual(1, len(reader.manifest["entries"]))
            self.assertEqual(1, len(list(reader.chunks_dir.iterdir())))

    def test_http_200_fallback_is_rejected_without_cache_publication(self):
        with tempfile.TemporaryDirectory() as tmp:
            reader = self._reader(Path(tmp))
            with self.assertRaisesRegex(wb_range.WbRangeError,
                                        "HTTP status 200"):
                self._read_with(
                    reader,
                    _FakeResponse(body=b"abcdefghij", status=200,
                                  content_range=""),
                )
            self._assert_cache_empty(reader)

    def test_wrong_206_interval_is_rejected_without_cache_publication(self):
        with tempfile.TemporaryDirectory() as tmp:
            reader = self._reader(Path(tmp))
            with self.assertRaisesRegex(wb_range.WbRangeError,
                                        "Content-Range"):
                self._read_with(
                    reader,
                    _FakeResponse(body=b"abcd",
                                  content_range="bytes 0-3/10"),
                )
            self._assert_cache_empty(reader)

    def test_non_identity_content_encoding_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            reader = self._reader(Path(tmp))
            with self.assertRaisesRegex(wb_range.WbRangeError,
                                        "Content-Encoding"):
                self._read_with(
                    reader,
                    _FakeResponse(body=b"cdef", content_encoding="gzip"),
                )
            self._assert_cache_empty(reader)

    def test_short_and_overlong_bodies_are_rejected(self):
        for body in (b"cde", b"cdefX"):
            with self.subTest(body=body), tempfile.TemporaryDirectory() as tmp:
                reader = self._reader(Path(tmp))
                with self.assertRaisesRegex(wb_range.WbRangeError,
                                            "range body"):
                    self._read_with(
                        reader,
                        _FakeResponse(body=body,
                                      content_range="bytes 2-5/10"),
                    )
                self._assert_cache_empty(reader)

    def test_https_to_http_redirect_is_rejected_even_for_localhost(self):
        with tempfile.TemporaryDirectory() as tmp:
            reader = self._reader(Path(tmp))
            with self.assertRaisesRegex(wb_range.WbRangeError,
                                        "HTTPS downgrade"):
                self._read_with(
                    reader,
                    _FakeResponse(body=b"cdef",
                                  content_range="bytes 2-5/10",
                                  url="http://127.0.0.1:8765/model.bin"),
                )
            self._assert_cache_empty(reader)

    def test_plain_http_rehearsal_is_limited_to_loopback_hosts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for url in (
                "http://127.0.0.1:8765/model.bin",
                "http://localhost:8765/model.bin",
                "http://[::1]:8765/model.bin",
            ):
                with self.subTest(url=url):
                    reader = self._reader(root / str(abs(hash(url))), url=url)
                    response = _FakeResponse(
                        body=b"cdef", content_range="bytes 2-5/10", url=url)
                    self.assertEqual(b"cdef", self._read_with(reader, response))
            with self.assertRaisesRegex(wb_range.WbRangeError,
                                        "localhost rehearsal"):
                self._reader(root / "bad", url="http://localhost.evil/model.bin")

    def test_remote_size_uses_the_same_strict_response_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            reader = self._reader(Path(tmp))
            good = _FakeResponse(body=b"a", content_range="bytes 0-0/10")
            with mock.patch.object(wb_range.urllib.request, "urlopen",
                                   return_value=good):
                self.assertEqual(10, reader.remote_size())

            bad_status = _FakeResponse(body=b"a", status=200,
                                       content_range="bytes 0-0/10")
            with mock.patch.object(wb_range.urllib.request, "urlopen",
                                   return_value=bad_status):
                with self.assertRaisesRegex(wb_range.WbRangeError,
                                            "HTTP status 200"):
                    reader.remote_size()

            wrong_interval = _FakeResponse(body=b"a",
                                           content_range="bytes 1-1/10")
            with mock.patch.object(wb_range.urllib.request, "urlopen",
                                   return_value=wrong_interval):
                with self.assertRaisesRegex(wb_range.WbRangeError,
                                            "Content-Range"):
                    reader.remote_size()

            encoded = _FakeResponse(body=b"a", content_range="bytes 0-0/10",
                                    content_encoding="gzip")
            with mock.patch.object(wb_range.urllib.request, "urlopen",
                                   return_value=encoded):
                with self.assertRaisesRegex(wb_range.WbRangeError,
                                            "Content-Encoding"):
                    reader.remote_size()

            overlong = _FakeResponse(body=b"ab", content_range="bytes 0-0/10")
            with mock.patch.object(wb_range.urllib.request, "urlopen",
                                   return_value=overlong):
                with self.assertRaisesRegex(wb_range.WbRangeError,
                                            "range body"):
                    reader.remote_size()


if __name__ == "__main__":
    unittest.main()
