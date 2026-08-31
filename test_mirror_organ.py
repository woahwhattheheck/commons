#!/usr/bin/env python3
"""MIRROR ORGAN proofs: copy manufactures twins; same injection, same state; drift fails closed."""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
GERMLINE = ROOT / "host" / "germline.py"
MIRROR = ROOT / "host" / "mirror_organ.py"


def run(tool: Path, *argv: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(tool), *argv],
        capture_output=True, text=True, timeout=120,
    )


class TestMirrorOrgan(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.d = Path(self.td.name)
        self.src = self.d / "world.bin"
        self.src.write_bytes(bytes(range(256)) * 256)
        self.twins = self.d / "twins"

    def tearDown(self):
        self.td.cleanup()

    def _make_twins(self, n: int = 3) -> subprocess.CompletedProcess:
        return run(MIRROR, "twin", str(self.src), "-n", str(n), "-o", str(self.twins))

    def test_copy_manufactures_identical_twins(self):
        r = self._make_twins(4)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout)["manufactured"], 4)
        v = run(MIRROR, "verify", str(self.twins))
        self.assertEqual(v.returncode, 0, v.stdout + v.stderr)
        self.assertTrue(json.loads(v.stdout)["same_state"])

    def test_same_injection_same_state_every_twin(self):
        self.assertEqual(self._make_twins(3).returncode, 0)
        new = bytearray(self.src.read_bytes())
        new[10_000] = 0xEE
        v2 = self.d / "world-v2.bin"
        v2.write_bytes(bytes(new))
        delta = self.d / "edit.gi"
        self.assertEqual(run(GERMLINE, "diff", str(self.src), str(v2), "-o", str(delta)).returncode, 0)
        r = run(MIRROR, "inject", str(self.twins), str(delta))
        self.assertEqual(r.returncode, 0, r.stderr)
        settled = json.loads(r.stdout)["settled_sha256"]
        import hashlib
        self.assertEqual(settled, hashlib.sha256(v2.read_bytes()).hexdigest())
        v = run(MIRROR, "verify", str(self.twins))
        self.assertEqual(v.returncode, 0)
        for name in ("twin-01.bin", "twin-02.bin", "twin-03.bin"):
            self.assertEqual((self.twins / name).read_bytes(), v2.read_bytes())

    def test_drifted_twin_is_named_and_fails_closed(self):
        self.assertEqual(self._make_twins(3).returncode, 0)
        bad = self.twins / "twin-02.bin"
        bad.write_bytes(b"forged-state")
        v = run(MIRROR, "verify", str(self.twins))
        self.assertEqual(v.returncode, 3)
        report = json.loads(v.stdout)
        self.assertFalse(report["same_state"])
        flagged = [t["twin"] for t in report["twins"] if not t["in_family"]]
        self.assertIn("twin-02.bin", flagged)

    def test_injection_determinism_across_replays(self):
        self.assertEqual(self._make_twins(2).returncode, 0)
        new = self.src.read_bytes() + b"appended-acreage"
        v2 = self.d / "v2.bin"
        v2.write_bytes(new)
        delta = self.d / "grow.gi"
        self.assertEqual(run(GERMLINE, "diff", str(self.src), str(v2), "-o", str(delta)).returncode, 0)
        first = run(MIRROR, "inject", str(self.twins), str(delta))
        self.assertEqual(first.returncode, 0)
        digest_1 = json.loads(first.stdout)["settled_sha256"]
        fresh = self.d / "fresh"
        self.assertEqual(run(MIRROR, "twin", str(self.src), "-n", "2", "-o", str(fresh)).returncode, 0)
        second = run(MIRROR, "inject", str(fresh), str(delta))
        self.assertEqual(json.loads(second.stdout)["settled_sha256"], digest_1)


if __name__ == "__main__":
    unittest.main()
