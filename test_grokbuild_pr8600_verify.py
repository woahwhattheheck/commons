#!/usr/bin/env python3
"""Pin unique PR 8600 already-merged verify. Do not remint discord-cloud leftover."""

from __future__ import annotations

import hashlib
import subprocess
import unittest
from pathlib import Path

import open_door_guard as guard

ROOT = Path(__file__).resolve().parent
VERIFY = ROOT / "p/grokbuild-pr8600-verify-20260903-01.md"
LEFTOVER = ROOT / "p/grok-build-discord-cloud-33718131448-billing-lock-20260903-01.md"
LEFTOVER_TEST = ROOT / "test_grokbuild_discord_cloud_33718131448_billing_lock.py"
PRIOR = ROOT / "p/grok-build-discord-cloud-33717741051-billing-lock-20260903-01.md"
WORKFLOW = ROOT / ".github/workflows/commons-discord-cloud.yml"
BODY_SHA256 = "be1d666fcbe9a6a95a683b0689656c1c08d62b01346951ac9c0a157434660fb7"

KEEP = {
    "p/grok-build-discord-cloud-33718131448-billing-lock-20260903-01.md": "861911cb",
    "test_grokbuild_discord_cloud_33718131448_billing_lock.py": "1fa28ce9",
    "p/grok-build-discord-cloud-33717741051-billing-lock-20260903-01.md": "b7a4ea0e",
    "test_grokbuild_discord_cloud_33717741051_billing_lock.py": "361b7c4b",
    ".github/workflows/commons-discord-cloud.yml": "6f1c1479",
    "commons_discord.py": "f6f1a374",
    "open_door_guard.py": "4b053e43",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildPr8600Verify(unittest.TestCase):
    def test_keep_8600_leftover_and_helpers_unread(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )
        yml = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("python3 infra/discord/assert_ready.py commons_to_discord", yml)
        self.assertIn("python3 commons_discord.py to-discord send", yml)
        self.assertNotIn("if: false", yml)
        self.assertNotIn("billing", yml.lower())

    def test_verify_receipt_is_unique_and_does_not_remint(self) -> None:
        text = VERIFY.read_text(encoding="utf-8")
        leftover = LEFTOVER.read_text(encoding="utf-8")
        leftover_test = LEFTOVER_TEST.read_text(encoding="utf-8")
        prior = PRIOR.read_text(encoding="utf-8")
        self.assertIn("grokbuild-pr8600-verify-20260903-01", text)
        self.assertIn(
            "woahwhattheheck/commons#8600@c2ae082438d640f858dda50b86b863b7dfcbdbbe",
            text,
        )
        self.assertIn("https://github.com/woahwhattheheck/commons/pull/8600", text)
        self.assertIn("c2ae082438d640f858dda50b86b863b7dfcbdbbe", text)
        self.assertIn("727feb85fe01df8b08c0bc3435d966babb75581b", text)
        self.assertIn("7de4c5b4f84483c18ef98b86b58f18a2262ab327", text)
        self.assertIn("861911cb", text)
        self.assertIn("1fa28ce9", text)
        self.assertIn("ALREADY_MERGED_VERIFIED", text)
        self.assertIn("INTEGRATED — VERIFIED ON CURRENT MAIN", text)
        self.assertIn("Unique leftover durable", text)
        self.assertIn("WkkFHkWQ8r5N", text)
        self.assertIn("33718131448", text)
        self.assertIn("EXTERNAL_BLOCKER", text)
        self.assertIn("Did not reopen #7915", text)
        self.assertIn("Did not reopen #7915 / #8400", text)
        self.assertNotEqual(text, leftover)
        self.assertNotEqual(text, prior)
        self.assertNotEqual(Path(__file__).read_text(encoding="utf-8"), leftover_test)
        self.assertNotIn("woahwhattheheck/commons#8600@", leftover)
        self.assertNotIn("grokbuild-pr8600-verify-20260903-01", leftover)
        parts = text.split("---\n")
        self.assertGreaterEqual(len(parts), 3)
        body = parts[2].lstrip("\n").rstrip("\n")
        self.assertEqual(hashlib.sha256(body.encode("utf-8")).hexdigest(), BODY_SHA256)

    def test_leftover_unittest_still_green(self) -> None:
        proc = subprocess.run(
            ["python3", "-m", "unittest", "test_grokbuild_discord_cloud_33718131448_billing_lock.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("Ran 4 tests", proc.stderr + proc.stdout)

    def test_open_door_guard_on_verify_paths(self) -> None:
        added = [
            guard.AddedLine(str(VERIFY.relative_to(ROOT)), i + 1, line)
            for i, line in enumerate(VERIFY.read_text(encoding="utf-8").splitlines())
        ]
        added.extend(
            guard.AddedLine(str(Path(__file__).relative_to(ROOT)), i + 1, line)
            for i, line in enumerate(Path(__file__).read_text(encoding="utf-8").splitlines())
        )
        self.assertEqual(guard.scan_added(added), [])


if __name__ == "__main__":
    unittest.main()
