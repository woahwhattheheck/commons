"""Malformed JSON containers must report validation errors before projection."""

import copy
import json
import tempfile
import unittest
from pathlib import Path

from host import agent_discovery


class AgentDiscoveryMalformedContainerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = agent_discovery.load_registry()

    def assert_rejected(self, registry, field) -> None:
        before = copy.deepcopy(registry)
        errors = agent_discovery.validate(registry)
        self.assertIn(field, errors)
        self.assertEqual(errors, sorted(set(errors)))
        with self.assertRaisesRegex(ValueError, "^INVALID "):
            agent_discovery.projections(registry)
        self.assertEqual(registry, before)

    def test_contact_and_capability_containers_must_be_lists(self) -> None:
        for field in ("contact_methods", "capabilities"):
            for value in (None, False, True, 0, 1, 0.5, "", "invalid", {}, {"id": "x"}):
                with self.subTest(field=field, value=value):
                    registry = copy.deepcopy(self.registry)
                    registry[field] = value
                    self.assert_rejected(registry, field)

    def test_interoperability_container_must_be_an_object(self) -> None:
        for value in (None, False, True, 0, 1, 0.5, "", "invalid", [], ["formats"]):
            with self.subTest(value=value):
                registry = copy.deepcopy(self.registry)
                registry["interoperability"] = value
                self.assert_rejected(registry, "interoperability")

    def test_formats_container_must_be_a_list(self) -> None:
        values = (None, False, True, 0, 1, 0.5, "", " ".join(agent_discovery.OUTPUTS),
                  {}, dict.fromkeys(agent_discovery.OUTPUTS, True))
        for value in values:
            with self.subTest(value=value):
                registry = copy.deepcopy(self.registry)
                registry["interoperability"]["formats"] = value
                self.assert_rejected(registry, "interoperability.formats")

    def test_formats_must_contain_only_strings(self) -> None:
        for value in (None, False, 1, {}, []):
            with self.subTest(value=value):
                registry = copy.deepcopy(self.registry)
                registry["interoperability"]["formats"].append(value)
                self.assert_rejected(registry, "interoperability.formats")

    def test_bad_rows_still_have_existing_field_diagnostics(self) -> None:
        registry = copy.deepcopy(self.registry)
        registry["contact_methods"] = [None]
        registry["capabilities"] = [None]
        registry["interoperability"]["formats"] = []
        errors = agent_discovery.validate(registry)
        self.assertIn("contact_methods.$.row", errors)
        self.assertIn("capabilities.0.row", errors)
        for output in agent_discovery.OUTPUTS:
            self.assertIn(f"interoperability.formats:{output}", errors)

    def test_generation_rejects_invalid_containers_without_writing_outputs(self) -> None:
        for field in ("contact_methods", "capabilities", "interoperability"):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                registry = copy.deepcopy(self.registry)
                registry[field] = 1
                (root / "agent-discovery.json").write_text(json.dumps(registry), encoding="utf-8")
                sentinel = root / "agents.txt"
                sentinel.write_text("keep existing bytes\n", encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "^INVALID "):
                    agent_discovery.generate(root)
                self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep existing bytes\n")
                self.assertEqual(sorted(path.name for path in root.iterdir()),
                                 ["agent-discovery.json", "agents.txt"])


if __name__ == "__main__":
    unittest.main()
