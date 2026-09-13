"""Keep retired CI providers from being advertised as executable roads."""

from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
README = ROOT / "ci" / "README.md"
PROVIDERS = ROOT / "ci" / "provider_quotas.json"


class CirrusShutdownContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.readme = README.read_text(encoding="utf-8")
        cls.provider_data = json.loads(PROVIDERS.read_text(encoding="utf-8"))

    def test_active_cirrus_config_is_absent(self) -> None:
        self.assertFalse((ROOT / ".cirrus.yml").exists())

    def test_readme_records_shutdown_without_activation_instructions(self) -> None:
        self.assertIn("Cirrus CI would shut down effective", self.readme)
        self.assertIn("Monday, June 1, 2026", self.readme)
        self.assertIn("| Cirrus | — | DEAD/EXCLUDED |", self.readme)
        self.assertNotIn("Cirrus CI GitHub App", self.readme)
        self.assertNotIn("50 compute credits", self.readme)

    def test_provider_ledger_marks_cirrus_dead(self) -> None:
        matches = [
            road for road in self.provider_data["roads"]
            if road.get("road") == "Cirrus CI"
        ]
        self.assertEqual(len(matches), 1)
        cirrus = matches[0]
        self.assertEqual(cirrus["state"], "DEAD/EXCLUDED")
        self.assertEqual(cirrus["job_class"], "excluded")
        self.assertIsNone(cirrus["config"])
        self.assertIsNone(cirrus["invoke"])
        self.assertIn("shut down effective 2026-06-01", cirrus["free_quota"])
        self.assertEqual(cirrus["terms"], "https://cirruslabs.org/")


if __name__ == "__main__":
    unittest.main()
