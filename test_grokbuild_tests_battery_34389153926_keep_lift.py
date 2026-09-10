#!/usr/bin/env python3
"""Living KEEP pins of reminted shared files must match current blobs.

Battery run 34389153926 (PR #11346 spy/ground-batch-live-cash-20260909-18)
failed 247 files. Dominant cause: leftover KEEP 8-char prefixes lagged
autogtm.html (want fab1d536 got dbbc96a5 then 2fe108f4) and related living
surfaces. Do not remint leftover receipts. Lift only living KEEP prefixes
and close the graph. Historical SOURCE_REV maps stay on their frozen trees.
"""

from __future__ import annotations

import ast
import importlib.util
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
KEEP_RE = re.compile(r"^KEEP\s*=\s*\{", re.M)
TARGETS = (
    "autogtm.html",
    "ground/OWNER_NOW.md",
    "commerce-agents.html",
    "commons-slack.html",
    "lanes.json",
)
SKIP_HISTORICAL = {
    "test_cursor_webmcp_adapter_keep_lift_battery.py",
}
ORIGINALS = (
    "test_commerce_agents.py",
    "test_autogtm_door_hub_readback_ack.py",
    "test_stealable_lanes.py",
    "test_spy_ground_batch_live_cash_20260909_18.py",
    "test_commons_slack_full_body.py",
    "test_owner_now_revenue.py",
    "test_open_door_guard.py",
)


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


class TestGrokbuildTestsBattery34389153926KeepLift(unittest.TestCase):
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
        self.assertGreaterEqual(pinned_by["autogtm.html"], 20)
        self.assertGreaterEqual(pinned_by["ground/OWNER_NOW.md"], 20)
        self.assertEqual(stale, [], msg="\n".join(stale))

    def test_autogtm_live_cash_door_stays_open(self) -> None:
        text = (ROOT / "autogtm.html").read_text(encoding="utf-8")
        self.assertIn('id="live-cash"', text)
        self.assertIn("agent-rescue.html", text)
        self.assertNotIn('type="password"', text)
        self.assertNotIn("Authorization", text)

    def test_slack_door_regeneration_matches_committed_bytes(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "commons_slack_full_body",
            ROOT / "host/commons_slack_full_body.py",
        )
        assert spec and spec.loader
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        door = (ROOT / "commons-slack.html").read_text(encoding="utf-8")
        self.assertEqual(mod.render_html(), door)
        self.assertIn('id="live-cash"', door)
        self.assertIn("Larger fixed engagements", door)

    def test_originally_failing_contracts_pass(self) -> None:
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

    def test_did_not_remint_leftover_receipts(self) -> None:
        leftover = ROOT / "p/cursor-claude-commerce-agents-20260902-01.md"
        self.assertTrue(leftover.is_file())
        blob = git_blob("p/cursor-claude-commerce-agents-20260902-01.md")
        self.assertTrue(blob.startswith("3e48f691"), leftover)


if __name__ == "__main__":
    unittest.main()
