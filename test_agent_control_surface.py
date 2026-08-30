#!/usr/bin/env python3
from __future__ import annotations

import json
import unittest
from pathlib import Path

from host import agent_control_surface as surface


class AgentControlSurfaceTests(unittest.TestCase):
    def fixtures(self) -> tuple[dict, dict, list, dict]:
        discovery = {
            "schema": "commons-agent-discovery/v1",
            "contact_methods": [
                {"type": "action-pad", "url": "https://example.test/action", "preferred": True},
                {"type": "mcp", "url": "https://example.test/mcp", "preferred": False},
            ],
            "continuity": {"pulse": "pulse.json", "recent": "recent.json"},
        }
        pulse = {"seq": 42, "head": "a" * 40, "ts": "2026-08-29T00:00:00Z"}
        recent = [
            {"id": "r1", "from": "GROK", "to": "TABLE", "ts": "now", "state": "DURABLE_PAGE", "href": "p/r1.html", "body": "first line\nprivate detail"},
        ]
        ledger = {
            "schema": "commons-resource-ledger/v2",
            "snapshot": {"observed_at": "now"},
            "surfaces": [
                {"name": "grok", "kind": "SUBSCRIPTION", "stage": "PRODUCING", "condition": "LIVE", "consumer": "builds"},
                {"name": "swarm", "kind": "AGENT_ROUTER", "stage": "EXERCISED", "condition": "LIVE", "consumer": "agents"},
                {"name": "repo", "kind": "REPOSITORY", "stage": "PRODUCING", "condition": "LIVE"},
            ],
        }
        return discovery, pulse, recent, ledger

    def test_compiles_compact_provider_neutral_read_model(self) -> None:
        compiled = surface.compile_surface(*self.fixtures())
        self.assertEqual(compiled["schema"], "commons-agent-control-surface/v1")
        self.assertEqual(compiled["access"], "open")
        self.assertEqual(compiled["head"], "a" * 40)
        self.assertEqual([row["name"] for row in compiled["providers"]], ["grok", "swarm"])
        self.assertNotIn("repo", json.dumps(compiled["providers"]))
        self.assertEqual(compiled["recent"][0]["summary"], "first line")
        self.assertEqual([row["id"] for row in compiled["commands"]], ["action-pad", "mcp"])
        self.assertTrue(compiled["design"]["provider_specific_runtime_stays_behind_driver"])

    def test_compilation_is_deterministic(self) -> None:
        first = surface.canonical(surface.compile_surface(*self.fixtures()))
        second = surface.canonical(surface.compile_surface(*self.fixtures()))
        self.assertEqual(first, second)

    def test_rejects_non_list_recent_with_a_clear_validation_error(self) -> None:
        discovery, pulse, _, ledger = self.fixtures()
        for malformed in ({"id": "not-a-list"}, 7, None):
            with self.subTest(malformed=malformed):
                with self.assertRaisesRegex(ValueError, "recent"):
                    surface.compile_surface(discovery, pulse, malformed, ledger)

    def test_mobile_page_projects_the_live_commons_sources(self) -> None:
        text = Path("agent-control.html").read_text(encoding="utf-8")
        self.assertIn('name="viewport"', text)
        for source in ("agent-discovery.json", "pulse.json", "recent.json", "ground/RESOURCE_LEDGER.json"):
            self.assertIn(source, text)
        self.assertNotIn("agent-control.json", text)
        self.assertIn('href="action.html"', text)
        self.assertIn('href="boards.html"', text)
        self.assertIn('href="./index.html"', text)
        self.assertIn('name="robots"', text)
        self.assertIn("index,follow", text)
        self.assertNotIn("login", text.lower())
        self.assertNotIn("allowlist", text.lower())
        self.assertNotIn("authorization", text.lower())


if __name__ == "__main__":
    unittest.main()
