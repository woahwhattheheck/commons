#!/usr/bin/env python3
"""KEEP-lift leftover commerce-agents freeze after battery 35147646349.

PR #14971 already merged (`5a605f9`). Tip later KEEP-lifted tools.json, board
cash Larger-fixed, invoice checkout slot, slack-chunk helpers, and door-audit
tree. Unique leftover on current main: `test_commerce_agents_same_loop.py`
still froze `CLAUDE.md` at `22119134` after GROK harness-MD Larger-fixed
`858efbba`, and living sibling KEEP dicts still froze `test_commerce_agents.py`
at `cdd4b502` vs live `3fe99d86`. Lift living pins. Do not remint #14971.
"""
from __future__ import annotations

import ast
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CLAUDE_BLOB = "858efbba"
STALE_CLAUDE = "22119134"
AGENTS_BLOB = "8ca269cd"
STALE_AGENTS = "cdd4b502"
STALE_AGENTS_SHA = "07109651"
SAME_LOOP_BLOB = "f45d3a49"
STALE_SAME_LOOP = "6ffe17b0"
CARRIERS = (
    "test_commerce_agents_same_loop.py",
    "test_harborline_commerce_compose.py",
    "test_cursor_claude_commerce_agents_readback.py",
    "test_cursor_claude_commerce_agents_readback_ack.py",
    "test_cursor_big_huge_commerce_agents_readback.py",
    "test_cursor_harborline_commerce_compose_readback.py",
    "test_harborline_commerce_compose_keep_lift.py",
    "test_cursor_harborline_commerce_compose_keep_lift_readback.py",
    "test_grokbuild_pr8471_verify.py",
    "test_harborline_merchant_portal.py",
    "test_harborline_operator_library.py",
)
ORIGINALS = (
    "test_commerce_agents.py",
    "test_commerce_agents_same_loop.py",
    "test_coil_tools_super_mcp_fold.py",
    "test_board_cash_rebake.py",
    # ≠ MCP doors: do not remint door/ or commons_door_audit.json.
    "test_checkout_landing_integrity.py",
    "test_commons_slack_full_body_chunk.py",
    "test_harborline_commerce_compose.py",
)
KEEP_UNREAD = {
    "p/cursor-claude-commerce-agents-20260902-01.md": "3e48f691",
    "p/cursor-big-huge-commerce-agents-20260902-01.md": "fddb5a7c",
    "p/cursor-harborline-commerce-compose-keep-lift-20260902-01.md": "668dd5c4",
    "autogtm.html": "1009c4cd",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


def parse_keep(text: str) -> dict[str, str]:
    match = re.search(r"^KEEP\s*=\s*\{", text, re.M)
    if not match:
        return {}
    start = text.find("{", match.start())
    depth = 0
    for index, char in enumerate(text[start:], start):
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                value = ast.literal_eval(text[start : index + 1])
                if isinstance(value, dict):
                    return {str(key): str(prefix) for key, prefix in value.items()}
                return {}
    return {}


class TestWireBattery35147646349KeepLift(unittest.TestCase):
    def test_same_loop_keep_matches_tip_claude_md(self) -> None:
        keep = parse_keep(
            (ROOT / "test_commerce_agents_same_loop.py").read_text(encoding="utf-8")
        )
        self.assertEqual(keep.get("CLAUDE.md"), CLAUDE_BLOB)
        self.assertNotEqual(keep.get("CLAUDE.md"), STALE_CLAUDE)
        blob = git_blob("CLAUDE.md")
        self.assertTrue(blob.startswith(CLAUDE_BLOB), blob)
        self.assertFalse(blob.startswith(STALE_CLAUDE), blob)
        text = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertIn("Larger fixed engagements", text)
        self.assertIn("diagnostic.html", text)
        self.assertIn("commercial.html", text)
        cash = text[text.find("## Live cash") :] if "## Live cash" in text else text
        self.assertNotIn("buy.stripe.com", cash)

    def test_living_carriers_keep_tip_commerce_agents_blobs(self) -> None:
        agents = git_blob("test_commerce_agents.py")
        same_loop = git_blob("test_commerce_agents_same_loop.py")
        self.assertTrue(agents.startswith(AGENTS_BLOB), agents)
        self.assertFalse(agents.startswith(STALE_AGENTS), agents)
        self.assertFalse(agents.startswith(STALE_AGENTS_SHA), agents)
        self.assertTrue(same_loop.startswith(SAME_LOOP_BLOB), same_loop)
        self.assertFalse(same_loop.startswith(STALE_SAME_LOOP), same_loop)
        stale: list[str] = []
        for name in CARRIERS:
            keep = parse_keep((ROOT / name).read_text(encoding="utf-8"))
            if "test_commerce_agents.py" in keep:
                prefix = keep["test_commerce_agents.py"]
                if prefix in {STALE_AGENTS, STALE_AGENTS_SHA} or not agents.startswith(
                    prefix
                ):
                    stale.append(
                        f"{name} pins test_commerce_agents.py want {prefix} got {agents[:8]}"
                    )
            if "test_commerce_agents_same_loop.py" in keep:
                prefix = keep["test_commerce_agents_same_loop.py"]
                if prefix == STALE_SAME_LOOP or not same_loop.startswith(prefix):
                    stale.append(
                        f"{name} pins test_commerce_agents_same_loop.py want {prefix} got {same_loop[:8]}"
                    )
            if keep.get("CLAUDE.md") == STALE_CLAUDE:
                stale.append(f"{name} still freezes CLAUDE.md {STALE_CLAUDE}")
        self.assertEqual(stale, [], msg="\n".join(stale))

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

    def test_did_not_remint_leftover_receipts_or_invent_stripe(self) -> None:
        for rel, prefix in KEEP_UNREAD.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel}: want {prefix} got {blob[:8]}",
            )
        self.assertFalse((ROOT / ".cirrus.yml").exists())
        same_loop = (ROOT / "test_commerce_agents_same_loop.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("buy.stripe.com", same_loop)
        self.assertNotIn("337 NO", same_loop)


if __name__ == "__main__":
    unittest.main()
