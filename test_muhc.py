#!/usr/bin/env python3
"""Functional .muhc tests plus same-run audit of the current compress CLIs."""
from __future__ import annotations

import hashlib
import inspect
import io
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

import evolve
import foldpack
import muhc
import stackpack

SEED0 = os.path.join(ROOT, "muhl", "containers", "MUHLNICKEL_DISTRO", "SEED0.mno")
PUBLISHED_PROGRAM = ["TRANSPOSE", "REV_COLS", "XOR_COL", "XOR_COL", "REV_COLS", "ROT4"]


def checker(width, height):
    return [bytearray((x + y) & 1 for x in range(width)) for y in range(height)]


def tailed(width=5, height=5):
    grid = checker(width, height)
    for x in range(width):
        grid[height - 1][x] = 1
    for y in range(height):
        grid[y][width - 1] = 1
    grid[height - 1][width - 1] = 0
    return grid


class TestCalibration(unittest.TestCase):
    def test_same_run_known_present(self):
        for name in (
            "foldpack.py",
            "stackpack.py",
            "evolve.py",
            "test_compress_doors.py",
            "compress_measured.json",
            "muhl/containers/MUHLNICKEL_DISTRO/SEED0.mno",
        ):
            path = os.path.join(ROOT, name)
            self.assertTrue(os.path.isfile(path), path)
        with open(SEED0, "rb") as handle:
            seed = handle.read()
        self.assertEqual(len(seed), 8192)
        self.assertEqual(hashlib.sha256(seed).hexdigest()[:16], "faa70efc328e9b59")


class TestCurrentCliGaps(unittest.TestCase):
    def test_stackpack_run_does_not_decompress_artifact(self):
        src = inspect.getsource(stackpack.run)
        self.assertNotIn("zlib.decompress", src)
        self.assertIn("for idx, v in enumerate(cols)", src)
        self.assertIn("order[table[v]]", src)

    def test_stackpack_prints_ok_after_dropping_tails(self):
        grid = tailed(5, 5)
        buf = io.StringIO()
        old = sys.stdout
        sys.stdout = buf
        try:
            total, ok = stackpack.run(5, 5, grid, 2, 2, 4, "synth")
        finally:
            sys.stdout = old
        self.assertTrue(ok)
        self.assertIn("OK", buf.getvalue())
        self.assertGreater(total, 0)
        covered = [bytes(row[:4]) for row in grid[:4]]
        self.assertNotEqual(bytes(grid[4]), covered[0])
        self.assertEqual([row[4] for row in grid], [1, 1, 1, 1, 0])

    def test_foldpack_rereive_is_in_memory(self):
        src = inspect.getsource(foldpack.main)
        after = src.split("RE-DERIVE", 1)[1]
        self.assertNotIn("zlib.decompress", after)
        self.assertIn("unfold_once(rec, recH, W, recS, mode, odds[f])", after)

    def test_evolve_score_excludes_framing_and_permits_padding_alias(self):
        src = inspect.getsource(evolve.score)
        self.assertNotIn("len(seq)", src)
        self.assertNotIn("sha256", src)
        three = evolve.pack([bytearray([1, 0, 1])])
        eight = evolve.pack([bytearray([1, 0, 1, 0, 0, 0, 0, 0])])
        self.assertEqual(three, eight)
        self.assertEqual(three, b"\xa0")

    def test_compress_doors_tests_are_presence_only(self):
        with open(os.path.join(ROOT, "test_compress_doors.py"), encoding="utf-8") as handle:
            text = handle.read()
        self.assertNotIn("round-trip", text.lower().replace("roundtrip", "round-trip"))
        self.assertNotIn("sha256", text)
        self.assertNotIn("subprocess", text)
        self.assertNotIn("zlib.decompress", text)
        self.assertEqual(text.count("def test_"), 9)


