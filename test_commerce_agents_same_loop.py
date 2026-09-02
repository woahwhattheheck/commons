#!/usr/bin/env python3
"""Unique same-loop remainder. Do not remint leftover clone pin."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SPEC_PATH = ROOT / "host" / "commerce_agents_same_loop.py"

import importlib.util

SPEC = importlib.util.spec_from_file_location("commerce_agents_same_loop", SPEC_PATH)
assert SPEC and SPEC.loader
loop = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(loop)

KEEP = {
    "p/cursor-claude-commerce-agents-20260902-01.md": "3e48f691",
    "host/commerce_agents.py": "8d2ddf29",
    "test_commerce_agents.py": "78a158b3",
    "commerce-agents.html": "e2028ddc",
    "ground/COMMERCE_AGENTS.json": "ab6f56a8",
    ".agents/skills/commerce-agents/SKILL.md": "1f93c4a2",
    "shots/cursor-big-things-incoming-hub-1-20260902.png": "ac761b7036834acf38c34b9a2eaa17170a590c4b",
    "shots/cursor-big-things-incoming-hub-2-20260902.png": "8eb5940f94a0875b1c653c0bbfcb3c3f33209ce1",
    "p/cursor-big-things-incoming-shots-20260902-01.md": "60b24eff",
    "p/cursor-big-things-incoming-alert-20260902-01.md": "fde94226",
    "p/cursor-what-a-pack-is-20260902-01.md": "a4e4dd89",
    "host/autogtm_same_loop.py": "18b120c7",
    "autogtm.html": "9d8b3e85",
    "host/payment_capability.py": "04c36e43",
    "p/cursor-harborline-qualify-live-probe-20260902-01.md": "92c4e31f",
    "p/cursor-harborline-pack-market-render-20260902-01.md": "54c348dc",
    "door.js": "dc59355d",
    "hub_pages.py": "5ac12648",
    "ground/OWNER_NOW.md": "59b1fd37",
    "host/slack_mirror.py": "8d3a5e0b",
    "CLAUDE.md": "2e11d96a",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


def fake_200(_url: str) -> tuple[int, str]:
    return 200, "<html>commerce-agents</html>"


def fake_down(_url: str) -> tuple[int, str]:
    return 0, "network down"


class TestCommerceAgentsSameLoop(unittest.TestCase):
    def test_shopper_retail_stages_checkout_and_never_sends(self) -> None:
        row = loop.measure(agent="shopper", vertical="retail", opener=fake_200)
        self.assertEqual(row["state"], "INTEGRATED")
        self.assertEqual(row["rides_leftover"], "cursor-claude-commerce-agents-20260902-01")
        self.assertEqual(row["leftover"]["verdict"], "RENDER")
        self.assertEqual(row["agent"], "shopper")
        self.assertEqual(row["checkout"]["state"], "STAGED_HOST_HANDOFF")
        self.assertEqual(row["checkout"]["host_door"], "payment-capability.html")
        self.assertFalse(row["checkout"]["model_sees_url"])
        self.assertFalse(row["checkout"]["invented_url"])
        self.assertFalse(row["sent"])
        self.assertEqual(row["cash_usd"], 0)
        self.assertTrue(row["no_auth"])
        self.assertFalse(row["copied_tree"])
        self.assertGreaterEqual(len(row["hits"]), 1)

    def test_merchant_writes_stay_staged(self) -> None:
        row = loop.measure(agent="merchant", vertical="travel", opener=fake_200)
        self.assertEqual(row["steps"], list(loop.MERCHANT_STEPS))
        self.assertEqual(row["writes"]["state"], "STAGED")
        self.assertFalse(row["writes"]["applied"])

    def test_unknown_vertical_is_finder_failed_not_zero(self) -> None:
        with self.assertRaises(ValueError):
            loop.choose_vertical("lottery")

    def test_twin_miss_is_finder_failed_never_silent_zero(self) -> None:
        row = loop.measure(opener=fake_down)
        self.assertEqual(row["open_twin"]["state"], "FINDER-FAILED")
        self.assertEqual(row["open_twin"]["http"], 0)
        self.assertIn("never silent 0", row["open_twin"]["note"])

    def test_send_go_charge_live_plugin_refused(self) -> None:
        for flag in ("--send", "--go", "--charge", "--live", "--claude-plugin"):
            with self.subTest(flag=flag):
                self.assertEqual(loop.main([flag, "--json"]), 2)

    def test_unknown_flag_is_finder_failed(self) -> None:
        self.assertEqual(loop.main(["--explode", "--json"]), 1)

    def test_cites_open_twin_and_named_flows(self) -> None:
        self.assertEqual(loop.OPEN_TWIN, "https://github.com/anthropics/commerce-agents")
        self.assertEqual(loop.LEFTOVER_ID, "cursor-claude-commerce-agents-20260902-01")
        self.assertEqual(loop.VERTICALS, ("retail", "travel", "telecom", "entertainment"))

    def test_slack_file_bytes_named_finder_failed(self) -> None:
        row = loop.measure(opener=fake_200)
        slack = row["slack_file"]
        self.assertEqual(slack["id"], "F0BUL9V9Z34")
        self.assertEqual(slack["bytes"], "FINDER-FAILED")
        self.assertTrue(slack["never_silent_0"])

    def test_keep_unread_leftovers_not_reminted(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                "%s moved: got %s want prefix %s" % (rel, blob, prefix),
            )
        self.assertFalse((ROOT / "CLAUDE_CORNER.md").exists())
        leftover_catalog = json.loads(
            (ROOT / "ground/COMMERCE_AGENTS.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            leftover_catalog["id"], "cursor-claude-commerce-agents-20260902-01"
        )

    def test_unique_loop_door_has_no_login(self) -> None:
        door = (ROOT / "commerce-agents-loop.html").read_text(encoding="utf-8")
        leftover_door = (ROOT / "commerce-agents.html").read_text(encoding="utf-8")
        self.assertIn('href="./index.html"', door)
        self.assertNotIn('type="password"', door)
        self.assertIn("No login", door)
        self.assertIn("commerce_agents_same_loop.py", door)
        self.assertIn("Possessing the link is enough", leftover_door)
        self.assertNotIn("commerce_agents_same_loop.py", leftover_door)

    def test_does_not_remint_autogtm_or_steal_harborline(self) -> None:
        row = loop.measure(opener=fake_200)
        self.assertIn("cursor-claude-commerce-agents-20260902-01", row["do_not_remint"])
        self.assertIn("cursor-what-a-pack-is-20260902-01", row["do_not_remint"])
        self.assertIn("door.js", row["do_not_remint"])
        catalog = json.loads(
            (ROOT / "ground/COMMERCE_AGENTS_SAME_LOOP.json").read_text(encoding="utf-8")
        )
        ids = {item["id"] for item in catalog["offers"]}
        self.assertNotIn("harborline-local-sites", ids)
        self.assertNotIn("marketplace.html", json.dumps(catalog))

    def test_skill_and_receipt_exist(self) -> None:
        token = (ROOT / "ground/tokens/commerce-agents.md").read_text(encoding="utf-8")
        receipt = (ROOT / "p/cursor-big-huge-commerce-agents-20260902-01.md").read_text(
            encoding="utf-8"
        )
        leftover_skill = (
            ROOT / ".agents/skills/commerce-agents/SKILL.md"
        ).read_text(encoding="utf-8")
        self.assertIn("F0BUL9V9Z34", token)
        self.assertIn("id: cursor-big-huge-commerce-agents-20260902-01", receipt)
        self.assertIn("cursor-claude-commerce-agents-20260902-01", receipt)
        self.assertIn("host/commerce_agents.py", leftover_skill)
        self.assertNotIn("commerce_agents_same_loop.py", leftover_skill)


if __name__ == "__main__":
    unittest.main()
