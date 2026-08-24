#!/usr/bin/env python3
"""Structural tests for muhl_fab_chimera_immn_hdvs. Does not evaluate the organ."""
import hashlib
import os
import struct
import tempfile
import unittest

import muhl_fab_chimera_immn_hdvs as fab


class TestChimeraImmnHdvsFab(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.blob, cls.meta, cls.stored = fab.fabricate(0)
        fab.verify_physical(cls.blob, cls.meta, cls.stored)

    def test_header(self):
        self.assertEqual(self.blob[:8], b"MUHLCHIH")
        ng, nw, ni, no, dp = struct.unpack_from("<IIIII", self.blob, 8)
        self.assertEqual((ng, nw, ni, no, dp), (20, 32, 10, 10, 2))
        self.assertEqual(self.meta["len"], 28 + 10 * 8 + 32 + 20 * 25)

    def test_one_writer_per_out(self):
        outs = [gate[3] for gate in self.stored]
        self.assertEqual(len(outs), 20)
        self.assertEqual(len(set(outs)), 20)

    def test_not_not_buffers(self):
        self.assertEqual([gate[0] for gate in self.stored], [fab.OP_NOT] * 20)
        self.assertEqual(self.meta["input_addrs"], self.meta["output_addrs"])

    def test_dest_from_file(self):
        dests = self.meta["dests"]
        self.assertEqual(dests["src_organ"], "muhl_immn")
        self.assertEqual(dests["dst_organ"], "muhl_hdvs")
        self.assertEqual(dests["src_addrs"], list(range(70, 80)))
        self.assertEqual(dests["dst_addrs"][0], 8222)
        self.assertEqual(len(dests["dst_addrs"]), 10)
        self.assertEqual(len(dests["immn_sha256"]), 64)
        self.assertEqual(len(dests["hdvs_sha256"]), 64)

    def test_deterministic(self):
        blob2, meta2, _ = fab.fabricate(0)
        self.assertEqual(self.blob, blob2)
        self.assertEqual(self.meta["sha256"], meta2["sha256"])
        self.assertEqual(self.meta["sha256"], hashlib.sha256(self.blob).hexdigest())

    def test_dry_does_not_write(self):
        here = os.path.dirname(os.path.abspath(fab.__file__))
        with tempfile.TemporaryDirectory() as tmp:
            old_mno, old_reg = fab.MNO_PATH, fab.REG_PATH
            fab.MNO_PATH = os.path.join(tmp, "muhl_chimera_immn_hdvs.mno")
            fab.REG_PATH = os.path.join(tmp, "chih_circuits.json")
            try:
                self.assertEqual(fab.main(["--dry"]), 0)
                self.assertFalse(os.path.exists(fab.MNO_PATH))
                self.assertFalse(os.path.exists(fab.REG_PATH))
            finally:
                fab.MNO_PATH, fab.REG_PATH = old_mno, old_reg
        self.assertTrue(os.path.isdir(here))


if __name__ == "__main__":
    unittest.main()
