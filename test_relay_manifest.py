#!/usr/bin/env python3

import json
from pathlib import Path
import unittest
from unittest import mock

import board_ingest
import commons_mcp
import relay_manifest


ROOT = Path(__file__).resolve().parent
EXPECTED = (
    "https://ntfy.sh",
    "https://ntfy.envs.net",
    "https://ntfy.adminforge.de",
    "https://ntfy.mzte.de",
    "https://ntfy.tedomum.net",
    "https://ntfy.hostux.net",
)


class RelayManifestTests(unittest.TestCase):
    def test_canonical_six_relay_order(self):
        self.assertEqual(relay_manifest.NTFY_HOSTS, EXPECTED)
        self.assertEqual(relay_manifest.NTFY_TOPIC, "woahwhattheheck-commons-board")
        self.assertEqual(relay_manifest.MANIFEST["participation_effect"], "NONE")
        self.assertEqual(relay_manifest.MANIFEST["observation_policy"], "DIRECT_POLL_EVERY_RELAY")

    def test_schema_describes_every_manifest_key(self):
        schema = json.loads((ROOT / "relay-manifest.schema.json").read_text(encoding="utf-8"))
        manifest = json.loads((ROOT / "relay-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(set(manifest), set(schema["properties"]))
        self.assertTrue(set(schema["required"]).issubset(manifest))
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(schema["properties"]["observation_policy"]["const"], "DIRECT_POLL_EVERY_RELAY")
        self.assertEqual(schema["properties"]["participation_effect"]["const"], "NONE")

    def test_browser_and_typescript_blocks_are_generated_from_same_bytes(self):
        for target in relay_manifest.TARGETS:
            path = ROOT / target
            self.assertFalse(
                relay_manifest.sync_file(path, target, relay_manifest.MANIFEST, write=False),
                target,
            )
            text = path.read_text(encoding="utf-8")
            marker_count = int(relay_manifest.TARGETS[target].get("markers", True))
            self.assertEqual(text.count(relay_manifest.BEGIN), marker_count, target)
            self.assertEqual(text.count(relay_manifest.END), marker_count, target)
            for url in EXPECTED:
                self.assertEqual(text.count(json.dumps(url)), 1, (target, url))

    def test_sync_preserves_crlf(self):
        source = (
            '(function () {\r\n'
            '  var NTFY_TOPIC = "old";\r\n'
            '  var NTFY_HOSTS = [\r\n'
            '    "https://old.example"\r\n'
            '  ];\r\n'
            '})();\r\n'
        )
        updated = relay_manifest.sync_text(source, "carrier.js", relay_manifest.MANIFEST)
        self.assertNotIn("\n", updated.replace("\r\n", ""))
        self.assertIn(EXPECTED[-1], updated)

    def test_python_consumers_reference_shared_constants(self):
        board = (ROOT / "board_ingest.py").read_text(encoding="utf-8")
        mcp = (ROOT / "commons_mcp.py").read_text(encoding="utf-8")
        lanes = (ROOT / "independent_commons_mcp" / "lanes.py").read_text(encoding="utf-8")
        package = (ROOT / "independent_commons_mcp" / "__init__.py").read_text(encoding="utf-8")
        relays = (ROOT / "ntfy_relays.py").read_text(encoding="utf-8")
        self.assertIn("from relay_manifest import NTFY_HOSTS, NTFY_TOPIC", board)
        self.assertIn("from relay_manifest import NTFY_HOSTS, NTFY_TOPIC", mcp)
        self.assertIn("from relay_manifest import NTFY_HOSTS, NTFY_TOPIC as TOPIC", lanes)
        self.assertIn("from relay_manifest import NTFY_TOPIC as TOPIC", package)
        self.assertIn("from relay_manifest import NTFY_HOSTS, NTFY_TOPIC", relays)

    def test_board_ingest_directly_polls_relay_five(self):
        self._assert_direct_poll(EXPECTED[4])

    def test_board_ingest_directly_polls_relay_six(self):
        self._assert_direct_poll(EXPECTED[5])

    def _assert_direct_poll(self, only_host):
        called = []

        def observe(host, _already, _seen):
            called.append(host)
            return int(host == only_host)

        with mock.patch.object(board_ingest, "_ingest_ntfy_host", side_effect=observe):
            self.assertEqual(board_ingest.ingest_ntfy(), 1)
        self.assertEqual(tuple(called), EXPECTED)
        self.assertIn(only_host, called)

    def test_mcp_publishes_the_same_manifest(self):
        text = (ROOT / "commons_mcp.py").read_text(encoding="utf-8")
        self.assertIn('("relays", "ntfy"): ("relay-manifest.json"', text)
        self.assertIn('"uri": "commons://relays/ntfy"', text)

        class Truth:
            def head_sha(self):
                return "a" * 40

            def read_at_sha(self, path, sha):
                self.path = path
                self.sha = sha
                return (ROOT / path).read_text(encoding="utf-8")

        truth = Truth()
        gateway = commons_mcp.CommonsGateway(truth=truth, carrier=object())
        resource = gateway.read_resource("commons://relays/ntfy")
        self.assertEqual(resource["git_sha"], "a" * 40)
        self.assertEqual(truth.path, "relay-manifest.json")
        self.assertEqual(json.loads(resource["text"])["relays"][-1]["url"], EXPECTED[-1])


if __name__ == "__main__":
    unittest.main()
