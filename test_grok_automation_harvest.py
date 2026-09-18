#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from host.grok_automation_harvest import (
    COMPLETE,
    UNMEASURED,
    collect_harvest,
    classify_provenance,
    summarize_automations,
)


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ).stdout.strip()


class GrokAutomationHarvestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory(prefix="grok-automation-harvest-")
        self.repo = Path(self.tempdir.name)
        git(self.repo, "init", "-b", "main")
        git(self.repo, "config", "user.name", "Harvest Test")
        git(self.repo, "config", "user.email", "harvest@example.invalid")
        posts = self.repo / "p"
        posts.mkdir()
        (posts / "grok-repair-pr12-20260901-01.md").write_text(
            "from: GROK_BUILD\nharness: grok.com automation\nid: grok-repair-pr12-20260901-01\n"
            "subject: workflow repair\n\nreceipt\n",
            encoding="utf-8",
        )
        (posts / "grok-repair-pr12-20260901-01.html").write_text("rendered\n", encoding="utf-8")
        (posts / "grok-gemini-20260831-01.md").write_text(
            "from: GEMINI\nharness: Commons MCP\nid: grok-gemini-20260831-01\n\nreceipt\n",
            encoding="utf-8",
        )
        (posts / "grok-unnamed.md").write_text("id: grok-unnamed\n\nreceipt\n", encoding="utf-8")
        (posts / "charttrace-lane-e-20260901-01.md").write_text(
            "from: CURSOR\nid: charttrace-lane-e-20260901-01\n\nreceipt\n",
            encoding="utf-8",
        )
        git(self.repo, "add", "p")
        git(self.repo, "commit", "-m", "receipts")
        self.base = git(self.repo, "rev-parse", "HEAD")
        self.branch_truth = {
            "schema": "commons.branch-truth-delta.v1",
            "repository": str(self.repo.resolve()),
            "base_sha": self.base,
            "branches": [
                {
                    "branch": "grok/landed",
                    "ref": "origin/grok/landed",
                    "head_sha": "a" * 40,
                    "merge_base_sha": "a" * 40,
                    "ahead": 0,
                    "behind": 0,
                    "unique_delta_state": "ANCESTRAL",
                    "comparison_completeness": COMPLETE,
                    "changed_path_blob_map": {},
                    "active_pr": None,
                },
                {
                    "branch": "grok-review",
                    "ref": "origin/grok-review",
                    "head_sha": "b" * 40,
                    "merge_base_sha": "c" * 40,
                    "ahead": 2,
                    "behind": 1,
                    "unique_delta_state": "UNIQUE",
                    "comparison_completeness": COMPLETE,
                    "changed_path_blob_map": {"tool.py": {"blob": "d" * 40}},
                    "active_pr": {"number": 12},
                },
                {
                    "branch": "cursor/unrelated",
                    "ref": "origin/cursor/unrelated",
                    "head_sha": "e" * 40,
                    "unique_delta_state": "UNIQUE",
                },
            ],
        }

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_provenance_requires_explicit_metadata(self) -> None:
        self.assertEqual(
            classify_provenance({"from": ["GROK_BUILD"], "harness": ["grok.com automation"]}),
            "EXPLICIT_GROK_COM",
        )
        self.assertEqual(classify_provenance({"from": ["GROK"]}), "EXPLICIT_GROK")
        self.assertEqual(
            classify_provenance({"from": ["GEMINI"], "subject": ["mentions grok.com"]}),
            "EXPLICIT_OTHER_HARNESS",
        )
        self.assertEqual(classify_provenance({}), "GROK_NAMED_ONLY")

    def test_body_metadata_lookalikes_do_not_change_provenance(self) -> None:
        posts = self.repo / "p"
        (posts / "grok-body-lookalike-20260901-01.md").write_text(
            "id: grok-body-lookalike-20260901-01\n---\n\nquoted packet:\n"
            "from: GEMINI\nharness: grok.com\n",
            encoding="utf-8",
        )
        git(self.repo, "add", "p/grok-body-lookalike-20260901-01.md")
        git(self.repo, "commit", "-m", "body lookalike")
        base = git(self.repo, "rev-parse", "HEAD")
        payload = dict(self.branch_truth)
        payload["base_sha"] = base
        result = collect_harvest(
            self.repo,
            branch_truth=payload,
            base_sha=base,
            branch_prefixes=("grok",),
            receipt_prefixes=("grok-body",),
            generated_at="2026-09-01T10:30:00Z",
        )
        self.assertEqual(result["receipts"]["provenance_counts"], {"GROK_NAMED_ONLY": 1})

    def test_missing_manifest_is_unmeasured_not_zero(self) -> None:
        summary = summarize_automations(None)
        self.assertEqual(summary["completeness"], UNMEASURED)
        self.assertIsNone(summary["count"])

    def test_harvest_joins_frozen_branch_and_receipt_truth(self) -> None:
        manifest = self.repo / "automations.json"
        manifest.write_text(
            json.dumps(
                {
                    "source": "operator screenshot",
                    "observed_at": "2026-09-01T10:27:00Z",
                    "automations": [
                        {"name": "morning", "trigger_kind": "daily", "schedule": "07:55"},
                        {"name": "push reconcile", "trigger_kind": "event"},
                    ],
                }
            ),
            encoding="utf-8",
        )
        result = collect_harvest(
            self.repo,
            branch_truth=self.branch_truth,
            base_sha=self.base,
            branch_prefixes=("grok/", "grok-"),
            receipt_prefixes=("grok", "charttrace"),
            automation_manifest=manifest,
            generated_at="2026-09-01T10:30:00Z",
            recent_limit=10,
        )
        self.assertEqual(result["summary"]["automation_count"], 2)
        self.assertEqual(result["summary"]["branch_count"], 2)
        self.assertEqual(result["summary"]["accounted_branch_count"], 1)
        self.assertEqual(result["summary"]["review_branch_count"], 1)
        self.assertEqual(result["summary"]["logical_receipt_count"], 4)
        self.assertEqual(result["branches"]["unmeasured_count"], 0)
        self.assertEqual(result["receipts"]["date_counts"]["20260901"], 2)
        self.assertEqual(result["receipts"]["provenance_counts"]["EXPLICIT_GROK_COM"], 1)
        self.assertEqual(result["receipts"]["provenance_counts"]["EXPLICIT_OTHER_HARNESS"], 2)
        self.assertEqual(result["receipts"]["provenance_counts"]["GROK_NAMED_ONLY"], 1)
        self.assertEqual(result["branches"]["review"][0]["changed_paths"], ["tool.py"])
        self.assertNotIn("rendered", json.dumps(result))

    def test_mismatched_frozen_bases_are_rejected(self) -> None:
        payload = dict(self.branch_truth)
        payload["base_sha"] = "f" * 40
        with self.assertRaisesRegex(Exception, "does not match"):
            collect_harvest(
                self.repo,
                branch_truth=payload,
                base_sha=self.base,
                branch_prefixes=("grok",),
                receipt_prefixes=("grok",),
                generated_at="2026-09-01T10:30:00Z",
            )


if __name__ == "__main__":
    unittest.main()
