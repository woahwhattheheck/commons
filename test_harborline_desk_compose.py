#!/usr/bin/env python3
"""Harborline composes against TALLY desk helper. Does not steal peer paths."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "host"))

import harborline_desk_compose as compose  # noqa: E402


class HarborlineDeskComposeTest(unittest.TestCase):
    def test_does_not_claim_tally_paths(self) -> None:
        self.assertEqual(
            compose.DO_NOT_OVERWRITE,
            (
                "host/business_pack_desk_instance.py",
                "test_business_pack_desk_instance.py",
                "packs/sidewalk-signal-web-desk-20260902-01",
            ),
        )
        self.assertEqual(compose.PEER_HELPER.name, "business_pack_desk_instance.py")
        self.assertNotEqual(Path(compose.HARBORLINE).name, "sidewalk-signal-web-desk-20260902-01")

    def test_missing_peer_does_not_invent_tally_files(self) -> None:
        missing = Path("/tmp/does-not-exist-business_pack_desk_instance.py")
        result = compose.compose(peer_path=missing, pack_dir=Path("/tmp"))
        self.assertEqual(result["verdict"], "COMPOSE_PEER_MISSING")
        self.assertFalse(result["peer_helper_present"])
        self.assertTrue(result["did_not_overwrite_peer"])
        self.assertTrue(result["did_not_remint_harborline_instance"])
        self.assertEqual(result["shared_helper_single_owner"], "tally")
        self.assertNotIn("337 NO", json.dumps(result))

    def test_live_peer_when_present_classifies_harborline_door(self) -> None:
        if not compose.PEER_HELPER.is_file() or not (compose.HARBORLINE / "door.html").is_file():
            self.skipTest("peer helper or Harborline instance not in this tree")
        result = compose.compose()
        self.assertTrue(result["peer_helper_present"])
        self.assertEqual(result["copy_via_peer"], "COPY_OK")
        self.assertEqual(result["verdict"], "COMPOSE_OK")
        self.assertTrue(result["did_not_overwrite_peer"])


if __name__ == "__main__":
    unittest.main()
