#!/usr/bin/env python3

import json
import tempfile
import unittest
from pathlib import Path

from host import agent_discovery


class AgentDiscoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = agent_discovery.load_registry()

    def test_registry_is_valid_and_public(self) -> None:
        self.assertEqual(agent_discovery.validate(self.registry), [])
        self.assertEqual(self.registry["runtime_signals"]["discovery_state"], "open")
        self.assertEqual(self.registry["runtime_signals"]["runtime_access"], "public")
        self.assertTrue(all(row["url"].startswith(("https://", "mailto:")) for row in self.registry["contact_methods"]))

    def test_projection_is_deterministic_and_well_known_copies_match(self) -> None:
        first = agent_discovery.projections(self.registry)
        second = agent_discovery.projections(json.loads(json.dumps(self.registry)))
        self.assertEqual(first, second)
        self.assertEqual(first["agent.json"], first[".well-known/agent.json"])
        self.assertEqual(first["agents.json"], first[".well-known/agents.json"])

    def test_generate_then_check_exact_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "agent-discovery.json").write_text(json.dumps(self.registry), encoding="utf-8")
            agent_discovery.generate(root)
            self.assertEqual(agent_discovery.check(root), [])
            (root / "agents.txt").write_text("stale", encoding="utf-8")
            self.assertEqual(agent_discovery.check(root), ["agents.txt"])

    def test_continuity_capsule_starts_with_capability_map_and_points_to_receipts(self) -> None:
        capsule = json.loads(agent_discovery.projections(self.registry)["continuity.json"])
        self.assertEqual(capsule["startup_order"][0], "harnesses/catalog.json")
        self.assertIn("boards.html", capsule["startup_order"])
        self.assertIn("discover_commons_capabilities", capsule["instruction"])
        self.assertTrue(capsule["receipts"].endswith("/tree/main/p"))
        self.assertEqual(capsule["runtime_signals"]["source_of_truth"], "git-head")

    def test_machine_surfaces_advertise_existing_roads_without_claiming_a2a_runtime(self) -> None:
        projected = agent_discovery.projections(self.registry)
        card = json.loads(projected["agent.json"])
        skills = {row["id"] for row in card["skills"]}
        self.assertEqual(skills, {"discover", "publish", "execute", "collaborate", "commerce"})
        self.assertNotIn("A2A", self.registry["interoperability"]["protocols"])
        self.assertIn("https://commons-spark-mcp.vercel.app/mcp", projected["agents.txt"])
        self.assertIn("harnesses/catalog.json", projected["agents.txt"])


if __name__ == "__main__":
    unittest.main()
