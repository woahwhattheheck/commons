#!/usr/bin/env python3
"""Retired CI providers must stay non-executable and fail closed."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CIRRUS_CONFIG = ROOT / ".cirrus.yml"
README = ROOT / "ci" / "README.md"
PROVIDERS = ROOT / "ci" / "provider_quotas.json"
ACTIONS = ROOT / ".github" / "workflows" / "tests.yml"


class RetiredCiProviderTest(unittest.TestCase):
    def setUp(self):
        self.cirrus_text = CIRRUS_CONFIG.read_text(encoding="utf-8")
        self.readme_text = README.read_text(encoding="utf-8")
        cards = json.loads(PROVIDERS.read_text(encoding="utf-8"))
        self.cirrus_card = next(
            row for row in cards["roads"] if row["road"] == "Cirrus CI"
        )

    def test_retired_cirrus_config_defines_no_tasks(self):
        self.assertIsNone(
            re.search(r"(?m)^[A-Za-z0-9_]+_task\s*:", self.cirrus_text)
        )
        self.assertNotIn("commons_battery_task:", self.cirrus_text)
        self.assertNotIn("header_census_task:", self.cirrus_text)
        self.assertIn("2026-06-01", self.cirrus_text)
        self.assertIn("https://cirruslabs.org/", self.cirrus_text)

    def test_machine_card_is_dead_and_has_no_invocation(self):
        self.assertEqual(self.cirrus_card["state"], "DEAD/EXCLUDED")
        self.assertIsNone(self.cirrus_card["invoke"])
        self.assertEqual(self.cirrus_card["config"], ".cirrus.yml")
        self.assertIn("2026-06-01", self.cirrus_card["free_quota"])
        self.assertIn("retired", self.cirrus_card["runtime"])
        self.assertEqual(self.cirrus_card["terms"], "https://cirruslabs.org/")

    def test_docs_remove_activation_path_and_keep_direct_runner(self):
        self.assertIn("### Cirrus CI is retired", self.readme_text)
        self.assertIn("2026-06-01", self.readme_text)
        self.assertIn("https://cirruslabs.org/", self.readme_text)
        self.assertIn("| Cirrus | `.cirrus.yml` | DEAD/EXCLUDED |", self.readme_text)
        self.assertNotIn("github.com/apps/cirrus-ci", self.readme_text)
        self.assertNotIn("Automatic execution on Cirrus", self.readme_text)
        self.assertIn(
            "python3 host/ci_battery.py --output-dir /tmp/commons-ci",
            self.readme_text,
        )
        workflow = ACTIONS.read_text(encoding="utf-8")
        self.assertIn(
            'python3 host/ci_battery.py --results "$RUNNER_TEMP/commons-battery-results.nul"',
            workflow,
        )


if __name__ == "__main__":
    unittest.main()
