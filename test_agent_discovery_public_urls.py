#!/usr/bin/env python3
"""Scheme-specific public URL validation for generated discovery surfaces."""
from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from host import agent_discovery


ROOT = Path(__file__).resolve().parent


class AgentDiscoveryPublicUrlTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = json.loads((ROOT / "agent-discovery.json").read_text(encoding="utf-8"))

    def test_current_registry_remains_valid_and_byte_stable(self) -> None:
        self.assertEqual(agent_discovery.validate(self.registry), [])
        projected = agent_discovery.projections(self.registry)
        self.assertEqual(projected["manifest.json"], agent_discovery.canonical(self.registry))
        self.assertIn("homepage: https://woahwhattheheck.github.io/commons/", projected["agents.txt"])

    def test_https_requires_an_absolute_authority(self) -> None:
        valid = (
            "https://example.com",
            "https://example.com/path?query=yes#fragment",
            "https://[2001:db8::1]/agent.json",
        )
        invalid = (
            "https:relative-path",
            "https:///missing-host",
            "https://",
            "https://:443/path",
            "https://example.com:bad/path",
        )
        for value in valid:
            with self.subTest(value=value):
                self.assertTrue(agent_discovery._public_url(value))
        for value in invalid:
            with self.subTest(value=value):
                self.assertFalse(agent_discovery._public_url(value))

    def test_mailto_requires_a_recipient_path_and_no_authority(self) -> None:
        valid = (
            "mailto:ops@example.com",
            "mailto:postmaster",
            "mailto:ops@example.com?subject=Hello",
        )
        invalid = (
            "mailto://example.com",
            "mailto:/ops@example.com",
            "mailto:",
            "mailto:?subject=Hello",
        )
        for value in valid:
            with self.subTest(value=value):
                self.assertTrue(agent_discovery._public_url(value))
        for value in invalid:
            with self.subTest(value=value):
                self.assertFalse(agent_discovery._public_url(value))

    def test_controls_and_whitespace_cannot_escape_agents_txt_lines(self) -> None:
        invalid = (
            " https://example.com",
            "https://example.com/space here",
            "https://example.com/\n[Contact Methods]",
            "https://example.com/\tother",
            "https://example.com/\x00other",
            "https://example.com\\other",
            "mailto:ops@example.com\rcontact: forged",
        )
        for value in invalid:
            with self.subTest(value=repr(value)):
                self.assertFalse(agent_discovery._public_url(value))

    def test_identity_validation_rejects_scheme_shape_errors(self) -> None:
        for field, value in (
            ("homepage", "https:relative"),
            ("repository", "mailto://github.com"),
        ):
            with self.subTest(field=field, value=value):
                registry = copy.deepcopy(self.registry)
                registry["identity"][field] = value
                self.assertIn("identity", agent_discovery.validate(registry))
                with self.assertRaisesRegex(ValueError, "INVALID identity"):
                    agent_discovery.projections(registry)

    def test_contact_validation_rejects_scheme_shape_errors(self) -> None:
        for value in (
            "https:///missing-host",
            "mailto://example.com",
            "https://example.com/\ncontact: forged",
        ):
            with self.subTest(value=value):
                registry = copy.deepcopy(self.registry)
                registry["contact_methods"][0]["url"] = value
                self.assertIn("contact_methods.$.url", agent_discovery.validate(registry))
                with self.assertRaisesRegex(ValueError, r"contact_methods\.\$\.url"):
                    agent_discovery.projections(registry)


if __name__ == "__main__":
    unittest.main()
