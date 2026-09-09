#!/usr/bin/env python3
"""Living KEEP pins of shared reminted files must match current blobs.

Battery run 34387708942 failed because leftover KEEP prefixes lagged
host/slack_mirror.py, webmcp.html, lanes.json, boards.html, and related
live-cash / titanmcp successor files. Goat sidewalk reverse-apply lagged
the titanmcp pad pointer. Do not remint leftover receipts. Lift only the
living KEEP prefixes. Historical SOURCE_REV maps stay on their frozen trees.
"""

from __future__ import annotations

import ast
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
KEEP_RE = re.compile(r"^KEEP\s*=\s*\{", re.M)
TARGETS = (
    "host/slack_mirror.py",
    "webmcp.html",
    "lanes.json",
    "boards.html",
    ".agents/skills/autogtm/SKILL.md",
    "ground/tokens/super-mcp.md",
    "commons-slack.html",
)
SKIP_HISTORICAL = {
    "test_cursor_webmcp_adapter_keep_lift_battery.py",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


def is_historical(text: str) -> bool:
    return "SOURCE_REV" in text and (
        "rev-parse" in text or "SOURCE_REV:" in text or "git show" in text
    )


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


def iter_living_keep_maps() -> list[tuple[str, dict[str, str]]]:
    maps: list[tuple[str, dict[str, str]]] = []
    for path in sorted(ROOT.glob("test_*.py")):
        if path.name in SKIP_HISTORICAL:
            continue
        text = path.read_text(encoding="utf-8")
        if is_historical(text):
            continue
        keep = parse_keep(text)
        if keep:
            maps.append((path.name, keep))
    return maps


class TestGrokbuildSharedKeepGraph34387708942(unittest.TestCase):
    def test_living_keep_pins_of_shared_remints_match_current_blobs(self) -> None:
        blobs = {rel: git_blob(rel) for rel in TARGETS}
        stale: list[str] = []
        pinned_by = {rel: 0 for rel in TARGETS}
        for carrier, keep in iter_living_keep_maps():
            for rel, prefix in keep.items():
                blob = blobs.get(rel)
                if blob is None:
                    continue
                pinned_by[rel] += 1
                if not blob.startswith(prefix):
                    stale.append(
                        f"{carrier} pins {rel} want {prefix} got {blob[:8]}"
                    )
        self.assertGreaterEqual(pinned_by["host/slack_mirror.py"], 5)
        self.assertGreaterEqual(pinned_by["webmcp.html"], 3)
        self.assertGreaterEqual(pinned_by["lanes.json"], 3)
        self.assertGreaterEqual(pinned_by["boards.html"], 2)
        self.assertEqual(stale, [], msg="\n".join(stale))

    def test_goat_sidewalk_reverse_applies_titanmcp_pad_pointer(self) -> None:
        import sys

        sys.path.insert(0, str(ROOT / "host"))
        import goat_sidewalk_door_match as match  # noqa: WPS433

        result = match.classify_match()
        self.assertEqual(result["door_baseline_blob"], "638e60b4")
        self.assertIn("titanmcp-pad-pointer-v1", result["door_successors"])
        self.assertTrue(result["match_ok"])


if __name__ == "__main__":
    unittest.main()
