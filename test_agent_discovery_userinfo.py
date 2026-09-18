from __future__ import annotations

import copy
import json
import unittest

from host import agent_discovery as discovery


def registry() -> dict:
    return {
        "schema": "commons-agent-discovery/v1",
        "identity": {
            "name": "Commons",
            "description": "Public agent discovery",
            "homepage": "https://example.test/commons/",
            "repository": "https://example.test/repository",
        },
        "runtime_signals": {
            "discovery_state": "open",
            "runtime_state": "event-driven",
            "runtime_access": "public",
            "source_of_truth": "git-head",
            "claims_require_receipts": True,
        },
        "contact_methods": [
            {"type": "action-pad", "preferred": True, "url": "https://example.test/action"},
            {"type": "mail", "preferred": False, "url": "mailto:operator@example.test"},
        ],
        "capabilities": [
            {"id": "discover", "description": "Read roads", "entrypoints": ["agents.txt"]},
        ],
        "continuity": {
            "startup_order": ["harnesses/catalog.json", "AGENTS.md", "START.md", "boards.html"],
            "pulse": "pulse.json",
            "recent": "recent.json",
            "receipts": "p/",
            "instruction": "Read current git HEAD.",
        },
        "interoperability": {"formats": list(discovery.OUTPUTS)},
    }


class AgentDiscoveryUserinfoTests(unittest.TestCase):
    def test_clean_https_authorities_remain_public(self) -> None:
        for value in (
            "https://example.test",
            "https://example.test:443/path?query=yes#fragment",
            "https://[2001:db8::1]/agent.json",
            "https://sub.example.test/a:b",
        ):
            with self.subTest(value=value):
                self.assertTrue(discovery._public_url(value))

    def test_https_userinfo_is_not_a_public_discovery_url(self) -> None:
        values = (
            "https://user@example.test/path",
            "https://user:password@example.test/path",
            "https://:password@example.test/path",
            "https://example.test@evil.test/path",
            "https://user%40name:secret@example.test/path",
            "https://user@[2001:db8::1]/path",
        )
        for value in values:
            with self.subTest(value=value):
                self.assertFalse(discovery._public_url(value))

    def test_mailto_and_existing_malformed_authority_behavior_is_unchanged(self) -> None:
        self.assertTrue(discovery._public_url("mailto:operator@example.test"))
        self.assertFalse(discovery._public_url("mailto://operator@example.test"))
        self.assertFalse(discovery._public_url("https:relative"))
        self.assertFalse(discovery._public_url("https://example.test:not-a-port/path"))
        self.assertFalse(discovery._public_url("http://example.test"))

    def test_identity_userinfo_is_rejected(self) -> None:
        for field in ("homepage", "repository"):
            value = registry()
            value["identity"][field] = "https://PUBLIC-SENTINEL:secret@example.test/path"
            with self.subTest(field=field):
                self.assertIn("identity", discovery.validate(value))
                with self.assertRaisesRegex(ValueError, "INVALID identity"):
                    discovery.projections(value)

    def test_contact_userinfo_is_rejected(self) -> None:
        value = registry()
        value["contact_methods"][0]["url"] = "https://PUBLIC-SENTINEL:secret@example.test/action"
        self.assertIn("contact_methods.$.url", discovery.validate(value))
        with self.assertRaisesRegex(ValueError, r"INVALID contact_methods\.\$\.url"):
            discovery.projections(value)

    def test_clean_registry_projections_keep_existing_shape(self) -> None:
        value = registry()
        self.assertEqual(discovery.validate(value), [])
        projected = discovery.projections(value)
        self.assertEqual(set(projected), set(discovery.OUTPUTS))
        card = json.loads(projected["agent.json"])
        self.assertEqual(card["url"], value["identity"]["homepage"])
        self.assertEqual(card["contact_methods"], value["contact_methods"])
        self.assertEqual(projected["agent.json"], projected[".well-known/agent.json"])

    def test_userinfo_rejection_does_not_echo_secret_into_outputs(self) -> None:
        value = registry()
        value["contact_methods"][0]["url"] = "https://name:PRIVATE-SENTINEL@example.test/action"
        with self.assertRaises(ValueError) as caught:
            discovery.projections(value)
        self.assertNotIn("PRIVATE-SENTINEL", str(caught.exception))

    def test_validation_does_not_mutate_the_registry(self) -> None:
        value = registry()
        original = copy.deepcopy(value)
        self.assertEqual(discovery.validate(value), [])
        self.assertEqual(value, original)


if __name__ == "__main__":
    unittest.main()
