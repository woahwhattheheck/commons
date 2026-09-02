#!/usr/bin/env python3
"""Independent MATCH that GitHub PR #7915 is CLOSED unmerged."""

from __future__ import annotations

import importlib.util
import io
import json
import subprocess
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "pr7915_closed_unmerged", ROOT / "host" / "pr7915_closed_unmerged.py"
)
assert SPEC and SPEC.loader
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)

RECEIPT = ROOT / "p/cursor-pr7915-closed-unmerged-readback-20260902-01.md"
POINTER = ROOT / "p/cursor-business-pack-harborline-map-pin-lift-pointer-20260902-01.md"
KEEP7915 = ROOT / "p/cursor-ack-moth-stamp-cz03-keep7915-20260902-01.md"
CLOSED_BODY = json.dumps(
    {
        "state": "closed",
        "merged": False,
        "merged_at": None,
        "closed_at": "2026-09-02T19:44:19Z",
        "title": "Point unique-pack at leftover Harborline map pin-lift",
        "number": 7915,
        "head": {
            "ref": "cursor/harborline-map-pin-lift-pointer-ae54",
            "sha": "fa046ce059009f0ddece9d91eaa5d60a1f281f39",
        },
    }
).encode("utf-8")


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestPr7915ClosedUnmerged(unittest.TestCase):
    def test_go_reopen_merge_send_apply_are_refused(self) -> None:
        for flag in ("--go", "--reopen", "--merge", "--send", "--apply"):
            with self.subTest(flag=flag):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    rc = probe.main([flag])
                self.assertEqual(rc, 2)
                dumped = json.loads(buf.getvalue())
                self.assertEqual(dumped["state"], "REFUSED")
                self.assertEqual(dumped["sent"], 0)
                row = probe.refuse(flag.lstrip("-"))
                self.assertEqual(row["state"], "REFUSED")
                self.assertEqual(row["sent"], 0)
                self.assertFalse(row["reopened"])
                self.assertFalse(row["merged"])
                self.assertFalse(row["permission"])

    def test_closed_unmerged_payload_is_match(self) -> None:
        row = probe.classify(200, CLOSED_BODY)
        self.assertEqual(row["state"], "MATCH")
        self.assertEqual(row["http"], 200)
        self.assertFalse(row["merged"])
        self.assertFalse(row["reopened"])
        self.assertEqual(row["sent"], 0)
        self.assertEqual(row["head_sha"], probe.HEAD_SHA)
        self.assertNotEqual(row["http"], 0)

    def test_network_miss_is_finder_failed_never_silent_zero(self) -> None:
        row = probe.classify(0, b"network down")
        self.assertEqual(row["state"], "FINDER-FAILED")
        self.assertEqual(row["http"], 0)
        self.assertIn("never silent 0", row["note"])
        self.assertFalse(row["reopened"])

    def test_http_403_is_named_miss_never_reopen_never_silent_zero(self) -> None:
        body = json.dumps({"message": "API rate limit exceeded for github.com"}).encode(
            "utf-8"
        )
        row = probe.classify(403, body)
        self.assertEqual(row["state"], "FINDER-FAILED")
        self.assertEqual(row["http"], 403)
        self.assertNotEqual(row["http"], 0)
        self.assertFalse(row["reopened"])
        self.assertFalse(row["merged"])
        self.assertEqual(row["sent"], 0)
        self.assertFalse(row["permission"])
        self.assertIn("Will not reopen", row["note"])

    def test_http_429_is_named_miss_never_reopen(self) -> None:
        body = json.dumps({"message": "You have exceeded a secondary rate limit"}).encode(
            "utf-8"
        )
        row = probe.classify(429, body)
        self.assertEqual(row["state"], "FINDER-FAILED")
        self.assertEqual(row["http"], 429)
        self.assertFalse(row["reopened"])
        self.assertEqual(row["sent"], 0)
        self.assertIn("Will not reopen", row["note"])

    def test_open_payload_is_finder_failed_not_permission_to_reopen(self) -> None:
        body = json.dumps(
            {
                "state": "open",
                "merged": False,
                "merged_at": None,
                "closed_at": None,
                "head": {"ref": probe.HEAD_REF, "sha": probe.HEAD_SHA},
            }
        ).encode("utf-8")
        row = probe.classify(200, body)
        self.assertEqual(row["state"], "FINDER-FAILED")
        self.assertFalse(row["reopened"])
        self.assertIn("Will not reopen", row["note"])

    def test_receipt_keep_pointer_and_does_not_steal_qualify_live_probe(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        self.assertIn("cursor-pr7915-closed-unmerged-readback-20260902-01", text)
        self.assertIn("CLOSED", text)
        self.assertIn("19:44:19Z", text)
        self.assertIn("fa046ce05900", text)
        self.assertIn("7a8987b5", text)
        self.assertIn("Did not steal", text)
        self.assertIn("host/harborline_qualify_live_probe.py", text)
        self.assertNotIn("qualify.html", text)
        self.assertTrue(POINTER.exists())
        self.assertTrue(KEEP7915.exists())
        self.assertTrue(
            git_blob(
                "p/cursor-business-pack-harborline-map-pin-lift-pointer-20260902-01.md"
            ).startswith("7a8987b5")
        )
        self.assertTrue(
            git_blob("p/cursor-ack-moth-stamp-cz03-keep7915-20260902-01.md").startswith(
                "9d28dd61"
            )
        )
        self.assertTrue(git_blob("autogtm.html").startswith("9d8b3e85"))

    def test_this_seat_did_not_dump_qualify_html_or_corner(self) -> None:
        # Harborline CLAIM three live-probe paths may land later. Do not freeze
        # their absence. This seat must not dump qualify.html or CLAUDE_CORNER.md.
        self.assertFalse((ROOT / "qualify.html").exists())
        self.assertFalse((ROOT / "CLAUDE_CORNER.md").exists())
        self.assertTrue((ROOT / "host" / "pr7915_closed_unmerged.py").exists())
        self.assertNotEqual(
            (ROOT / "host" / "pr7915_closed_unmerged.py").name,
            "harborline_qualify_live_probe.py",
        )

    def test_live_github_pr_is_closed_unmerged_or_named_miss(self) -> None:
        row = probe.measure()
        # Unauthenticated GitHub API 403/429 is a named miss, not permission to
        # add a token and not silent 0. Missing auth is not a Commons defect.
        if row["http"] != 200:
            self.assertEqual(row["state"], "FINDER-FAILED")
            self.assertFalse(row["reopened"])
            self.assertFalse(row["merged"])
            self.assertEqual(row["sent"], 0)
            self.assertFalse(row["permission"])
            if row["http"] == 0:
                self.assertIn("never silent 0", row["note"])
            else:
                self.assertIn("Will not reopen", row["note"])
            return
        self.assertEqual(row["http"], 200)
        self.assertEqual(row["github_state"], "closed")
        self.assertFalse(row["merged"])
        self.assertEqual(row["closed_at"], probe.CLOSED_AT)
        self.assertEqual(row["head_sha"], probe.HEAD_SHA)
        self.assertEqual(row["state"], "MATCH")
        self.assertNotEqual(row["http"], 0)


if __name__ == "__main__":
    unittest.main()
