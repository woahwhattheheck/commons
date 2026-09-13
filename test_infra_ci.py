"""Keep the infra inventory and nested test wiring measurable."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from host.ci_battery import discover


ROOT = Path(__file__).resolve().parent
README = ROOT / "infra" / "README.md"
WORKFLOW = ROOT / ".github" / "workflows" / "tests.yml"
PROVIDERS = ROOT / "ci" / "provider_quotas.json"


def file_count(relative: str) -> int:
    return sum(1 for path in (ROOT / relative).rglob("*") if path.is_file())


def documented_count(text: str, relative: str) -> int:
    match = re.search(
        rf"^\s*{re.escape(relative)}/\s+(\d+)\s+files\s*$",
        text,
        flags=re.MULTILINE,
    )
    if not match:
        raise AssertionError(f"missing documented count for {relative}/")
    return int(match.group(1))


class InfraCiTest(unittest.TestCase):
    def test_documented_live_counts_match_the_tree(self):
        text = README.read_text(encoding="utf-8")
        for relative in ("infra/host", "infra/tools"):
            with self.subTest(relative=relative):
                self.assertEqual(documented_count(text, relative), file_count(relative))

    def test_nested_discord_test_is_discovered_by_ci(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        nested = ROOT / "infra" / "discord" / "test_commons_discord_bridge.py"
        self.assertTrue(nested.is_file())
        self.assertEqual(workflow.count("- 'infra/**'"), 2)
        self.assertIn("python3 host/ci_battery.py --results", workflow)
        self.assertIn(("python3", "infra/discord/test_commons_discord_bridge.py"), discover(ROOT))

    def test_retired_cirrus_provider_cannot_look_executable(self):
        inventory = json.loads(PROVIDERS.read_text(encoding="utf-8"))
        matches = [row for row in inventory["roads"] if row["road"] == "Cirrus CI"]
        self.assertEqual(len(matches), 1)
        cirrus = matches[0]
        self.assertEqual(cirrus["job_class"], "excluded")
        self.assertEqual(cirrus["state"], "DEAD/EXCLUDED")
        self.assertIsNone(cirrus["config"])
        self.assertIsNone(cirrus["invoke"])
        self.assertIn("2026-06-01", cirrus["free_quota"])
        self.assertFalse((ROOT / ".cirrus.yml").exists())

    def test_historical_classifier_is_not_current_policy(self):
        notice = (ROOT / "infra" / "OUT_OF_SPEC_NOT_INCLUDED.txt").read_text(
            encoding="utf-8"
        )
        self.assertIn("HISTORICAL CLASSIFIER OUTPUT", notice)
        self.assertIn("SUPERSEDED SCOPE NOTICE", notice)


if __name__ == "__main__":
    unittest.main()
