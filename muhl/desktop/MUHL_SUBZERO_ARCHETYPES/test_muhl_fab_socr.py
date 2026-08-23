#!/usr/bin/env python3
"""Structural tests for muhl_fab_socr. Does not walk the organ as inference."""
import hashlib
import os
import struct
import tempfile
import unittest

import muhl_fab_socr as fab


class TestSocrFab(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.blob, cls.meta, cls.stored = fab.fabricate(0)
        fab.verify_physical(cls.blob, cls.meta, cls.stored)

    def test_header_matches_mha_layout(self):
        self.assertEqual(self.blob[:8], b"MUHLSOCR")
        header = struct.unpack_from("<IIIII", self.blob, 8)
        self.assertEqual(header, (15872, 16642, 768, 768, 14))
        self.assertEqual(self.meta["len"], 28 + 768 * 8 + 16642 + 15872 * 25)

    def test_exact_plumb_gate_arithmetic(self):
        self.assertEqual(256 * 62, 15872)
        self.assertEqual(4 * 15 + 1 + 1, 62)
        self.assertEqual(len(self.stored), 15872)
        fa_ops = [fab.OP_XOR, fab.OP_XOR, fab.OP_AND, fab.OP_AND, fab.OP_OR]
        for cell in range(256):
            chunk = self.stored[cell * 62:(cell + 1) * 62]
            adds = chunk[:60]
            self.assertEqual(chunk[60][0], fab.OP_AND)
            self.assertEqual(chunk[61][0], fab.OP_XOR)
            for adder in range(4):
                block = adds[adder * 15:(adder + 1) * 15]
                for fa_i in range(3):
                    ops = [record[0] for record in block[fa_i * 5:(fa_i + 1) * 5]]
                    self.assertEqual(ops, fa_ops)

    def test_one_writer_per_gate_output(self):
        outputs = [record[3] for record in self.stored]
        self.assertEqual(len(outputs), 15872)
        self.assertEqual(len(set(outputs)), 15872)

    def test_declared_depth_matches_gate_dag(self):
        records, roots = fab.build_gates()
        depths = {wire: 0 for wire in range(fab.W_H0 + fab.N_IN)}
        max_depth = 0
        for _op, a, b, out in records:
            self.assertIn(a, depths)
            self.assertIn(b, depths)
            depths[out] = max(depths[a], depths[b]) + 1
            max_depth = max(max_depth, depths[out])
        self.assertEqual(max_depth, 14)
        self.assertEqual(max(depths[root] for root in roots), 14)

    def test_wrap16_lattice_has_four_distinct_neighbours(self):
        self.assertEqual(fab.neighbors(0), (240, 1, 16, 15))
        self.assertEqual(fab.neighbors(15), (255, 0, 31, 14))
        self.assertEqual(fab.neighbors(255), (239, 240, 15, 254))
        for cell in range(256):
            owned = fab.neighbors(cell)
            self.assertEqual(len(set(owned)), 4)
            self.assertNotIn(cell, owned)

    def test_self_clock_height_plane(self):
        self.assertEqual(self.meta["output_addrs"], self.meta["input_addrs"])
        self.assertEqual(len(self.meta["output_addrs"]), 768)
        self.assertEqual(len(set(self.meta["output_addrs"])), 768)

    def test_deterministic_bytes(self):
        blob2, meta2, stored2 = fab.fabricate(0)
        self.assertEqual(self.blob, blob2)
        self.assertEqual(self.stored, stored2)
        self.assertEqual(self.meta["sha256"], meta2["sha256"])
        self.assertEqual(self.meta["sha256"], hashlib.sha256(self.blob).hexdigest())

    def test_dry_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_mno, old_reg, old_dir = fab.MNO_PATH, fab.REG_PATH, fab.EXCERPT_DIR
            fab.EXCERPT_DIR = tmp
            fab.MNO_PATH = os.path.join(tmp, "muhl_socr.mno")
            fab.REG_PATH = os.path.join(tmp, "socr_circuits.json")
            try:
                self.assertEqual(fab.main(["--dry"]), 0)
                self.assertFalse(os.path.exists(fab.MNO_PATH))
                self.assertFalse(os.path.exists(fab.REG_PATH))
            finally:
                fab.MNO_PATH, fab.REG_PATH, fab.EXCERPT_DIR = old_mno, old_reg, old_dir


if __name__ == "__main__":
    unittest.main()
