#!/usr/bin/env python3
"""GERMLINE proofs: byte-exact manufacture, injection-weight wire, tamper failure."""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HOST = ROOT / "host" / "germline.py"
SPEC = importlib.util.spec_from_file_location("germline", HOST)
assert SPEC and SPEC.loader
germline = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(germline)


def run_cli(*argv: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(HOST), *argv],
        capture_output=True, text=True, timeout=120,
    )


class TestGermlineOps(unittest.TestCase):
    def test_identical_bodies_need_zero_injection(self):
        body = b"commons" * 4096
        self.assertEqual(germline.diff_bytes(body, body), [])

    def test_single_byte_edit_is_one_tiny_op(self):
        old = bytearray(b"a" * 1_000_000)
        new = bytearray(old)
        new[500_000] = ord("b")
        ops = germline.diff_bytes(bytes(old), bytes(new))
        self.assertEqual(len(ops), 1)
        off, old_len, new_hex = ops[0]
        self.assertLessEqual(old_len, 1 << 16)
        manufactured = germline.apply_ops(bytes(old), ops)
        self.assertEqual(manufactured, bytes(new))

    def test_scattered_edits_stay_small(self):
        old = bytearray(b"\x00" * 2_000_000)
        new = bytearray(old)
        for at in (10, 900_000, 1_999_999):
            new[at] = 0xFF
        ops = germline.diff_bytes(bytes(old), bytes(new))
        self.assertEqual(len(ops), 3)
        self.assertEqual(germline.apply_ops(bytes(old), ops), bytes(new))

    def test_append_and_truncate_are_exact(self):
        old = b"seed-body"
        for new in (old + b"-extended-bytes", old[:4], b"", old):
            ops = germline.diff_bytes(old, new)
            self.assertEqual(germline.apply_ops(old, ops), new)

    def test_prefix_suffix_binary_shift(self):
        old = bytes(range(256)) * 512
        new = b"\xAA" + old[:-1]
        ops = germline.diff_bytes(old, new)
        self.assertEqual(germline.apply_ops(old, ops), new)


class TestGermlineCli(unittest.TestCase):
    def test_pack_diff_surface_roundtrip_and_wire_ratio(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            v1 = d / "v1.bin"
            v2 = d / "v2.bin"
            seed = d / "body.germ"
            delta = d / "v2.gi"
            out = d / "manufactured.bin"
            v1.write_bytes(bytes(1_000_000))
            changed = bytearray(v1.read_bytes())
            changed[123_456] = 0x42
            v2.write_bytes(bytes(changed))

            r = run_cli("pack", str(v1), "-o", str(seed))
            self.assertEqual(r.returncode, 0, r.stderr)
            r = run_cli("diff", str(v1), str(v2), "-o", str(delta))
            self.assertEqual(r.returncode, 0, r.stderr)
            receipt = json.loads(r.stdout)
            self.assertLess(receipt["wire_ratio"], 0.01)
            r = run_cli("surface", str(seed), str(delta), "-o", str(out))
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue(json.loads(r.stdout)["byte_exact"])
            self.assertEqual(out.read_bytes(), v2.read_bytes())

    def test_surface_without_injection_manufactures_the_seed_body(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            payload = d / "p.bin"
            seed = d / "p.germ"
            out = d / "out.bin"
            payload.write_bytes(b"the body never moved" * 100)
            self.assertEqual(run_cli("pack", str(payload), "-o", str(seed)).returncode, 0)
            r = run_cli("surface", str(seed), "-o", str(out))
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(out.read_bytes(), payload.read_bytes())

    def test_injection_refuses_wrong_base(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            a = d / "a.bin"
            b = d / "b.bin"
            other = d / "other.bin"
            seed = d / "other.germ"
            delta = d / "ab.gi"
            out = d / "out.bin"
            a.write_bytes(b"alpha" * 1000)
            b.write_bytes(b"omega" * 1000)
            other.write_bytes(b"unrelated" * 1000)
            self.assertEqual(run_cli("pack", str(other), "-o", str(seed)).returncode, 0)
            self.assertEqual(run_cli("diff", str(a), str(b), "-o", str(delta)).returncode, 0)
            r = run_cli("surface", str(seed), str(delta), "-o", str(out))
            self.assertEqual(r.returncode, 3)
            self.assertIn("from_sha256", r.stderr)

    def test_verify_fails_closed_on_tamper(self):
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "body.bin"
            f.write_bytes(b"presence manufactured")
            good = run_cli("verify", str(f), "--expect",
                           "9f1b5c6c" + "0" * 56)
            self.assertEqual(good.returncode, 3)
            import hashlib
            ok = run_cli("verify", str(f), "--expect", hashlib.sha256(f.read_bytes()).hexdigest())
            self.assertEqual(ok.returncode, 0)


if __name__ == "__main__":
    unittest.main()
