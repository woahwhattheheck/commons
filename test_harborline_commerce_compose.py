#!/usr/bin/env python3
"""Pin Harborline commerce compose leftover. Do not remint LEAD or /market."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HELPER = ROOT / "host/harborline_commerce_compose.py"
RECEIPT = ROOT / "p/cursor-harborline-commerce-compose-20260902-01.md"

KEEP = {
    "p/cursor-claude-commerce-agents-20260902-01.md": "3e48f691",
    "host/commerce_agents.py": "8d2ddf29",
    "ground/COMMERCE_AGENTS.json": "ab6f56a8",
    "commerce-agents.html": "e2028ddc",
    ".agents/skills/commerce-agents/SKILL.md": "1f93c4a2",
    "test_commerce_agents.py": "78a158b3",
    "p/cursor-harborline-pack-market-render-20260902-01.md": "54c348dc",
    "host/harborline_pack_market_render.py": "cc9a3320",
    "p/cursor-what-a-pack-is-20260902-01.md": "a4e4dd89",
    "p/cursor-pack-is-ready-to-run-20260902-01.md": "897b00ba",
    "p/cursor-pack-quality-dictates-tier-20260902-01.md": "f2054b18",
    "packs/desk-website-service-20260902-01/instance.json": "f460d7bc",
    "packs/desk-website-service-20260902-01/checkout.md": "64633e36",
    "packs/desk-website-service-20260902-01/door.html": "d3d6fcc7",
    "autogtm.html": "9d8b3e85",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


def run_helper(*flags: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3", str(HELPER), *flags],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


class TestHarborlineCommerceCompose(unittest.TestCase):
    def test_keep_lead_unique_pack_and_harborline_leftovers(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )
        self.assertFalse(
            (ROOT / "p/cursor-big-huge-commerce-agents-20260902-01.md").exists()
        )
        self.assertFalse((ROOT / "marketplace.html").exists())

    def test_json_fills_cart_and_handoff_stays_finder_failed(self) -> None:
        proc = run_helper("--json")
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        packet = json.loads(proc.stdout)
        self.assertEqual(packet["id"], "cursor-harborline-commerce-compose-20260902-01")
        self.assertEqual(packet["cite"], "https://github.com/anthropics/commerce-agents")
        self.assertFalse(packet["copy_blueprint_source"])
        self.assertEqual(packet["lead_leftover"], "cursor-claude-commerce-agents-20260902-01")
        self.assertEqual(packet["desk_route"], "/shop")
        self.assertEqual(packet["over"], "/market")
        self.assertEqual(packet["product"]["title"], "Harborline Local Sites")
        self.assertEqual(packet["product"]["price_usd"], 200)
        self.assertTrue(packet["cart"]["filled"])
        self.assertEqual(packet["cart"]["lines"][0]["product_id"], "harborline-local-sites")
        self.assertIsNone(packet["checkout"]["model_visible"]["checkout_url"])
        self.assertFalse(packet["checkout"]["model_sees_url"])
        self.assertEqual(packet["checkout"]["host_only"]["checkout_handoff"]["state"], "FINDER-FAILED")
        self.assertIsNone(packet["checkout"]["host_only"]["checkout_handoff"]["url"])
        self.assertEqual(packet["merchant_staged"]["status"], "staged")
        self.assertFalse(packet["merchant_staged"]["applied"])
        self.assertEqual(packet["merchant_apply"]["gate"], "host_approval")
        self.assertFalse(packet["merchant_apply"]["applied"])
        self.assertEqual(packet["anthropic_api_key"]["state"], "FINDER-FAILED")
        self.assertFalse(packet["anthropic_api_key"]["called"])
        self.assertEqual(packet["sent"], 0)
        self.assertEqual(packet["cash"], 0)
        self.assertNotIn("buy.stripe.com", proc.stdout)
        blob = json.dumps(packet)
        self.assertNotIn("buy.stripe.com", blob)
        self.assertIn("search-discovery", packet["shopping_skills"])
        self.assertIn("catalog-listings", packet["merchant_skills"])

    def test_cart_provenance_blocks_unseen_ids(self) -> None:
        sys_path = str(ROOT / "host")
        spec = __import__("importlib.util").util.spec_from_file_location(
            "harborline_commerce_compose", HELPER
        )
        assert spec and spec.loader
        loop = __import__("importlib.util").util.module_from_spec(spec)
        spec.loader.exec_module(loop)
        session: dict = {"seen_ids": [], "cart": []}
        blocked = loop.add_to_cart("harborline-local-sites", session)
        self.assertEqual(blocked["status"], "blocked")
        self.assertEqual(blocked["gate"], "cart_provenance")
        self.assertFalse(blocked["filled"])
        hits = loop.search_discovery("harborline", session)
        self.assertEqual(hits[0]["product_id"], "harborline-local-sites")
        filled = loop.add_to_cart("harborline-local-sites", session)
        self.assertTrue(filled["filled"])

    def test_invented_stripe_token_stays_finder_failed(self) -> None:
        spec = __import__("importlib.util").util.spec_from_file_location(
            "harborline_commerce_compose", HELPER
        )
        assert spec and spec.loader
        loop = __import__("importlib.util").util.module_from_spec(spec)
        spec.loader.exec_module(loop)
        fake = loop.checkout_handoff("https://buy.stripe.com/fake-harborline")
        self.assertEqual(fake["state"], "FINDER-FAILED")
        self.assertIsNone(fake["url"])
        self.assertFalse(fake["model_sees_url"])
        self.assertFalse(fake["invented_stripe_urls"])
        empty = loop.checkout_handoff("")
        self.assertEqual(empty["state"], "FINDER-FAILED")
        self.assertIsNone(empty["url"])

    def test_send_go_dump_refused(self) -> None:
        for flag in ("--send", "--go", "--live", "--dump-commons", "--marketplace-html"):
            proc = run_helper(flag)
            self.assertEqual(proc.returncode, 2, msg=proc.stdout + proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertEqual(payload["sent"], 0)
            self.assertEqual(payload["cash"], 0)
            self.assertEqual(payload["refused"], flag)
            self.assertFalse(payload["invented_stripe_urls"])
        proc = run_helper("--not-a-real-flag")
        self.assertEqual(proc.returncode, 1)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["verdict"], "FINDER-FAILED")
        self.assertEqual(payload["sent"], 0)

    def test_receipt_does_not_steal(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        self.assertIn("cursor-harborline-commerce-compose-20260902-01", text)
        self.assertIn("cursor-claude-commerce-agents-20260902-01", text)
        self.assertIn("cursor-big-huge-commerce-agents-20260902-01", text)
        self.assertIn("54c348dc", text)
        self.assertIn("a4e4dd89", text)
        self.assertIn("f2054b18", text)
        self.assertIn("897b00ba", text)
        self.assertIn("/shop", text)
        self.assertIn("FINDER-FAILED", text)
        self.assertIn("Did not remint", text)
        self.assertNotIn("buy.stripe.com", text)
        self.assertNotIn("qualify.html", text)
        self.assertFalse((ROOT / "marketplace.html").exists())


if __name__ == "__main__":
    unittest.main()
