#!/usr/bin/env python3
"""Named leftover 404s from spy-deferred-20260819-01 / goat / grok-build.

Byte-identical copies of files that already lived under muhl/, plus the missing
image-drop.html door and FABLE's failed.html sweep line. Do not remint those ids.
PEER_PACKET in-repo is 3333 B after the living 337-NO closer was stripped; later
ground-only sections may extend that exact source prefix without reminting it.
"""
from __future__ import annotations

import hashlib
import os
import unittest


HERE = os.path.dirname(os.path.abspath(__file__))


def read(name):
    with open(os.path.join(HERE, name), "rb") as f:
        return f.read()


class DeferredLeftovers(unittest.TestCase):
    def test_byte_identical_copies(self):
        pairs = (
            ("muhl/lda-docs/START_HERE.md", "lda/START_HERE.md", 13136),
            ("muhl/lda-docs/NEW_SESSION_PROMPT.md", "lda/NEW_SESSION_PROMPT.md", 19888),
            ("muhl/docs/KEEPCURRENTALLTESTS.md", "lda/KEEPCURRENTALLTESTS.md", 14395),
            ("muhl/docs/TEST_BATTERY_INDEX.md", "ground/TEST_BATTERY_INDEX.md", 11187),
        )
        for src, dest, size in pairs:
            a = read(src)
            b = read(dest)
            self.assertEqual(len(a), size, src)
            self.assertEqual(a, b, dest + " must be an exact copy of " + src)
            self.assertEqual(hashlib.sha256(a).hexdigest(), hashlib.sha256(b).hexdigest())

    def test_peer_packet_preserves_source_before_live_cash_extension(self):
        source = read("muhl/docs/PEER_PACKET_20260819.md")
        ground = read("ground/PEER_PACKET_20260819.md")
        self.assertEqual(len(source), 3333)
        self.assertTrue(ground.startswith(source))
        extension = ground[len(source):]
        self.assertTrue(extension.startswith(b"\n## Live cash\n"))
        self.assertIn(b"spy-ground-batch-live-cash-20260905-24", extension)
        self.assertNotIn(b"337 NO", source)
        self.assertNotIn(b"337 NO", ground)

    def test_test_battery_index_hash(self):
        digest = hashlib.sha256(read("ground/TEST_BATTERY_INDEX.md")).hexdigest()
        self.assertTrue(digest.startswith("fd7d0a54e395"))

    def test_image_drop_door(self):
        html = read("image-drop.html").decode("utf-8")
        self.assertIn("drop: shots/", html)
        self.assertIn("encoding: base64", html)
        self.assertIn("DROP.md", html)
        self.assertIn("file_drop.py", html)
        self.assertIn("spy-deferred-20260819-01", html)
        self.assertIn("FileReader", html)
        self.assertIn("readAsDataURL", html)
        self.assertNotIn("woahwhattheheck-commons-board", html)
        self.assertNotIn('method: "POST"', html)
        self.assertNotIn("labels=board", html)
        boards = read("boards.html").decode("utf-8")
        self.assertIn('href="./image-drop.html"', boards)
        hub = read("hub_pages.py").decode("utf-8")
        self.assertIn('href="./image-drop.html"', hub)
        shots = read("shots.html").decode("utf-8")
        self.assertIn("image-drop.html", shots)

    def test_failed_sweep_line(self):
        html = read("failed.html").decode("utf-8")
        self.assertIn("Swept issues carry a receipt comment", html)
        self.assertIn("no receipt + no page = tell the table", html)
        self.assertIn("fable-requests-sweep-pagination-20260819-01", html)


if __name__ == "__main__":
    raise SystemExit(unittest.main())
