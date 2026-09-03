#!/usr/bin/env python3
"""Pin unique leftover for llms-txt run 33699607384. Do not remint prior leftover or publisher."""

from __future__ import annotations

import os
import subprocess
import unittest
from pathlib import Path

import fix_first

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grok-build-llms-txt-33699607384-billing-lock-20260903-01.md"
PRIOR = ROOT / "p/grok-build-llms-txt-billing-lock-20260902-01.md"
PRIOR_RUN = ROOT / "p/grok-build-llms-txt-33687829181-billing-lock-20260902-01.md"
SIBLING = ROOT / "p/grok-build-llms-txt-33689357433-billing-lock-20260902-01.md"
PEER_NEAR = ROOT / "p/grok-build-llms-txt-33694402716-billing-lock-20260902-01.md"
PEER_LATER = ROOT / "p/grok-build-llms-txt-33699286770-billing-lock-20260903-01.md"
ASSOC = ROOT / "p/grokbuild-pr8525-verify-20260903-01.md"
REMATCH = ROOT / "p/cursor-wire-catalog-marketplace-latch-readback-rematch-20260903-01.md"
WORKFLOW = ROOT / ".github/workflows/llms-txt.yml"

KEEP = {
    "p/grok-build-llms-txt-billing-lock-20260902-01.md": "cf9c9f40",
    "p/grok-build-llms-txt-33687829181-billing-lock-20260902-01.md": "3183564c",
    "p/grok-build-llms-txt-33689083252-billing-lock-20260902-01.md": "31213531",
    "p/grok-build-llms-txt-33689096471-billing-lock-20260902-01.md": "e739b9cd",
    "p/grok-build-llms-txt-33689281224-billing-lock-20260902-01.md": "e710946d",
    "p/grok-build-llms-txt-33689357433-billing-lock-20260902-01.md": "d103be4c",
    "p/grok-build-llms-txt-33694219034-billing-lock-20260902-01.md": "d8f8b166",
    "p/grok-build-llms-txt-33694253456-billing-lock-20260902-01.md": "8e08896c",
    "p/grok-build-llms-txt-33694402716-billing-lock-20260902-01.md": "6a8728e3",
    "p/grok-build-llms-txt-33699286770-billing-lock-20260903-01.md": "43c6e5cb",
    "p/grokbuild-pr8525-verify-20260903-01.md": "3e36c93c",
    "p/cursor-wire-catalog-marketplace-latch-readback-rematch-20260903-01.md": "f23e1db8",
    "p/cursor-wire-shared-super-mcp-catalog-readback-20260902-01.md": "593d54bc",
    "p/cursor-wire-super-mcp-marketplace-readback-20260902-01.md": "448eda52",
    "p/latch-wake-super-mcp-pointer-readback-20260902-01.md": "250907c9",
    "wire.html": "4ae38ce9",
    "ground/WIRE_SUPER_MCP.md": "f36de0a5",
    "p/cursor-big-huge-commerce-agents-readback-20260902-01.md": "2a5ce894",
    "p/cursor-harborline-commerce-compose-keep-lift-readback-20260902-01.md": "7155141f",
    ".github/workflows/llms-txt.yml": "d2182a3d",
    "llms_txt.py": "83fc5ea9",
    "owner_pin.py": "76e19209",
    "test_llms_publish.py": "c07317be",
    "test_llms_pulse.py": "e79f7851",
    "test_grokbuild_llms_txt_billing_lock.py": "6d73d3f9",
    "test_grokbuild_llms_txt_33687829181_billing_lock.py": "e02e5ab5",
    "test_grokbuild_llms_txt_33689083252_billing_lock.py": "1fda6a87",
    "test_grokbuild_llms_txt_33689096471_billing_lock.py": "862e61d2",
    "test_grokbuild_llms_txt_33689281224_billing_lock.py": "1d36c203",
    "test_grokbuild_llms_txt_33689357433_billing_lock.py": "c34d15c9",
    "test_grokbuild_llms_txt_33694219034_billing_lock.py": "b457e317",
    "test_grokbuild_llms_txt_33694253456_billing_lock.py": "45da7270",
    "test_grokbuild_llms_txt_33694402716_billing_lock.py": "5747616e",
    "test_grokbuild_llms_txt_33699286770_billing_lock.py": "fc9b6424",
    "test_cursor_wire_catalog_marketplace_latch_readback_rematch.py": "b9dffb45",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildLlmsTxt33699607384BillingLock(unittest.TestCase):
    def test_keep_publisher_and_prior_leftovers_unread(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )
        yml = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("python3 llms_txt.py --publish", yml)
        self.assertIn("ref: main", yml)
        self.assertNotIn("billing", yml.lower())
        self.assertNotIn("if: false", yml)
        src = (ROOT / "llms_txt.py").read_text(encoding="utf-8")
        self.assertIn('os.environ.get("GITHUB_ACTIONS") != "true"', src)
        self.assertIn("unsafe-context", src)

    def test_receipt_is_unique_and_does_not_remint(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        prior = PRIOR.read_text(encoding="utf-8")
        prior_run = PRIOR_RUN.read_text(encoding="utf-8")
        sibling = SIBLING.read_text(encoding="utf-8")
        peer_near = PEER_NEAR.read_text(encoding="utf-8")
        peer_later = PEER_LATER.read_text(encoding="utf-8")
        assoc = ASSOC.read_text(encoding="utf-8")
        rematch = REMATCH.read_text(encoding="utf-8")
        self.assertIn("grok-build-llms-txt-33699607384-billing-lock-20260903-01", text)
        self.assertIn(
            "woahwhattheheck/commons:llms-txt:e25521733acdd3387c285e37483a74d7af8de3c3:bake",
            text,
        )
        self.assertIn("33699607384", text)
        self.assertIn("100475840373", text)
        self.assertIn("100476808248", text)
        self.assertIn("e25521733acdd3387c285e37483a74d7af8de3c3", text)
        self.assertIn("8525", text)
        self.assertIn(
            "The job was not started because your account is locked due to a billing issue.",
            text,
        )
        self.assertIn("EXTERNAL_BLOCKER", text)
        self.assertIn("Did not remint leftover grok-build-llms-txt-billing-lock-20260902-01", text)
        self.assertIn("cf9c9f40", text)
        self.assertIn("3183564c", text)
        self.assertIn("31213531", text)
        self.assertIn("e739b9cd", text)
        self.assertIn("e710946d", text)
        self.assertIn("d103be4c", text)
        self.assertIn("d8f8b166", text)
        self.assertIn("8e08896c", text)
        self.assertIn("6a8728e3", text)
        self.assertIn("43c6e5cb", text)
        self.assertIn("3e36c93c", text)
        self.assertIn("f23e1db8", text)
        self.assertIn("593d54bc", text)
        self.assertIn("448eda52", text)
        self.assertIn("250907c9", text)
        self.assertIn("4ae38ce9", text)
        self.assertIn("f36de0a5", text)
        self.assertIn("2a5ce894", text)
        self.assertIn("7155141f", text)
        self.assertIn("83fc5ea9", text)
        self.assertIn("d2182a3d", text)
        self.assertIn("did not reopen #7915", text)
        self.assertNotEqual(text, prior)
        self.assertNotEqual(text, prior_run)
        self.assertNotEqual(text, sibling)
        self.assertNotEqual(text, peer_near)
        self.assertNotEqual(text, peer_later)
        self.assertNotEqual(text, assoc)
        self.assertNotEqual(text, rematch)
        self.assertNotIn(
            "llms-txt:e25521733acdd3387c285e37483a74d7af8de3c3:bake",
            prior,
        )
        self.assertNotIn(
            "llms-txt:e25521733acdd3387c285e37483a74d7af8de3c3:bake",
            prior_run,
        )
        self.assertNotIn(
            "llms-txt:e25521733acdd3387c285e37483a74d7af8de3c3:bake",
            sibling,
        )
        self.assertNotIn(
            "woahwhattheheck/commons:llms-txt:e25521733acdd3387c285e37483a74d7af8de3c3:bake",
            peer_near,
        )
        self.assertNotIn(
            "woahwhattheheck/commons:llms-txt:e25521733acdd3387c285e37483a74d7af8de3c3:bake",
            peer_later,
        )
        self.assertNotIn(
            "woahwhattheheck/commons:llms-txt:e25521733acdd3387c285e37483a74d7af8de3c3:bake",
            assoc,
        )
        self.assertNotIn(
            "woahwhattheheck/commons:llms-txt:e25521733acdd3387c285e37483a74d7af8de3c3:bake",
            rematch,
        )
        self.assertIn("llms-txt:8b42a78e0fa73ba3d343d8e8e78d6ca5d1a7be03:bake", prior)
        self.assertIn("llms-txt:19d172a397c98974de2b259473bfc670743a46e9:bake", prior_run)
        self.assertIn("llms-txt:ffacc45de870c3e7f7890f0e8cd025d40dc619f4:bake", sibling)
        self.assertIn(
            "woahwhattheheck/commons:llms-txt:f85e0aca9844c7571f92ef1b4ce4da874741fcb6:bake",
            peer_near,
        )
        self.assertIn("33699286770", peer_later)

    def test_publish_still_refuses_outside_actions(self) -> None:
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
        self.assertIn("refused outside GitHub Actions", out)
        self.assertIn("unsafe-context", out)

    def test_local_bake_only_and_fix_first_external_blocker(self) -> None:
        generated = [
            "challenge.json",
            "change.md",
            "fresh.md",
            "head.json",
            "llms.txt",
            "peers.md",
            "pulse.json",
        ]

        def restore() -> None:
            subprocess.run(
                ["git", "checkout", "--", *generated],
                cwd=ROOT,
                check=False,
            )

        self.addCleanup(restore)
        proc = subprocess.run(
            ["python3", "llms_txt.py", "--bake-only"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("baked src=git HEAD p/", proc.stdout)
        packet = {
            "outcome": "external_blocker",
            "observed_broken": True,
            "finding_kind": "behavior",
            "expected_contract": (
                "llms-txt.yml job bake executes python3 llms_txt.py --publish "
                "on push to main"
            ),
            "repair_attempts": [
                "local --bake-only PASS on current main (publisher KEEP 83fc5ea9)",
                "test_llms_publish.py ALL PASS; test_llms_pulse.py 4/4; test_baked_head_json.py 10/10",
                "github rerun_failed_jobs; attempt 2 same billing refusal runner empty",
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
