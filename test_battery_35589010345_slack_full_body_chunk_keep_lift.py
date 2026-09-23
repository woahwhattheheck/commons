#!/usr/bin/env python3
"""Item-7 living KEEP pins must match current blobs after ingest remint.

Battery run 35589010345 failed test_commons_slack_full_body_chunk.py:
chunk/ship KEEP still froze slack_ingest.py a35169fe, catalog 5b2bf0e0,
and leftover tests 6a66d3f8 after the ingest rate-limit remint and two
incomplete pin lifts. Close the item-7 cluster including chunk readback.
Do not remint leftover receipts or the 5000-char slack_mirror split.
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
    "slack_ingest.py",
    "ground/COMMONS_SLACK_FULL_BODY.json",
    "test_commons_slack_full_body.py",
    "ground/COMMONS_SLACK_FULL_BODY_CHUNK.json",
    "test_commons_slack_full_body_chunk.py",
)
CLUSTER = (
    "test_commons_slack_full_body.py",
    "test_commons_slack_full_body_chunk.py",
    "test_commons_slack_full_body_ship.py",
    "test_cursor_commons_slack_full_body_chunk_readback.py",
    "ground/COMMONS_SLACK_FULL_BODY.json",
    "ground/COMMONS_SLACK_FULL_BODY_CHUNK.json",
)
ORIGINALS = (
    "test_commons_slack_full_body_chunk.py",
    "test_commons_slack_full_body.py",
    "test_commons_slack_full_body_ship.py",
    "test_commons_slack_full_body_exact_ids.py",
    "test_cursor_commons_slack_full_body_chunk_readback.py",
)
KEEP_UNREAD = {
    "p/cursor-commons-slack-full-body-20260902-01.md": "86f4eddc",
    "p/cursor-commons-slack-full-body-chunk-20260902-01.md": "94770f41",
    "host/slack_mirror.py": "72c0844e",
    "host/commons_slack_full_body.py": "7a6067d7",
    "commons-slack.html": "b7630b56",
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
        path = ROOT / rel
        if rel.endswith(".json"):
            data = json.loads(path.read_text(encoding="utf-8"))
            keep = data.get("keep_unread")
            if isinstance(keep, dict):
                maps.append(
                    (rel, {str(key): str(prefix) for key, prefix in keep.items()})
                )
            continue
        keep = parse_keep(path.read_text(encoding="utf-8"))
        if keep:
            maps.append((rel, keep))
    return maps


class TestBattery35589010345SlackFullBodyChunkKeepLift(unittest.TestCase):
    def test_item7_cluster_keep_pins_match_current_blobs(self) -> None:
        blobs = {rel: git_blob(rel) for rel in TARGETS}
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
        self.assertGreaterEqual(pinned_by["slack_ingest.py"], 3)
        self.assertGreaterEqual(pinned_by["ground/COMMONS_SLACK_FULL_BODY.json"], 3)
        self.assertGreaterEqual(pinned_by["test_commons_slack_full_body.py"], 3)
        self.assertGreaterEqual(
            pinned_by["ground/COMMONS_SLACK_FULL_BODY_CHUNK.json"], 1
        )
        self.assertGreaterEqual(pinned_by["test_commons_slack_full_body_chunk.py"], 1)
        self.assertEqual(stale, [], msg="\n".join(stale))

    def test_chunk_helper_renders_without_login(self) -> None:
        proc = subprocess.run(
            [sys.executable, "host/commons_slack_full_body_chunk.py", "--json"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        packet = json.loads(proc.stdout)
        self.assertEqual(packet["verdict"], "RENDER", packet)
        self.assertEqual(packet["channel_limit"], 4000)
        self.assertEqual(packet["leftover_slack_limit_keep"], 5000)
        self.assertFalse(packet["login"])
        self.assertFalse(packet["gate"])
        self.assertFalse(packet["cursor_advanced"])
        self.assertEqual(packet["sends"], 0)
        self.assertEqual(packet.get("errors") or [], [])

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
        mirror = (ROOT / "host/slack_mirror.py").read_text(encoding="utf-8")
        self.assertIn("SLACK_LIMIT = 5000", mirror)
        door = (ROOT / "commons-slack-chunk.html").read_text(encoding="utf-8")
        self.assertIn("No login", door)
        self.assertIn("Possessing the link is enough", door)
        self.assertNotIn("Authorization", door)
        self.assertFalse((ROOT / "marketplace.html").exists())
        self.assertFalse((ROOT / "qualify.html").exists())


if __name__ == "__main__":
    unittest.main()
