#!/usr/bin/env python3
"""resources.html last-reviewed stamp + regenerate-or-alarm canaries."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "host"))

import resources_tab as tab  # noqa: E402


FIXED_SHA = "4168d76c4d12633fa2ac2e7b3946ec3ad60f77b9"
FIXED_TIME = "2026-08-31T00:00:00Z"
def _absent_constructions(blob: str) -> None:
    lowered = blob.lower()
    assert "must authenticate" not in lowered
    assert "seat is required" not in lowered
    assert "required reviewers" not in lowered
    assert ("protected" + "_files").lower() not in lowered
    assert ("allowed" + "_verbs").lower() not in lowered
    assert ("tos" + "_gate").lower() not in lowered


def copy_live_tree(dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    rels = list(tab.FIXED_SOURCES) + [tab.DEFAULT_PAGE, "host/resources_tab.py"]
    for rel in rels:
        src = ROOT / rel
        if not src.is_file():
            continue
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target)
    records = ROOT / tab.INVENTORY_RECORDS
    if records.is_dir():
        target_records = dest / tab.INVENTORY_RECORDS
        target_records.mkdir(parents=True, exist_ok=True)
        for path in records.glob("*.json"):
            shutil.copy2(path, target_records / path.name)


class ResourcesTabTests(unittest.TestCase):
    def test_self_test(self) -> None:
        self.assertEqual(tab.self_test(), 0)

    def test_live_page_has_generated_stamp_after_regenerate(self) -> None:
        with tempfile.TemporaryDirectory(prefix="resources-tab-live-") as tmp:
            root = Path(tmp)
            copy_live_tree(root)
            row = tab.regenerate(
                str(root),
                sha=FIXED_SHA,
                reviewed_at=FIXED_TIME,
            )
            page = (root / "resources.html").read_text(encoding="utf-8")
            self.assertEqual(row["state"], "FRESH")
            self.assertTrue(row["present"])
            self.assertIn('id="resources-last-reviewed"', page)
            self.assertIn("LAST REVIEWED 2026-08-31T00:00:00Z", page)
            self.assertIn(FIXED_SHA, page)
            self.assertIn('data-resources-freshness="FRESH"', page)
            self.assertIn("Action Pad", page)
            self.assertIn("does not move money", page)
            self.assertIn("measured host-zero operation was already achieved", page)
            self.assertIn('href="./ledger.html"', page)

    def test_stale_sources_fail_and_alarm_writes_visible_mark(self) -> None:
        with tempfile.TemporaryDirectory(prefix="resources-tab-stale-") as tmp:
            root = Path(tmp)
            copy_live_tree(root)
            tab.regenerate(str(root), sha=FIXED_SHA, reviewed_at=FIXED_TIME)
            ledger = root / "ground" / "RESOURCE_LEDGER.json"
            data = json.loads(ledger.read_text(encoding="utf-8"))
            data["_freshness_canary"] = "drift"
            ledger.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
            measured = tab.measure(str(root))
            self.assertEqual(measured["state"], "STALE")
            check = subprocess.run(
                [sys.executable, str(ROOT / "host" / "resources_tab.py"), "--root", str(root), "--check"],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(check.returncode, 0)
            self.assertIn("STALE", check.stdout)
            alarmed = tab.alarm(str(root), sha=FIXED_SHA, reviewed_at=FIXED_TIME)
            page = (root / "resources.html").read_text(encoding="utf-8")
            self.assertEqual(alarmed["state"], "STALE")
            self.assertIn('data-resources-freshness="STALE"', page)
            self.assertIn("STALE", page)
            self.assertIn("Do not treat this tab as current", page)
            self.assertIn("Action Pad", page)

    def test_regenerate_or_alarm_produces_matching_page(self) -> None:
        with tempfile.TemporaryDirectory(prefix="resources-tab-regen-") as tmp:
            root = Path(tmp)
            copy_live_tree(root)
            tab.regenerate(str(root), sha=FIXED_SHA, reviewed_at=FIXED_TIME)
            record_dir = root / tab.INVENTORY_RECORDS
            record_dir.mkdir(parents=True, exist_ok=True)
            (record_dir / "canary-resources-tab-20260830-01.json").write_text(
                '{"event_type":"CANARY","id":"canary-resources-tab-20260830-01"}\n',
                encoding="utf-8",
            )
            self.assertEqual(tab.measure(str(root))["state"], "STALE")
            row = tab.regenerate_or_alarm(
                str(root),
                sha="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                reviewed_at="2026-08-31T00:05:00Z",
            )
            page = (root / "resources.html").read_text(encoding="utf-8")
            self.assertEqual(row["state"], "FRESH")
            self.assertEqual(row.get("action"), "REGENERATED")
            self.assertEqual(row["digest"], row["page_digest"])
            self.assertIn("LAST REVIEWED 2026-08-31T00:05:00Z", page)
            self.assertIn("aaaaaaaaaaaa", page)
            self.assertNotIn('data-resources-freshness="STALE"', page)
            self.assertEqual(tab.measure(str(root))["state"], "FRESH")

    def test_helper_and_workflow_do_not_gate_posting(self) -> None:
        helper = (ROOT / "host" / "resources_tab.py").read_text(encoding="utf-8")
        workflow = (ROOT / ".github" / "workflows" / "resources-tab-freshness.yml").read_text(
            encoding="utf-8"
        )
        page = (ROOT / "resources.html").read_text(encoding="utf-8")
        for blob in (helper, workflow):
            _absent_constructions(blob)
        self.assertIn("No gate", helper)
        self.assertIn("Does not block posting", helper)
        self.assertIn("zero-credential POST", page)
        self.assertIn("Do not add login, credentials, identity proof, trust or approval gates", page)
        self.assertIn("cron:", workflow)
        self.assertIn("regenerate-or-alarm", workflow)
        self.assertIn("test_resources_tab.py", workflow)

    def test_workflow_is_scheduled_and_path_scoped(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "resources-tab-freshness.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("schedule:", workflow)
        self.assertIn("resources.html", workflow)
        self.assertIn("ground/RESOURCE_LEDGER.json", workflow)
        self.assertIn("inventory/resources/**", workflow)
        self.assertIn("contents: write", workflow)
        self.assertIn("contents: read", workflow)
        self.assertNotIn("branch-protection", workflow)

    def test_open_door_guard_accepts_this_diff_shape(self) -> None:
        helper = (ROOT / "host" / "resources_tab.py").read_text(encoding="utf-8")
        added = [line for line in helper.splitlines() if line.strip()][:8]
        diff = "\n".join(
            [
                "diff --git a/host/resources_tab.py b/host/resources_tab.py",
                "--- a/host/resources_tab.py",
                "+++ b/host/resources_tab.py",
                "@@ -0,0 +1,%s @@" % len(added),
                *("+" + line for line in added),
                "",
            ]
        )
        proc = subprocess.run(
            [sys.executable, str(ROOT / "open_door_guard.py"), "--diff-file", "-"],
            input=diff,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)


if __name__ == "__main__":
    unittest.main()
