#!/usr/bin/env python3
"""Merge-on-PR living KEEP pins must match current api/mcp.py after adapter remint.

Battery run 35624444194 failed test_cursor_merge_on_pr_readback.py:
KEEP still froze api/mcp.py at 393da756 after the adapter remint to a2683bf4
(toolCount 19). Nested leftover test_merge_on_pr.py used the same stale pin.
Close the merge-on-pr cluster so leftover + readback track the live adapter
together. Do not remint leftover receipts or reopen #7915.
"""

from __future__ import annotations

import ast
import json
import re
import subprocess
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
KEEP_RE = re.compile(r"^KEEP\s*=\s*\{", re.M)
TARGETS = (
    "api/mcp.py",
    "test_merge_on_pr.py",
)
CLUSTER = (
    "test_merge_on_pr.py",
    "test_cursor_merge_on_pr_readback.py",
)
ORIGINALS = (
    "test_merge_on_pr.py",
    "test_cursor_merge_on_pr_readback.py",
)
KEEP_UNREAD = {
    "p/cursor-merge-on-pr-20260902-01.md": "22b63e25",
    "p/cursor-merge-on-pr-readback-20260902-01.md": "e160b2c3",
    "host/merge_on_pr.py": "5062c29b",
    "merge-on-pr.html": "f1d0c6d9",
    "ground/MERGE_ON_PR.json": "4e7967dc",
    "host/sprint_integration.py": "1ba2002c",
    "host/pr7915_closed_unmerged.py": "9d56ea0e",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


def parse_keep(text: str) -> dict[str, str] | None:
    match = KEEP_RE.search(text)
    if not match:
        return None
    start = text.find("{", match.start())
    depth = 0
    for index, char in enumerate(text[start:], start):
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                try:
                    value = ast.literal_eval(text[start : index + 1])
                except (SyntaxError, ValueError):
                    return None
                if isinstance(value, dict):
                    return {str(key): str(prefix) for key, prefix in value.items()}
                return None
    return None


def cluster_keep_maps() -> list[tuple[str, dict[str, str]]]:
    maps: list[tuple[str, dict[str, str]]] = []
    for rel in CLUSTER:
        keep = parse_keep((ROOT / rel).read_text(encoding="utf-8"))
        if keep:
            maps.append((rel, keep))
    return maps


class TestBattery35624444194MergeOnPrMcpKeepLift(unittest.TestCase):
    def test_merge_on_pr_cluster_keep_pins_match_current_blobs(self) -> None:
        blobs = {rel: git_blob(rel) for rel in TARGETS}
        self.assertTrue(blobs["api/mcp.py"].startswith("a2683bf4"))
        stale: list[str] = []
        pinned_by = {rel: 0 for rel in TARGETS}
        for carrier, keep in cluster_keep_maps():
            for rel, prefix in keep.items():
                blob = blobs.get(rel)
                if blob is None:
                    continue
                pinned_by[rel] += 1
                if not blob.startswith(prefix):
                    stale.append(
                        f"{carrier} pins {rel} want {prefix} got {blob[:8]}"
                    )
        self.assertGreaterEqual(pinned_by["api/mcp.py"], 2)
        self.assertGreaterEqual(pinned_by["test_merge_on_pr.py"], 1)
        self.assertEqual(stale, [], msg="\n".join(stale))

    def test_helper_renders_without_reopening_7915(self) -> None:
        proc = subprocess.run(
            [sys.executable, "host/merge_on_pr.py", "--json"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        packet = json.loads(proc.stdout)
        self.assertEqual(packet["verdict"], "RENDER", packet)
        self.assertTrue(packet["merge_default"])
        self.assertFalse(packet["login"])
        self.assertFalse(packet["gate"])
        self.assertEqual(packet["pr7915_leftover_state"], "MATCH")
        self.assertFalse(packet["pr7915_merged"])
        self.assertTrue(packet["pr7915_reopen_refused"])
        self.assertEqual(packet["sends"], 0)

    def test_originally_failing_contracts_pass(self) -> None:
        for name in ORIGINALS:
            with self.subTest(name=name):
                proc = subprocess.run(
                    [sys.executable, name],
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

    def test_did_not_remint_leftover_receipts_or_add_login(self) -> None:
        for rel, prefix in KEEP_UNREAD.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel}: want {prefix} got {blob[:8]}",
            )
        door = (ROOT / "merge-on-pr.html").read_text(encoding="utf-8")
        self.assertIn("No login", door)
        self.assertNotIn("oauth", door.lower())
        self.assertFalse((ROOT / "marketplace.html").exists())
        self.assertFalse((ROOT / "qualify.html").exists())


if __name__ == "__main__":
    unittest.main()
