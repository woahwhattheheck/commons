from __future__ import annotations

import ast
import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
LANE = ROOT / "orchestration" / "jeffersonville"
FRAMEWORKS = LANE / "frameworks.json"
SCHEMA = LANE / "adapter.schema.json"
TOPOLOGY = LANE / "topology.json"
PROBE = LANE / "probe.py"
PAGE = ROOT / "orchestration.html"
README = LANE / "README.md"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class JeffersonvilleCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = load_json(FRAMEWORKS)
        cls.schema = load_json(SCHEMA)
        cls.topology = load_json(TOPOLOGY)

    def test_all_json_artifacts_parse(self):
        self.assertIsInstance(self.catalog, dict)
        self.assertIsInstance(self.schema, dict)
        self.assertIsInstance(self.topology, dict)

    def test_framework_revisions_licenses_and_verdicts_are_pinned(self):
        expected = {
            "inception-core": ("https://github.com/nbursa/inception-core", "e8f4b13", "MIT", "REFERENCE_ONLY"),
            "multi-agent-engine": ("https://github.com/NickSpyker/multi-agent-engine", "ed540b8", "MIT OR Apache-2.0", "BENCHMARK_SCAFFOLD_ONLY"),
            "autoagents": ("https://github.com/liquidos-ai/AutoAgents", "6301004", "MIT OR Apache-2.0", "PILOT_CANDIDATE_AFTER_PATCH"),
            "swarms-rs": ("https://github.com/The-Swarm-Corporation/swarms-rs", "9d22ba9", "Apache-2.0", "HOLD"),
            "graphbit": ("https://github.com/InfinitiBit/graphbit", "f80c46e", "Apache-2.0", "BENCHMARK_CANDIDATE"),
            "sayiir": ("https://github.com/sayiir/sayiir", "7d60cee", "MIT", "DURABILITY_ADAPTER_CANDIDATE"),
            "agent-framework-go": ("https://github.com/microsoft/agent-framework-go", "8c8544a", "MIT", "CONTROL_PLANE_ADAPTER_CANDIDATE"),
            "aof": ("https://github.com/agenticdevops/aof", "bf15701", "Apache-2.0", "SCHEMA_AND_MCP_PATTERN_ONLY"),
            "rusty-agent": ("https://github.com/tmetsch/rusty_agent", "f07e7df", "MIT", "ARCHIVE_REFERENCE_ONLY")
        }
        actual = {
            record["id"]: (
                record["canonical_repository"],
                record["head_short_sha"],
                record["license"],
                record["verdict"]
            )
            for record in self.catalog["frameworks"]
        }
        self.assertEqual(actual, expected)
        self.assertTrue(all(len(record["head_short_sha"]) == 7 for record in self.catalog["frameworks"]))

    def test_misattribution_corrections_are_explicit(self):
        corrections = {
            item["incorrectly_attributed_to"]: item["corrected_source_candidate"]
            for item in self.catalog["misattribution_corrections"]
        }
        self.assertEqual(
            corrections,
            {
                "https://github.com/nbursa/inception-core": "https://github.com/scalarian/cathedral.fabric",
                "https://github.com/agenticdevops/aof": "https://github.com/raestrada/kumeo"
            }
        )

        candidates = {item["id"]: item for item in self.catalog["unverified_candidates"]}
        self.assertEqual(set(candidates), {"cathedral.fabric", "kumeo"})
        self.assertEqual(candidates["cathedral.fabric"]["head_short_sha"], "a98b290")
        self.assertEqual(candidates["cathedral.fabric"]["verdict"], "UNVERIFIED_LAB")
        self.assertEqual(candidates["kumeo"]["head_short_sha"], "1b90d5d")
        self.assertEqual(candidates["kumeo"]["license"], "GPL-3.0-or-later")
        self.assertEqual(candidates["kumeo"]["verdict"], "UNVERIFIED_REFERENCE")

    def test_every_catalog_and_topology_record_is_not_deployed(self):
        self.assertEqual(self.catalog["deployment_status"], "NOT_DEPLOYED")
        for group in ("frameworks", "misattribution_corrections", "unverified_candidates"):
            for record in self.catalog[group]:
                self.assertEqual(record["deployment_status"], "NOT_DEPLOYED")

        self.assertEqual(self.topology["deployment_status"], "NOT_DEPLOYED")
        for tier in self.topology["tiers"]:
            self.assertEqual(tier["deployment_status"], "NOT_DEPLOYED")
        for step in self.topology["plan_flow"]:
            self.assertEqual(step["deployment_status"], "NOT_DEPLOYED")

        boundary = self.topology["scope_boundary"]
        self.assertEqual(boundary["deployment_intent"], "NONE")
        self.assertEqual(boundary["facility_build_intent"], "NONE")
        self.assertEqual(boundary["rust_or_go_rewrite_intent"], "NONE")
        self.assertEqual(boundary["external_code_execution_intent"], "NONE")
        self.assertIn("no data-center build", boundary["statement"])

    def test_open_door_has_no_admission_gates(self):
        for policy in (
            self.catalog["open_door"],
            self.topology["open_door"],
            self.schema["x-open-door"]
        ):
            self.assertEqual(policy["participation_effect"], "NONE")
            self.assertIs(policy["descriptive_only"], True)
            self.assertEqual(policy["unknown_capabilities"], "ACCEPT_AND_DESCRIBE")

    def test_adapter_schema_is_permissive_and_descriptive(self):
        self.assertTrue(self.schema["additionalProperties"])
        capability_schema = self.schema["properties"]["capabilities"]
        self.assertTrue(capability_schema["additionalProperties"])
        observation_object = self.schema["$defs"]["capabilityObservation"]["oneOf"][1]
        self.assertTrue(observation_object["additionalProperties"])
        self.assertEqual(self.schema["x-catalog-mode"], "DESCRIPTIVE_ONLY")
        self.assertEqual(self.schema["x-deployment-status"], "NOT_DEPLOYED")

    def test_topology_is_reference_and_plan_only(self):
        self.assertEqual(
            self.topology["topology_kind"],
            "REFERENCE_ONLY_ADAPTER_AND_BENCHMARK_CATALOG"
        )
        self.assertTrue(
            all(tier["mode"] in {"REFERENCE_ONLY", "PLAN_ONLY", "UNVERIFIED_REFERENCE_ONLY"}
                for tier in self.topology["tiers"])
        )
        self.assertEqual(
            set(self.topology["probe_non_actions"]),
            {"CLONE_REPOSITORY", "INSTALL_DEPENDENCY", "RUN_EXTERNAL_CODE", "DEPLOY"}
        )

    def test_probe_is_stdlib_read_only_and_deterministic(self):
        source = PROBE.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported_roots = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_roots.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_roots.add(node.module.split(".")[0])
        self.assertTrue(imported_roots <= {"__future__", "json", "sys", "pathlib", "typing"})
        self.assertNotIn("write_text", source)
        self.assertNotIn("os.system", source)

        first = subprocess.run(
            [sys.executable, str(PROBE)],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True
        )
        second = subprocess.run(
            [sys.executable, str(PROBE)],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True
        )
        self.assertEqual(first.stdout, second.stdout)
        plan = json.loads(first.stdout)
        self.assertEqual(plan["deployment_status"], "NOT_DEPLOYED")
        self.assertEqual(len(plan["capability_plans"]), 11)
        self.assertEqual(
            [item["candidate_id"] for item in plan["benchmark_plans"]],
            ["graphbit", "multi-agent-engine"]
        )
        self.assertTrue(
            all(item["external_candidate_execution"] is False for item in plan["benchmark_plans"])
        )

    def test_crawler_visible_page_contract(self):
        html = PAGE.read_text(encoding="utf-8")
        first_four_kib = html[:4096].lower()
        self.assertIn('name="robots"', first_four_kib)
        self.assertIn("index,follow", first_four_kib)
        self.assertIn('href="./"', html)
        self.assertIn("Commons home", html)
        self.assertIn("NOT_DEPLOYED", html)
        self.assertIn("orchestration/jeffersonville/frameworks.json", html)
        self.assertIn("orchestration/jeffersonville/adapter.schema.json", html)
        self.assertIn("orchestration/jeffersonville/topology.json", html)

    def test_readme_repeats_operational_boundary(self):
        text = README.read_text(encoding="utf-8")
        self.assertIn("NOT_DEPLOYED", text)
        self.assertIn("not a data-center design", text)
        self.assertIn("Rust/Go rewrite", text)
        self.assertIn("no auth, identity, permission, approval, allowlist", text)

    def test_existing_mcp_exposes_catalog_resources_when_present(self):
        path = ROOT / "commons_mcp.py"
        if not path.is_file():
            return
        text = path.read_text(encoding="utf-8")
        for uri in (
            "commons://orchestration/jeffersonville/frameworks",
            "commons://orchestration/jeffersonville/topology",
            "commons://orchestration/jeffersonville/adapter-schema",
        ):
            self.assertIn(uri, text)


if __name__ == "__main__":
    unittest.main()
