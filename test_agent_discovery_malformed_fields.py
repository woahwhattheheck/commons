"""Malformed discovery fields should receive diagnostics, not parser crashes."""

import copy
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from host import agent_discovery


class AgentDiscoveryMalformedFieldTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = agent_discovery.load_registry()

    def assert_rejected(self, registry, field) -> None:
        before = copy.deepcopy(registry)
        self.assertIn(field, agent_discovery.validate(registry))
        with self.assertRaisesRegex(ValueError, "^INVALID "):
            agent_discovery.projections(registry)
        self.assertEqual(registry, before)

    def test_malformed_identity_urls_report_identity(self) -> None:
        for field in ("homepage", "repository"):
            for value in ("https://[", "https://example.com\uff1a443/"):
                with self.subTest(field=field, value=value):
                    registry = copy.deepcopy(self.registry)
                    registry["identity"][field] = value
                    self.assert_rejected(registry, "identity")

    def test_malformed_contact_urls_report_contact_field(self) -> None:
        for value in ("https://[", "https://example.com\uff1a443/"):
            with self.subTest(value=value):
                registry = copy.deepcopy(self.registry)
                registry["contact_methods"][0]["url"] = value
                self.assert_rejected(registry, "contact_methods.$.url")

    def test_existing_url_schemes_and_ipv6_remain_supported(self) -> None:
        for value in ("https://example.com/", "https://[::1]/", "mailto:agent@example.com"):
            with self.subTest(value=value):
                self.assertTrue(agent_discovery._public_url(value))
        for value in ("", "http://example.com/", "relative/path"):
            with self.subTest(value=value):
                self.assertFalse(agent_discovery._public_url(value))

    def test_continuity_rendered_fields_require_nonempty_text(self) -> None:
        for field in ("pulse", "recent", "receipts", "instruction"):
            for value in (None, False, True, 0, 1, 0.5, [], ["text"], {}, {"text": "x"}, "", " \n"):
                with self.subTest(field=field, value=value):
                    registry = copy.deepcopy(self.registry)
                    registry["continuity"][field] = value
                    self.assert_rejected(registry, f"continuity.{field}")
        registry = copy.deepcopy(self.registry)
        registry["continuity"]["instruction"] = "Read the capability map — then publish receipts."
        self.assertEqual(agent_discovery.validate(registry), [])
        self.assertIn(registry["continuity"]["instruction"], agent_discovery.projections(registry)["agents.txt"])

    def test_cli_validate_reports_invalid_without_traceback(self) -> None:
        for field, value, expected in (("identity", "https://[", "identity"),
                                        ("continuity", 1, "continuity.instruction")):
            with self.subTest(field=field):
                registry = copy.deepcopy(self.registry)
                if field == "identity":
                    registry[field]["homepage"] = value
                else:
                    registry[field]["instruction"] = value
                output = io.StringIO()
                with mock.patch.object(agent_discovery, "load_registry", return_value=registry), \
                        mock.patch("sys.argv", ["agent_discovery.py", "validate"]), \
                        redirect_stdout(output):
                    self.assertEqual(agent_discovery.main(), 1)
                self.assertIn(expected, output.getvalue())
                self.assertTrue(output.getvalue().startswith("INVALID "))

    def test_generation_rejects_invalid_fields_before_writing(self) -> None:
        for field in ("identity", "continuity"):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                registry = copy.deepcopy(self.registry)
                if field == "identity":
                    registry[field]["homepage"] = "https://["
                else:
                    registry[field]["instruction"] = 1
                (root / "agent-discovery.json").write_text(json.dumps(registry), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "^INVALID "):
                    agent_discovery.generate(root)
                self.assertEqual([path.name for path in root.iterdir()], ["agent-discovery.json"])


if __name__ == "__main__":
    unittest.main()
