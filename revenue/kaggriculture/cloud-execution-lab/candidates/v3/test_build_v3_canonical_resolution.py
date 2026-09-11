#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Focused fail-closed contracts for build_v3 canonical archive resolution."""
from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import build_v3


class CanonicalArchiveResolutionTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.live = self.root / "titan-current.tar.gz"
        self.historical = self.root / "historical"
        self.historical.mkdir()
        self.good = b"manifest-pinned-canonical"
        self.bad = b"newer-incompatible-live"
        self.expected = hashlib.sha256(self.good).hexdigest()
        self.manifest = {"base": {"sha256": self.expected}}

    def tearDown(self):
        self.tmp.cleanup()

    def patches(self):
        return (
            mock.patch.object(build_v3, "CANON", self.live),
            mock.patch.object(build_v3, "HISTORICAL", self.historical),
            mock.patch.object(build_v3, "manifest", return_value=self.manifest),
        )

    def historical_path(self):
        return self.historical / ("titan-%s.tar.gz" % self.expected)

    def test_matching_live_archive_is_preferred(self):
        self.live.write_bytes(self.good)
        with self.patches()[0], self.patches()[1], self.patches()[2]:
            path, data = build_v3.resolve_canonical_archive()
        self.assertEqual(path, self.live)
        self.assertEqual(data, self.good)
        self.assertFalse(self.historical_path().exists())

    def test_mismatched_live_falls_back_to_exact_historical_digest(self):
        self.live.write_bytes(self.bad)
        self.historical_path().write_bytes(self.good)
        with self.patches()[0], self.patches()[1], self.patches()[2]:
            path, data = build_v3.resolve_canonical_archive()
        self.assertEqual(path, self.historical_path())
        self.assertEqual(data, self.good)

    def test_missing_historical_fails_when_live_does_not_match(self):
        self.live.write_bytes(self.bad)
        with self.patches()[0], self.patches()[1], self.patches()[2]:
            with self.assertRaises(FileNotFoundError):
                build_v3.resolve_canonical_archive()

    def test_wrong_historical_digest_fails_closed(self):
        self.live.write_bytes(self.bad)
        self.historical_path().write_bytes(b"wrong-historical-bytes")
        with self.patches()[0], self.patches()[1], self.patches()[2]:
            with self.assertRaises(AssertionError):
                build_v3.resolve_canonical_archive()

    def test_explicit_archive_never_falls_back(self):
        explicit = self.root / "explicit.tar.gz"
        explicit.write_bytes(self.bad)
        self.historical_path().write_bytes(self.good)
        with self.patches()[0], self.patches()[1], self.patches()[2]:
            with self.assertRaises(AssertionError):
                build_v3.resolve_canonical_archive(explicit)

    def test_explicit_matching_archive_is_accepted(self):
        explicit = self.root / "explicit.tar.gz"
        explicit.write_bytes(self.good)
        self.live.write_bytes(self.bad)
        with self.patches()[0], self.patches()[1], self.patches()[2]:
            path, data = build_v3.resolve_canonical_archive(explicit)
        self.assertEqual(path, explicit)
        self.assertEqual(data, self.good)


if __name__ == "__main__":
    unittest.main()
