#!/usr/bin/env python3
"""Exact tests for the deterministic MUHC auto organ."""

from __future__ import annotations

import hashlib
import inspect
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "host"))

import muhc
from host import muhc_auto


SEED0 = ROOT / "muhl" / "containers" / "MUHLNICKEL_DISTRO" / "SEED0.mno"


class MuhcAutoOrganTests(unittest.TestCase):
    def test_chosen_artifact_is_exact_verified_minimum(self):
        data = (bytes(range(64)) + b"ABCD" * 16) * 2
        blob, report = muhc_auto.select_bytes(
            data,
            width=32,
            max_depth=1,
            beam_width=3,
            entropies=("zlib",),
        )
        restored, header = muhc.decode_bytes(blob)
        self.assertEqual(restored, data)
        self.assertEqual(header["sha256"], hashlib.sha256(data).hexdigest())
        self.assertEqual(report["state"], "VERIFIED")
        self.assertEqual(report["chosen"]["container_b"], len(blob))
        self.assertEqual(
            report["chosen"]["container_b"],
            min(row["container_b"] for row in report["candidates"]),
        )
        self.assertEqual(
            report["chosen"]["container_sha256"],
            hashlib.sha256(blob).hexdigest(),
        )
        self.assertEqual(
            report["candidate_count"],
            len(report["candidates"]),
        )
        self.assertTrue(report["guarantees"]["complete_container_bytes_counted"])
        self.assertTrue(report["guarantees"]["every_accepted_candidate_decoded"])
        self.assertTrue(report["guarantees"]["every_accepted_candidate_source_sha_matched"])

    def test_search_is_deterministic_and_source_bound(self):
        data = b"muhc-auto-deterministic-fixture-" * 5
        first_blob, first = muhc_auto.select_bytes(
            data,
            width=24,
            max_depth=1,
            beam_width=2,
            entropies=("zlib", "bz2"),
        )
        second_blob, second = muhc_auto.select_bytes(
            data,
            width=24,
            max_depth=1,
            beam_width=2,
            entropies=("zlib", "bz2"),
        )
        self.assertEqual(first_blob, second_blob)
        self.assertEqual(first, second)
        self.assertFalse(first["search"]["persistent_ledger"])
        self.assertEqual(first["source"]["sha256"], hashlib.sha256(data).hexdigest())
        self.assertEqual(
            first["chosen"]["id"],
            min(
                (
                    row["container_b"],
                    row["id"],
                )
                for row in first["candidates"]
            )[1],
        )

    def test_candidate_accounting_is_full_container_accounting(self):
        data = b"\x00\xff" * 97
        blob, report = muhc_auto.select_bytes(
            data,
            width=31,
            max_depth=0,
            beam_width=1,
            entropies=("zlib",),
        )
        parsed, _payload = muhc.parse_header(blob)
        self.assertEqual(parsed["total"], len(blob))
        for row in report["candidates"]:
            self.assertEqual(
                row["container_b"],
                row["payload_b"] + row["overhead_b"],
                row["id"],
            )
            self.assertEqual(row["source_sha256"], report["source"]["sha256"])

    def test_invalid_search_controls_fail_closed(self):
        bad = (
            (b"", 8, 0, 1, ("zlib",)),
            (b"x", 0, 0, 1, ("zlib",)),
            (b"x", 8, -1, 1, ("zlib",)),
            (b"x", 8, muhc_auto.MAX_DEPTH_LIMIT + 1, 1, ("zlib",)),
            (b"x", 8, 0, 0, ("zlib",)),
            (b"x", 8, 0, muhc_auto.MAX_BEAM_LIMIT + 1, ("zlib",)),
            (b"x", 8, 0, 1, ()),
            (b"x", 8, 0, 1, ("invented",)),
        )
        for data, width, depth, beam, entropies in bad:
            with self.subTest(data=data, width=width, depth=depth, beam=beam, entropies=entropies):
                with self.assertRaises(muhc_auto.AutoOrganError):
                    muhc_auto.select_bytes(
                        data,
                        width=width,
                        max_depth=depth,
                        beam_width=beam,
                        entropies=entropies,
                    )

    def test_seed0_smoke_is_real_artifact_not_claim(self):
        data = SEED0.read_bytes()
        self.assertEqual(len(data), 8192)
        blob, report = muhc_auto.select_bytes(
            data,
            width=200,
            max_depth=0,
            beam_width=1,
            entropies=("zlib",),
        )
        restored, header = muhc.decode_bytes(blob)
        self.assertEqual(restored, data)
        self.assertEqual(header["sha256"], hashlib.sha256(data).hexdigest())
        self.assertGreater(report["candidate_count"], 3)
        self.assertEqual(report["chosen"]["container_b"], len(blob))

    def test_cli_emits_decodable_artifact_and_machine_report(self):
        data = b"cli-auto-organ-fixture-" * 7
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "src.bin"
            dst = Path(tmp) / "out.muhc"
            report_path = Path(tmp) / "report.json"
            src.write_bytes(data)
            proc = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "host" / "muhc_auto.py"),
                    "select",
                    str(src),
                    str(dst),
                    "--report",
                    str(report_path),
                    "--width",
                    "32",
                    "--max-depth",
                    "1",
                    "--beam-width",
                    "2",
                    "--entropies",
                    "zlib",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            stdout = json.loads(proc.stdout)
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(stdout, report)
            restored, _header = muhc.decode_bytes(dst.read_bytes())
            self.assertEqual(restored, data)
            self.assertEqual(report["chosen"]["container_b"], dst.stat().st_size)

    def test_implementation_has_no_persistent_or_cross_source_ledger(self):
        source = inspect.getsource(muhc_auto)
        self.assertNotIn("evolve_ledger", source)
        self.assertNotIn("json.dump(", source)
        self.assertNotIn("random.", source)
        self.assertIn('"persistent_ledger": False', source)


if __name__ == "__main__":
    unittest.main()
