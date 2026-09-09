#!/usr/bin/env python3
"""KEEP pins of the PR11108/11113 reminted root and dependent must stay current.

Do not remint those leftovers; lift only the dependent KEEP prefixes.
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
    "test_grokbuild_main_range_verify_33717084528_billing_lock.py",
    "test_grokbuild_pr8583_already_merged_verify.py",
)


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
                    return {
                        str(key): str(prefix)
                        for key, prefix in value.items()
                    }
                return None
    return None


def iter_keep_maps() -> list[tuple[str, dict[str, str]]]:
    maps: list[tuple[str, dict[str, str]]] = []
    for path in sorted(ROOT.glob("test_*.py")):
        keep = parse_keep(path.read_text(encoding="utf-8"))
        if keep:
            maps.append((path.name, keep))
    return maps


class TestGrokbuildPr8583RootKeepGraph(unittest.TestCase):
    def test_all_keep_pins_of_reminted_root_and_dependent_match_current_blobs(
        self,
    ) -> None:
        blobs = {rel: git_blob(rel) for rel in TARGETS}
        stale = []
        pinned_by = {rel: 0 for rel in TARGETS}
        for carrier, keep in iter_keep_maps():
            for rel, prefix in keep.items():
                blob = blobs.get(rel)
                if blob is None:
                    continue
                pinned_by[rel] += 1
                if not blob.startswith(prefix):
                    stale.append(
                        f"{carrier} pins {rel} want {prefix} got {blob[:8]}"
                    )
        self.assertGreaterEqual(pinned_by[TARGETS[0]], 13)
        self.assertGreaterEqual(pinned_by[TARGETS[1]], 1)
        self.assertEqual(stale, [], msg="\n".join(stale))


if __name__ == "__main__":
    unittest.main()
