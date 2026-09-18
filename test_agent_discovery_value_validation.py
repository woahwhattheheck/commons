"""Reject malformed rendered values before generating discovery surfaces."""

import copy
import json
import tempfile
import unittest
from pathlib import Path

from host import agent_discovery


class AgentDiscoveryValueValidationTests(unittest.TestCase):
    CONTINUITY_FIELDS = ("pulse", "recent", "receipts", "instruction")
    URL_FIELDS = ("homepage", "repository", "contact")

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

    def set_url(self, registry, field, value) -> str:
        if field == "contact":
            registry["contact_methods"][0]["url"] = value
            return "contact_methods.$.url"
        registry["identity"][field] = value
        return "identity"

    def test_continuity_rendered_fields_require_strings(self) -> None:
        values = (None, False, True, 0, 1, 0.5, {}, {"url": "x"}, [], ["x"])
        for field in self.CONTINUITY_FIELDS:
            for value in values:
                with self.subTest(field=field, value=value):
                    registry = copy.deepcopy(self.registry)
                    registry["continuity"][field] = value
                    self.assert_rejected(registry, f"continuity.{field}")

    def test_continuity_empty_and_blank_strings_remain_invalid(self) -> None:
        for field in self.CONTINUITY_FIELDS:
            for value in ("", " ", "\t\n"):
                with self.subTest(field=field, value=value):
                    registry = copy.deepcopy(self.registry)
                    registry["continuity"][field] = value
                    self.assert_rejected(registry, f"continuity.{field}")

    def test_malformed_urls_return_field_diagnostics(self) -> None:
        values = ("https://[", "https://example.org]", "https://[not-ipv6]/",
                  "https://exa\uff0fmple.org/")
        for field in self.URL_FIELDS:
            for value in values:
                with self.subTest(field=field, value=value):
                    registry = copy.deepcopy(self.registry)
                    diagnostic = self.set_url(registry, field, value)
                    self.assert_rejected(registry, diagnostic)

    def test_valid_urls_and_unicode_continuity_are_preserved(self) -> None:
        for url in ("https://example.org/path?q=1", "https://[::1]/", "mailto:agent@example.org"):
            with self.subTest(url=url):
                registry = copy.deepcopy(self.registry)
                self.set_url(registry, "contact", url)
                registry["continuity"]["instruction"] = "  Read caf\u00e9 receipts.  "
                before = copy.deepcopy(registry)
                self.assertEqual(agent_discovery.validate(registry), [])
                rendered = agent_discovery.projections(registry)
                self.assertIn(url, rendered["agents.txt"])
                self.assertIn("instruction:   Read caf\u00e9 receipts.  ", rendered["agents.txt"])
                self.assertEqual(registry, before)

    def test_generate_refuses_invalid_values_without_touching_outputs(self) -> None:
        cases = [("continuity", field) for field in self.CONTINUITY_FIELDS]
        cases.extend(("url", field) for field in self.URL_FIELDS)
        for kind, field in cases:
            with self.subTest(kind=kind, field=field), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                registry = copy.deepcopy(self.registry)
                if kind == "continuity":
                    registry["continuity"][field] = 1
                else:
                    self.set_url(registry, field, "https://[")
                (root / "agent-discovery.json").write_text(json.dumps(registry), encoding="utf-8")
                (root / "agents.txt").write_bytes(b"keep existing output\n")
                before = {str(path.relative_to(root)): path.read_bytes() for path in root.rglob("*") if path.is_file()}
                with self.assertRaisesRegex(ValueError, "^INVALID "):
                    agent_discovery.generate(root)
                after = {str(path.relative_to(root)): path.read_bytes() for path in root.rglob("*") if path.is_file()}
                self.assertEqual(after, before)
                self.assertFalse((root / ".well-known").exists())


if __name__ == "__main__":
    unittest.main()
