"""Discovery files must match projection bytes, not normalized text."""

import json
import tempfile
import unittest
from pathlib import Path

from host import agent_discovery


class AgentDiscoveryExactBytesTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        registry = agent_discovery.load_registry()
        registry["identity"]["description"] += " Caf\u00e9 \u2615"
        (self.root / "agent-discovery.json").write_bytes(
            json.dumps(registry, ensure_ascii=False).encode("utf-8")
        )
        self.expected = {
            name: content.encode("utf-8")
            for name, content in agent_discovery.projections(registry).items()
        }
        agent_discovery.generate(self.root)

    def test_generate_matches_utf8_projection_bytes(self) -> None:
        self.assertEqual(tuple(self.expected), agent_discovery.OUTPUTS)
        for name, expected in self.expected.items():
            with self.subTest(name=name):
                self.assertEqual((self.root / name).read_bytes(), expected)
                self.assertNotIn(b"\r", expected)
        self.assertIn("Caf\u00e9 \u2615".encode("utf-8"), self.expected["agents.txt"])
        self.assertEqual(agent_discovery.check(self.root), [])

    def test_newline_only_drift_is_reported_per_output(self) -> None:
        for name, expected in self.expected.items():
            variants = (
                expected.replace(b"\n", b"\r\n"),
                expected.replace(b"\n", b"\r"),
                expected.replace(b"\n", b"\r\n", 1),
            )
            for index, altered in enumerate(variants):
                with self.subTest(name=name, variant=index):
                    path = self.root / name
                    self.assertNotEqual(altered, expected)
                    path.write_bytes(altered)
                    try:
                        self.assertEqual(agent_discovery.check(self.root), [name])
                        self.assertEqual(path.read_bytes(), altered)
                    finally:
                        path.write_bytes(expected)

    def test_invalid_utf8_output_is_stale(self) -> None:
        for name, expected in self.expected.items():
            with self.subTest(name=name):
                path = self.root / name
                path.write_bytes(b"\xff\xfe\x80\n")
                try:
                    self.assertEqual(agent_discovery.check(self.root), [name])
                    self.assertEqual(path.read_bytes(), b"\xff\xfe\x80\n")
                finally:
                    path.write_bytes(expected)

    def test_missing_outputs_and_directories_keep_output_order(self) -> None:
        missing = ("manifest.json", ".well-known/agent.json", "continuity.json")
        for name in missing:
            (self.root / name).unlink()
        (self.root / "continuity.json").mkdir()
        self.assertEqual(agent_discovery.check(self.root), list(missing))
        self.assertTrue((self.root / "continuity.json").is_dir())

    def test_regenerate_repairs_all_newline_drift(self) -> None:
        source = (self.root / "agent-discovery.json").read_bytes()
        for name, expected in self.expected.items():
            (self.root / name).write_bytes(expected.replace(b"\n", b"\r\n"))
        self.assertEqual(agent_discovery.check(self.root), list(agent_discovery.OUTPUTS))
        agent_discovery.generate(self.root)
        self.assertEqual(agent_discovery.check(self.root), [])
        for name, expected in self.expected.items():
            self.assertEqual((self.root / name).read_bytes(), expected)
        self.assertEqual((self.root / "agent-discovery.json").read_bytes(), source)

    def test_check_never_rewrites_drifted_outputs(self) -> None:
        for name, expected in self.expected.items():
            (self.root / name).write_bytes(expected.replace(b"\n", b"\r\n"))
        before = {str(path.relative_to(self.root)): path.read_bytes()
                  for path in self.root.rglob("*") if path.is_file()}
        agent_discovery.check(self.root)
        after = {str(path.relative_to(self.root)): path.read_bytes()
                 for path in self.root.rglob("*") if path.is_file()}
        self.assertEqual(after, before)


if __name__ == "__main__":
    unittest.main()
