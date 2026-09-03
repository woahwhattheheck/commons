#!/usr/bin/env python3
"""Pin unique leftover for owner-net run 33723510040. Do not remint persist tree or prior leftovers."""

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

import fix_first
import owner_net

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grok-build-owner-net-33723510040-billing-lock-20260903-01.md"
PRIOR_PULSE = ROOT / "p/grok-build-repo-pulse-billing-lock-20260903-01.md"
PRIOR_DISCORD = ROOT / "p/grok-build-discord-cloud-billing-lock-20260902-01.md"
WORKFLOW = ROOT / ".github/workflows/owner-net.yml"

KEEP = {
    ".github/workflows/owner-net.yml": "5df56a0a",
    "owner_net.py": "941b0d8a",
    "owner.json": "dc6c0592",
    "test_owner_hash.py": "0f0e6870",
    "open_door_guard.py": "4b053e43",
    "fix_first.py": "a57aee1c",
    "p/grok-build-repo-pulse-billing-lock-20260903-01.md": "b6e5953c",
    "p/grok-build-discord-cloud-billing-lock-20260902-01.md": "2e0bfbfb",
    "p/grok-build-moving-main-mirror-billing-lock-20260903-01.md": "4550e922",
    "p/grok-resources-tab-freshness-billing-lock-20260902-01.md": "ac39fe78",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildOwnerNet33723510040BillingLock(unittest.TestCase):
    def test_keep_persist_tree_and_prior_leftovers_unread(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )
        yml = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("python3 owner_net.py", yml)
        self.assertIn("git add -- owner.json", yml)
        self.assertNotIn("billing", yml.lower())
        self.assertNotIn("if: false", yml)
        self.assertNotIn("board_ingest.py", yml)

    def test_receipt_is_unique_and_does_not_remint(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        prior_pulse = PRIOR_PULSE.read_text(encoding="utf-8")
        prior_discord = PRIOR_DISCORD.read_text(encoding="utf-8")
        self.assertIn("grok-build-owner-net-33723510040-billing-lock-20260903-01", text)
        self.assertIn(
            "woahwhattheheck/commons:owner-net:35ac733fbcf265852bc04e6400ef308a5b82104b:persist",
            text,
        )
        self.assertIn("33723510040", text)
        self.assertIn("100547406695", text)
        self.assertIn("100548409993", text)
        self.assertIn("35ac733fbcf265852bc04e6400ef308a5b82104b", text)
        self.assertIn(
            "The job was not started because your account is locked due to a billing issue.",
            text,
        )
        self.assertIn("EXTERNAL_BLOCKER", text)
        self.assertIn("Did not remint leftover grok-build-repo-pulse-billing-lock-20260903-01", text)
        self.assertIn("b6e5953c", text)
        self.assertIn("2e0bfbfb", text)
        self.assertIn("4550e922", text)
        self.assertIn("ac39fe78", text)
        self.assertIn("5df56a0a", text)
        self.assertIn("941b0d8a", text)
        self.assertIn("dc6c0592", text)
        self.assertIn("0f0e6870", text)
        self.assertNotEqual(text, prior_pulse)
        self.assertNotEqual(text, prior_discord)
        self.assertNotIn(
            "owner-net:35ac733fbcf265852bc04e6400ef308a5b82104b:persist",
            prior_pulse,
        )
        self.assertNotIn(
            "owner-net:35ac733fbcf265852bc04e6400ef308a5b82104b:persist",
            prior_discord,
        )

    def test_local_persist_still_live_without_writing(self) -> None:
        spec = owner_net.load_spec()
        self.assertTrue(owner_net.distinct_live(spec))
        pc = owner_net.slot_hash((spec.get("slots") or {}).get("pc"))
        phone = owner_net.slot_hash((spec.get("slots") or {}).get("phone"))
        self.assertTrue(pc and phone and pc != phone)
        self.assertFalse(owner_net.apply_sighting(spec, pc, "pc"))
        self.assertFalse(owner_net.apply_sighting(spec, pc, "phone"))
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / "owner.json"
            copy.write_text((ROOT / "owner.json").read_text(encoding="utf-8"), encoding="utf-8")
            loaded = owner_net.load_spec(str(copy))
            self.assertEqual(owner_net.persist(loaded, []), 0)
            self.assertTrue(owner_net.distinct_live(loaded))

    def test_fix_first_packet_is_external_blocker(self) -> None:
        packet = {
            "outcome": "external_blocker",
            "observed_broken": True,
            "finding_kind": "behavior",
            "expected_contract": (
                "owner-net.yml job persist on schedule executes checkout "
                "then python3 owner_net.py then commits owner.json hashes only"
            ),
            "repair_attempts": [
                "local test_owner_hash.py 84/84",
                "local owner_net.py rc=0 LIVE wrote=0",
                "local test_owner_context.py 26/26",
                "github rerun_failed_jobs 201; attempt 2 same billing refusal",
                "gmail_search GitHub billing lock empty",
                "GitHub Actions billing write road absent",
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
