#!/usr/bin/env python3
"""Restore MANUAL.md builds.html cite after tests battery 34395174679.

Delayed pull_request battery on already-merged PR #11511
(head 0001c497a2ca5f317c5b9a3e2b1f00b57a5f4b67, merge-ref
f321c6f5e063bd65126d9512098ef650c5a1deba) failed 140 files.
Unique WIRE cite of builds.html beside wire.html was later reminted
away by ingest rebuild because manual_build.py did not emit it.
Emit the cite from the living builder so rebuilds keep it. Do not
remint leftover receipts. Historical SOURCE_REV maps stay on their
frozen trees. Hands off #8802.
"""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

import manual_build

ROOT = Path(__file__).resolve().parent
POINTER = (
    "One shared super MCP: [wire.html](../wire.html) — paste "
    "`https://commons-spark-mcp.vercel.app/mcp`. "
    "Law: [WIRE_SUPER_MCP.md](./WIRE_SUPER_MCP.md). "
    "Build ledger: [builds.html](../builds.html). Do not remint a second `/mcp`."
)
ORIGINALS = (
    "test_wire_manual_md_builds_door.py",
    "test_coil_tools_super_mcp_fold.py",
    "test_coil_ground_manual_tools_json.py",
    "test_coil_ground_manual_living_file.py",
    "test_coil_ground_manual_no_js_job_hook.py",
)
RECEIPT = ROOT / "p/grokbuild-tests-battery-34395174679-keep-lift-20260910-01.md"
LEFTOVER = ROOT / "p/wire-manual-md-builds-door-20260909-01.md"
LEFTOVER_TEST = ROOT / "test_wire_manual_md_builds_door.py"


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildTestsBattery34395174679KeepLift(unittest.TestCase):
    def test_builder_emits_builds_ledger_on_super_mcp_pointer(self) -> None:
        data = json.loads((ROOT / "tools.json").read_text(encoding="utf-8"))
        line = manual_build.super_mcp_pointer_line(data)
        self.assertEqual(line, POINTER)
        builder = (ROOT / "manual_build.py").read_text(encoding="utf-8")
        self.assertIn("Build ledger: [builds.html](../builds.html)", builder)
        self.assertIn("super_mcp_pointer_line", builder)

    def test_live_manual_md_keeps_builds_html_beside_wire(self) -> None:
        manual = (ROOT / "ground/MANUAL.md").read_text(encoding="utf-8")
        self.assertIn(POINTER, manual)
        self.assertIn("builds.html", manual)
        self.assertIn("wire.html", manual)
        self.assertTrue(git_blob("ground/MANUAL.md").startswith("3f4140b0"))
        self.assertFalse(git_blob("ground/MANUAL.md").startswith("79a93583"))

    def test_rebuild_is_byte_identical_to_live_manual(self) -> None:
        before = (ROOT / "ground/MANUAL.md").read_text(encoding="utf-8")
        rc = manual_build.main()
        after = (ROOT / "ground/MANUAL.md").read_text(encoding="utf-8")
        self.assertEqual(rc, 0)
        self.assertEqual(before, after)
        self.assertIn(POINTER, after)

    def test_originally_failing_unique_graph_contracts_pass(self) -> None:
        for name in ORIGINALS:
            with self.subTest(name=name):
                proc = subprocess.run(
                    ["python3", name],
                    cwd=ROOT,
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(
                    proc.returncode,
                    0,
                    msg=f"{name}\n{proc.stdout}\n{proc.stderr}",
                )

    def test_did_not_remint_leftover_receipts_or_tools_json(self) -> None:
        self.assertTrue(LEFTOVER.is_file())
        leftover = git_blob("p/wire-manual-md-builds-door-20260909-01.md")
        self.assertTrue(leftover.startswith("51c18333"), leftover)
        self.assertTrue(LEFTOVER_TEST.is_file())
        self.assertTrue(
            git_blob("test_wire_manual_md_builds_door.py").startswith("0c62d7bd")
        )
        self.assertTrue(git_blob("tools.json").startswith("0c4b38e7"))
        self.assertTrue(
            git_blob("p/coil-tools-super-mcp-fold-20260902-01.md").startswith(
                "6948bdc1"
            )
        )
        receipt = RECEIPT.read_text(encoding="utf-8")
        self.assertIn("34395174679", receipt)
        self.assertIn(
            "woahwhattheheck/commons:tests:0001c497a2ca5f317c5b9a3e2b1f00b57a5f4b67:the whole battery, one failure fails the run",
            receipt,
        )
        builder = (ROOT / "manual_build.py").read_text(encoding="utf-8")
        manual = (ROOT / "ground/MANUAL.md").read_text(encoding="utf-8")
        for text in (builder, manual):
            self.assertNotIn('type="password"', text)
            self.assertNotIn("Authorization", text)
            self.assertNotIn("buy.stripe.com", text)


if __name__ == "__main__":
    unittest.main()