class TestMuhcRoundTrip(unittest.TestCase):
    def test_raw_stack_fold_evolve_exact_sha(self):
        grid = tailed(5, 5)
        bit_len = 25
        for codec, opts in (
            ("raw", {}),
            ("stack", {"tile_w": 2, "tile_h": 2}),
            ("fold", {"folds": 3, "mode": "adjacent"}),
            ("evolve", {"program": ["XOR_COL", "REV_ROWS"], "entropy": "zlib"}),
        ):
            blob = muhc.encode(grid, codec=codec, bit_len=bit_len, **opts)
            header = muhc.decode(blob)
            rec = bytes(muhc.bytes_from_grid(header["grid"], bit_len))
            src = bytes(muhc.bytes_from_grid(grid, bit_len))
            self.assertEqual(rec, src, codec)
            self.assertEqual(header["sha256"], hashlib.sha256(src).hexdigest(), codec)
            self.assertTrue(blob.startswith(b"MUHC"))

    def test_stack_keeps_non_divisible_tails(self):
        grid = tailed(5, 5)
        blob = muhc.encode(grid, codec="stack", tile_w=2, tile_h=2)
        rec = muhc.decode(blob)["grid"]
        self.assertEqual([list(row) for row in rec], [list(row) for row in grid])

    def test_independent_artifact_not_memory_cols(self):
        data = bytes(range(64))
        blob = muhc.encode_bytes(data, 16, codec="stack", tile_w=16, tile_h=1)
        header, payload = muhc.parse_header(blob)
        self.assertEqual(header["codec_name"], "stack_v1")
        self.assertIn("zlib.decompress", inspect.getsource(muhc._stack_decode))
        rec, _hdr = muhc.decode_bytes(blob)
        self.assertEqual(rec, data)
        self.assertIs(payload is blob, False)

    def test_corruption_refused(self):
        blob = bytearray(muhc.encode(checker(8, 8), codec="raw"))
        blob[20] ^= 0xFF
        with self.assertRaises(muhc.MuhcCorrupt):
            muhc.decode(bytes(blob))
        blob = bytearray(muhc.encode(checker(8, 8), codec="stack", tile_w=8, tile_h=1))
        blob[-1] ^= 0x01
        with self.assertRaises(muhc.MuhcCorrupt):
            muhc.decode(bytes(blob))
        with self.assertRaises(muhc.MuhcCorrupt):
            muhc.decode(b"MUHC" + b"\x00" * 20)

    def test_cross_process_decoder(self):
        data = b"muhc-cross-process-fixture-20260825"
        blob = muhc.encode_bytes(data, 8, codec="raw")
        with tempfile.TemporaryDirectory() as tmp:
            src = os.path.join(tmp, "t.muhc")
            dst = os.path.join(tmp, "t.bin")
            with open(src, "wb") as handle:
                handle.write(blob)
            proc = subprocess.run(
                [sys.executable, os.path.join(ROOT, "muhc.py"), "decode", src, dst],
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertIn("sha256", proc.stdout)
            with open(dst, "rb") as handle:
                self.assertEqual(handle.read(), data)

    def test_seed0_file_round_trip_and_ratio_accounting(self):
        with open(SEED0, "rb") as handle:
            data = handle.read()
        blob = muhc.encode_bytes(data, 200, codec="stack", tile_w=200, tile_h=1)
        rec, header = muhc.decode_bytes(blob)
        self.assertEqual(rec, data)
        raw = muhc.encode_bytes(data, 200, codec="raw")
        report = muhc.ratio_report(len(data), blob, muhc.parse_header(raw)[0]["payload_len"])
        self.assertEqual(report["source_b"], 8192)
        self.assertEqual(report["overhead_b"], muhc.HEADER_SIZE + 4)
        self.assertEqual(report["container_b"], report["payload_b"] + report["overhead_b"])
        self.assertGreater(report["container_pct"], report["payload_pct"])

    def test_published_program_does_not_generalize_to_seed0(self):
        with open(SEED0, "rb") as handle:
            data = handle.read()
        rows = muhc.bench_bytes(data, 200, PUBLISHED_PROGRAM)
        self.assertIn("evolve_v1", rows)
        self.assertGreater(rows["evolve_v1"]["payload_b"], rows["raw_zlib"]["payload_b"])
        self.assertLess(rows["zlib_file"]["payload_b"], 2000)

    def test_stackpack_ok_is_not_a_decodable_artifact(self):
        grid = tailed(5, 5)
        buf = io.StringIO()
        old = sys.stdout
        sys.stdout = buf
        try:
            _total, ok = stackpack.run(5, 5, grid, 2, 2, 4, "synth")
        finally:
            sys.stdout = old
        self.assertTrue(ok)
        blob = muhc.encode(grid, codec="stack", tile_w=2, tile_h=2)
        rec = muhc.decode(blob)["grid"]
        self.assertEqual(list(rec[4]), list(grid[4]))


if __name__ == "__main__":
    unittest.main()
