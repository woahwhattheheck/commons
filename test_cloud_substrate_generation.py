#!/usr/bin/env python3
"""Regression tests for the MUHLCLOUD1 generation verifier."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parent
VERIFY = ROOT / "muhl" / "cloud_substrate" / "verify_generation.py"


def digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


class CloudSubstrateGenerationVerifierTest(unittest.TestCase):
    def make_fixture(self, root: Path) -> tuple[Path, Path, Path]:
        source_bytes = b"abcd"
        source = root / "source.mno"
        source.write_bytes(source_bytes)

        pages_dir = root / "pages"
        pages_dir.mkdir()
        page_payloads = [b"ab", b"cd"]
        page_paths: list[Path] = []
        pages: list[dict[str, object]] = []
        cursor = 0
        for index, payload in enumerate(page_payloads):
            page_path = pages_dir / f"page-{index:04d}.mno.page"
            page_path.write_bytes(payload)
            page_paths.append(page_path)
            pages.append(
                {
                    "index": index,
                    "path": page_path.relative_to(root).as_posix(),
                    "byte_start": cursor,
                    "byte_end_exclusive": cursor + len(payload),
                    "bytes": len(payload),
                    "sha256": digest(payload),
                }
            )
            cursor += len(payload)

        source_sha = digest(source_bytes)
        manifest = {
            "format": "MUHLCLOUD1_GENERATION",
            "generation_id": f"muhlcloud1-{source_sha}",
            "source": {
                "bytes": len(source_bytes),
                "sha256": source_sha,
            },
            "record": {
                "stride_bytes": 1,
            },
            "pages": pages,
        }
        manifest_path = root / "generation.json"
        manifest_path.write_text(
            json.dumps(manifest, indent=2) + "\n",
            encoding="utf-8",
        )
        return manifest_path, source, page_paths[1]

    def run_verifier(self, manifest: Path, source: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(VERIFY),
                "--manifest",
                str(manifest),
                "--source",
                str(source),
            ],
            capture_output=True,
            check=False,
            text=True,
        )

    def test_valid_generation_exits_zero(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            manifest, source, _ = self.make_fixture(Path(temp))
            result = self.run_verifier(manifest, source)

        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads(result.stdout)
        self.assertTrue(receipt["verification_passed"])
        self.assertTrue(receipt["pages_match_declarations"])

    def test_corrupted_page_exits_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            manifest, source, second_page = self.make_fixture(Path(temp))
            second_page.write_bytes(b"cX")
            result = self.run_verifier(manifest, source)

        self.assertEqual(result.returncode, 1, result.stderr)
        receipt = json.loads(result.stdout)
        self.assertFalse(receipt["verification_passed"])
        self.assertFalse(receipt["byte_equal_measured"])
        self.assertFalse(receipt["pages_match_declarations"])


if __name__ == "__main__":
    unittest.main()
