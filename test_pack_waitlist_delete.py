#!/usr/bin/env python3
"""Waitlist CCPA delete leftover. Does not steal waitlist or thanks doors."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "host"))

import pack_waitlist_delete as erase  # noqa: E402


SIGNUP = {
    "kind": "signup",
    "email": "person@example.com",
    "tier": "desk",
    "state": "IN",
    "consent": True,
    "ccpa_do_not_sell": False,
}


class WaitlistDeleteTest(unittest.TestCase):
    def test_does_not_claim_peer_doors(self) -> None:
        self.assertIn("packs/waitlist.html", erase.DO_NOT_OVERWRITE)
        self.assertIn("host/pack_waitlist.py", erase.DO_NOT_OVERWRITE)
        self.assertIn("host/pack_waitlist_pixel_gate.py", erase.DO_NOT_OVERWRITE)
        self.assertIn("packs/thanks.html", erase.DO_NOT_OVERWRITE)
        self.assertIn("packs/desk-website-service-20260902-01/door.html", erase.DO_NOT_OVERWRITE)
        self.assertIn("packs/lotribbon-greetings-20260902-01", erase.DO_NOT_OVERWRITE)
        self.assertIn("host/pack_creative_brief.py", erase.DO_NOT_OVERWRITE)

    def test_missing_helper_does_not_invent_files(self) -> None:
        result = erase.delete(
            Path("/tmp/missing-waitlist.jsonl"),
            "person@example.com",
            waitlist_path=Path("/tmp/missing-pack_waitlist.py"),
        )
        self.assertEqual(result["verdict"], "DELETE_HELPER_MISSING")
        self.assertEqual(result["removed"], 0)
        self.assertEqual(result["sends"], 0)
        self.assertNotIn("@", json.dumps(result))

    def test_invalid_email_does_not_echo_address(self) -> None:
        if not erase.WAITLIST_HELPER.is_file():
            self.skipTest("waitlist helper not in this tree")
        result = erase.delete(Path("/tmp/unused-waitlist.jsonl"), "not-an-email")
        self.assertEqual(result["verdict"], "DELETE_INVALID")
        self.assertNotIn("@", json.dumps(result))

    def test_delete_drops_rows_and_counts(self) -> None:
        if not erase.WAITLIST_HELPER.is_file():
            self.skipTest("waitlist helper not in this tree")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "signups.jsonl"
            path.write_text(json.dumps(SIGNUP) + "\n", encoding="utf-8")
            result = erase.delete(path, "Person@Example.com")
            text = path.read_text(encoding="utf-8")
        self.assertEqual(result["verdict"], "DELETE_OK")
        self.assertEqual(result["removed"], 1)
        self.assertEqual(result["counts"]["total"], 0)
        self.assertEqual(result["counts"]["tiers"]["desk"], 0)
        self.assertNotIn("@", json.dumps(result))
        self.assertNotIn("person@example.com", text)
        self.assertNotIn("@", text)
        self.assertIn("email_sha256", text)
        self.assertEqual(result["email_sha256"], erase.email_sha256("person@example.com"))

    def test_missing_address_does_not_rewrite(self) -> None:
        if not erase.WAITLIST_HELPER.is_file():
            self.skipTest("waitlist helper not in this tree")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "signups.jsonl"
            path.write_text(json.dumps(SIGNUP) + "\n", encoding="utf-8")
            before = path.read_text(encoding="utf-8")
            result = erase.delete(path, "other@example.com")
            after = path.read_text(encoding="utf-8")
        self.assertEqual(result["verdict"], "DELETE_MISSING")
        self.assertEqual(result["removed"], 0)
        self.assertEqual(before, after)
        self.assertEqual(result["counts"]["total"], 1)
        self.assertNotIn("other@example.com", json.dumps(result))

    def test_keeps_other_signups(self) -> None:
        if not erase.WAITLIST_HELPER.is_file():
            self.skipTest("waitlist helper not in this tree")
        other = dict(SIGNUP, email="keep@example.com", tier="plant")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "signups.jsonl"
            path.write_text(
                json.dumps(SIGNUP) + "\n" + json.dumps(other) + "\n",
                encoding="utf-8",
            )
            result = erase.delete(path, "person@example.com")
            text = path.read_text(encoding="utf-8")
        self.assertEqual(result["verdict"], "DELETE_OK")
        self.assertEqual(result["counts"]["total"], 1)
        self.assertEqual(result["counts"]["tiers"]["plant"], 1)
        self.assertIn("keep@example.com", text)
        self.assertNotIn("person@example.com", text)
        self.assertNotIn("@", json.dumps(result))


if __name__ == "__main__":
    unittest.main()
