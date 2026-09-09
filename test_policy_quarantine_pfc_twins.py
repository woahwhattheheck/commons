"""Regression coverage for the PR #7752 policy quarantine.

The three canonical fabrication sources remain reviewable under infra/host.
Their byte-exact copies must not re-enter the activated host runtime closure
because muhlnickel_spec_guard rejected those copies as host compute.
"""

from __future__ import annotations

import hashlib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
QUARANTINED_BLOBS = {
    "pfc_verilog.py": "d470a52d9f7fbebff34eb8b1608fa89e2b6af06a",
    "pfc_wire.py": "fa0a6b3dbbd85d4d1af2de0dc066ef05cb90e474",
    "pfc_writeout_external.py": "f2e1794a1672ef6d8ed60ade602d667a5a151461",
}


def git_blob_sha(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


class PolicyQuarantinePfcTwinsTests(unittest.TestCase):
    def test_rejected_twins_stay_outside_activated_host(self) -> None:
        for name in QUARANTINED_BLOBS:
            with self.subTest(name=name):
                self.assertFalse((ROOT / "host" / name).exists())

    def test_canonical_sources_remain_byte_exact(self) -> None:
        for name, expected_blob in QUARANTINED_BLOBS.items():
            with self.subTest(name=name):
                source = ROOT / "infra" / "host" / name
                self.assertTrue(source.is_file())
                self.assertEqual(git_blob_sha(source.read_bytes()), expected_blob)


if __name__ == "__main__":
    unittest.main()
