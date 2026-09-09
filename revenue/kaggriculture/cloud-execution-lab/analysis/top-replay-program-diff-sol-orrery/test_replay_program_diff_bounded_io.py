from __future__ import annotations

import gzip
import tempfile
import unittest
from pathlib import Path

import replay_program_diff as rpd


class BoundedInputTests(unittest.TestCase):
    def test_gzip_decompression_limit_is_enforced_incrementally(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "oversized.json.gz"
            path.write_bytes(gzip.compress(b'{"x":"abcdefghijk"}', mtime=0))
            original = rpd.MAX_DECOMPRESSED_BYTES
            rpd.MAX_DECOMPRESSED_BYTES = 10
            try:
                with self.assertRaisesRegex(rpd.ReplayError, "decompressed-size limit"):
                    rpd._read_input(path)
            finally:
                rpd.MAX_DECOMPRESSED_BYTES = original

    def test_invalid_gzip_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "truncated.json.gz"
            path.write_bytes(b"\x1f\x8b\x08\x00")
            with self.assertRaisesRegex(rpd.ReplayError, "invalid gzip stream"):
                rpd._read_input(path)

    def test_plain_input_limit_is_enforced(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "oversized.json"
            path.write_bytes(b'{"x":1}')
            original = rpd.MAX_DECOMPRESSED_BYTES
            rpd.MAX_DECOMPRESSED_BYTES = 4
            try:
                with self.assertRaisesRegex(rpd.ReplayError, "decompressed-size limit"):
                    rpd._read_input(path)
            finally:
                rpd.MAX_DECOMPRESSED_BYTES = original


if __name__ == "__main__":
    unittest.main()
