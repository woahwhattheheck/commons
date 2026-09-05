#!/usr/bin/env python3
"""Pin unique leftover for resources-tab-freshness run 33809352414. Do not remint stamp contract or prior leftovers."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

import fix_first
import host.resources_tab as resources_tab

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-resources-tab-freshness-33809352414-billing-lock-20260903-01.md"
PRIOR_0902 = ROOT / "p/grok-resources-tab-freshness-billing-lock-20260902-01.md"
PRIOR_0903 = ROOT / "p/grok-resources-tab-freshness-billing-lock-20260903-01.md"
PRIOR_337675 = ROOT / "p/grokbuild-resources-tab-freshness-33767588782-billing-lock-20260903-01.md"
PRIOR_337916 = ROOT / "p/grokbuild-resources-tab-freshness-33791659583-billing-lock-20260903-01.md"
WORKFLOW = ROOT / ".github/workflows/resources-tab-freshness.yml"

KEEP = {
    ".github/workflows/resources-tab-freshness.yml": "658eec6f",
    "host/resources_tab.py": "18ae6933",
    "test_resources_tab.py": "8aa4fdd9",
    "open_door_guard.py": "4b053e43",
    "p/grok-resources-tab-freshness-billing-lock-20260902-01.md": "ac39fe78",
    "p/grok-resources-tab-freshness-billing-lock-20260903-01.md": "2eb99153",
    "p/grokbuild-resources-tab-freshness-33767588782-billing-lock-20260903-01.md": "eca6f65c",
    "p/grokbuild-resources-tab-freshness-33791659583-billing-lock-20260903-01.md": "3e88363c",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildResourcesTabFreshness33809352414BillingLock(unittest.TestCase):
    def test_keep_stamp_contract_and_prior_leftovers_unread(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )
        yml = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("python3 test_resources_tab.py", yml)
        self.assertIn("python3 host/resources_tab.py --regenerate-or-alarm", yml)
        self.assertIn("python3 host/resources_tab.py --check", yml)
        self.assertIn('cron: "19 * * * *"', yml)
        self.assertNotIn("billing", yml.lower())
        self.assertNotIn("if: false", yml)

    def test_receipt_is_unique_and_does_not_remint(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        prior_0902 = PRIOR_0902.read_text(encoding="utf-8")
        prior_0903 = PRIOR_0903.read_text(encoding="utf-8")
        prior_337675 = PRIOR_337675.read_text(encoding="utf-8")
        prior_337916 = PRIOR_337916.read_text(encoding="utf-8")
        self.assertIn(
            "grokbuild-resources-tab-freshness-33809352414-billing-lock-20260903-01",
            text,
        )
        self.assertIn(
            "woahwhattheheck/commons:resources-tab-freshness:e1e99b60a56dd56489b6dba03ab70c4b1cabba16:regenerate-or-alarm",
            text,
        )
        self.assertIn("33809352414", text)
        self.assertIn("100827291774", text)
        self.assertIn("100827975961", text)
        self.assertIn("e1e99b60a56dd56489b6dba03ab70c4b1cabba16", text)
        self.assertIn(
            "The job was not started because your account is locked due to a billing issue.",
            text,
        )
        self.assertIn("EXTERNAL_BLOCKER", text)
        self.assertIn("Did not remint leftover grok-resources-tab-freshness-billing-lock-20260902-01", text)
        self.assertIn("Did not remint leftover grok-resources-tab-freshness-billing-lock-20260903-01", text)
        self.assertIn("Did not remint leftover grokbuild-resources-tab-freshness-33767588782-billing-lock-20260903-01", text)
        self.assertIn("Did not remint leftover grokbuild-resources-tab-freshness-33791659583-billing-lock-20260903-01", text)
        self.assertIn("ac39fe78", text)
        self.assertIn("2eb99153", text)
        self.assertIn("eca6f65c", text)
        self.assertIn("3e88363c", text)
        self.assertIn("658eec6f", text)
        self.assertIn("8505d03d", text)
        self.assertIn("ec8a5aef", text)
        self.assertIn("4b053e43", text)
        self.assertIn("Did not reopen #8404", text)
        self.assertIn("Did not reopen #8683", text)
        self.assertIn("Did not reopen #8688", text)
        self.assertIn("Did not reopen #8691", text)
        self.assertIn("Did not reopen #7915", text)
        self.assertIn("8700", text)
        self.assertNotEqual(text, prior_0902)
        self.assertNotEqual(text, prior_0903)
        self.assertNotEqual(text, prior_337675)
        self.assertNotEqual(text, prior_337916)
        self.assertNotIn(
            "resources-tab-freshness:e1e99b60a56dd56489b6dba03ab70c4b1cabba16:regenerate-or-alarm",
            prior_0902,
        )
        self.assertNotIn(
            "resources-tab-freshness:e1e99b60a56dd56489b6dba03ab70c4b1cabba16:regenerate-or-alarm",
            prior_337916,
        )

    def test_local_resources_tab_still_fresh(self) -> None:
        row = resources_tab.measure(str(ROOT), sha="e1e99b60a56dd56489b6dba03ab70c4b1cabba16")
        self.assertEqual(row["state"], "FRESH")
        self.assertTrue(row["present"])
        self.assertEqual(
            row["digest"],
            "259f9729a21f2da32eefadd664a83fad0380720fb9e29eaa51ad929cbe8054fa",
        )
        self.assertEqual(row["page_digest"], row["digest"])
        again = resources_tab.regenerate_or_alarm(
            str(ROOT), sha="e1e99b60a56dd56489b6dba03ab70c4b1cabba16"
        )
        self.assertEqual(again["state"], "FRESH")
        self.assertEqual(again["digest"], row["digest"])

    def test_fix_first_packet_is_external_blocker(self) -> None:
        packet = {
            "outcome": "external_blocker",
            "observed_broken": True,
            "finding_kind": "behavior",
            "expected_contract": (
                "resources-tab-freshness.yml job regenerate-or-alarm executes "
                "python3 test_resources_tab.py then host/resources_tab.py "
                "--regenerate-or-alarm --sha GITHUB_SHA then --check"
            ),
            "repair_attempts": [
                "local test_resources_tab.py 7/7 --self-test --check FRESH --regenerate-or-alarm FRESH no writes",
                "inspected resources-tab-freshness.yml valid schedule no YAML defect",
                "github rerun_failed_jobs 201; attempt 2 same billing refusal",
                "GitHub Actions billing APIs unavailable; owner unlock is provider work",
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
