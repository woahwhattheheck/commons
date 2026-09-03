#!/usr/bin/env python3
"""Pin unique PR 8656 already-merged verify. Do not remint original leftover."""

from __future__ import annotations

import hashlib
import subprocess
import unittest
from pathlib import Path

import fix_first

ROOT = Path(__file__).resolve().parent
VERIFY = ROOT / "p/grokbuild-pr8656-verify-20260903-01.md"
ORIGINAL = ROOT / "p/grokbuild-llms-txt-33723861225-billing-lock-20260903-01.md"
ORIGINAL_TEST = ROOT / "test_grokbuild_llms_txt_33723861225_billing_lock.py"
WORKFLOW = ROOT / ".github/workflows/llms-txt.yml"
BODY_SHA256 = "3853a92a3fab712750332c8cf362748a733a9839acc5fc529e2a5dd00ac2d35f"

KEEP = {
    "p/grokbuild-llms-txt-33723861225-billing-lock-20260903-01.md": "09244cf3",
    "test_grokbuild_llms_txt_33723861225_billing_lock.py": "313df49a",
    "llms_txt.py": "83fc5ea9",
    ".github/workflows/llms-txt.yml": "d2182a3d",
    "open_door_guard.py": "4b053e43",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildPr8656Verify(unittest.TestCase):
    def test_original_leftover_and_publisher_unread(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )
        yml = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("python3 llms_txt.py --publish", yml)
        self.assertIn("ref: main", yml)
        self.assertIn("cancel-in-progress: false", yml)
        self.assertNotIn("if: false", yml)
        self.assertNotIn("billing", yml.lower())

    def test_verify_receipt_is_unique(self) -> None:
        text = VERIFY.read_text(encoding="utf-8")
        original = ORIGINAL.read_text(encoding="utf-8")
        self.assertIn("grokbuild-pr8656-verify-20260903-01", text)
        self.assertIn("https://github.com/woahwhattheheck/commons/pull/8656", text)
        self.assertIn("33723861225", text)
        self.assertIn("woahwhattheheck/commons#8656@bf9430b308f1e0427b2013e72c73f01aa46804e9", text)
        self.assertIn("woahwhattheheck/commons:llms-txt:f0a980053dae781f35e8723428d42aae64b7a5d3:bake", text)
        self.assertIn("6e058047468255802e2319474eacc2dc0f3fff97", text)
        self.assertIn("bf9430b308f1e0427b2013e72c73f01aa46804e9", text)
        self.assertIn("8b8bb19e2a332686a2b78b39bbcc328a62f2b096", text)
        self.assertIn("09244cf3", text)
        self.assertIn("313df49a", text)
        self.assertIn("83fc5ea9", text)
        self.assertIn("d2182a3d", text)
        self.assertIn("4b053e43", text)
        self.assertIn("issuecomment-5521690029", text)
        self.assertIn("issuecomment-5521729878", text)
        self.assertIn(
            "The job was not started because your account is locked due to a billing issue.",
            text,
        )
        self.assertIn("ALREADY_MERGED_VERIFIED", text)
        self.assertIn("INTEGRATED — VERIFIED ON CURRENT MAIN", text)
        self.assertIn("DURABLE_ON_MAIN", text)
        self.assertIn("EXTERNAL_BLOCKER", text)
        self.assertIn("Did not remint leftover grokbuild-llms-txt-33723861225-billing-lock-20260903-01", text)
        self.assertIn("Did not reopen #7915", text)
        self.assertNotEqual(text, original)
        self.assertNotIn("grokbuild-pr8656-verify-20260903-01", original)
        parts = text.split("---\n")
        self.assertGreaterEqual(len(parts), 3)
        body = parts[2].lstrip("\n").rstrip("\n")
        self.assertEqual(hashlib.sha256(body.encode("utf-8")).hexdigest(), BODY_SHA256)

    def test_publish_still_refuses_outside_actions(self) -> None:
        import os

        env = os.environ.copy()
        env.pop("GITHUB_ACTIONS", None)
        rc = subprocess.run(
            ["python3", "llms_txt.py", "--publish"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            env=env,
        )
        self.assertNotEqual(rc.returncode, 0)
        out = (rc.stdout or "") + (rc.stderr or "")
        self.assertIn("unsafe-context", out)

    def test_fix_first_packet_is_external_blocker(self) -> None:
        packet = {
            "outcome": "external_blocker",
            "observed_broken": True,
            "finding_kind": "behavior",
            "expected_contract": (
                "llms-txt.yml job bake executes python3 llms_txt.py --publish "
                "on push to main"
            ),
            "repair_attempts": [
                "original leftover 09244cf3 durable on current main",
                "leftover 4/4; test_llms_publish.py ALL PASS; test_llms_pulse.py 4/4; test_baked_head_json.py 10/10",
                "GitHub contents readback blobs 09244cf3 / 313df49a @ 8b8bb19e",
                "ntfy 200 mail; hosted ingest not durable under billing lock",
            ],
            "blocker": (
                "GitHub Actions ubuntu-latest never assigned: "
                "The job was not started because your account is locked due to a billing issue."
            ),
            "report_only_sessions": 0,
            "unconsumed_findings": 0,
        }
        self.assertEqual(fix_first.validate(packet)["state"], "EXTERNAL_BLOCKER")


if __name__ == "__main__":
    unittest.main()
