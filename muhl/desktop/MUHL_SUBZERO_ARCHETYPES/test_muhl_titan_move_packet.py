#!/usr/bin/env python3
"""Structural tests for the journaled titan MOVE packet. No titan write."""
import os
import tempfile
import unittest

import muhl_titan_move_packet as pkt


class TestTitanMovePacket(unittest.TestCase):
    def test_every_sidecar_row_has_matching_excerpt(self):
        packet = pkt.build_packet()
        self.assertGreaterEqual(packet["count"], 12)
        self.assertEqual(packet["titan"], "NOT_WRITTEN")
        self.assertEqual(len(packet["organs"]), packet["count"])
        names = [row["name"] for row in packet["organs"]]
        self.assertEqual(len(names), len(set(names)))
        for row in packet["organs"]:
            self.assertEqual(row["titan"], "NOT_WRITTEN")
            self.assertEqual(row["offset"], 0)
            self.assertIn("OWNER_LOCAL_ALLOCATOR", row["requested_offset_band"])
            self.assertTrue(row["path"].startswith("excerpts/20260823/"))
            self.assertEqual(len(row["sha256"]), 64)

    def test_dry_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            old = pkt.PACKET_PATH
            pkt.PACKET_PATH = os.path.join(tmp, "titan_move_packet.json")
            try:
                self.assertEqual(pkt.main(["--dry"]), 0)
                self.assertFalse(os.path.exists(pkt.PACKET_PATH))
            finally:
                pkt.PACKET_PATH = old


if __name__ == "__main__":
    unittest.main()
