#!/usr/bin/env python3
"""Focused tests for the connected capability inventory compiler."""
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from host import connected_capability_inventory as inventory

ROOT = Path(__file__).resolve().parent
OBSERVATIONS = ROOT / "inventory" / "resources" / "connected_capability_observations.json"
CATALOG = ROOT / "inventory" / "resources" / "connected_capabilities.json"

class ConnectedCapabilityInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = json.loads(OBSERVATIONS.read_text(encoding="utf-8"))
        cls.catalog = inventory.compile_catalog(cls.source)

    def test_snapshot_compiles_and_matches_checked_in_catalog(self) -> None:
        self.assertEqual(inventory.canonical_json(self.catalog), CATALOG.read_text(encoding="utf-8"))

    def test_axes_are_present_on_every_resource(self) -> None:
        for row in self.catalog["providers"]:
            self.assertTrue(inventory.REQUIRED_PROVIDER_FIELDS <= row.keys())

    def test_ids_are_unique_and_sorted(self) -> None:
        ids = [row["id"] for row in self.catalog["providers"]]
        self.assertEqual(ids, sorted(ids))
        self.assertEqual(len(ids), len(set(ids)))

    def test_all_carriers_share_everything_except_claude(self) -> None:
        owner_only = [row["id"] for row in self.catalog["providers"] if row["authority"] == "OWNER_ONLY"]
        self.assertEqual(owner_only, ["claude-code-max"])
        shared = [row for row in self.catalog["providers"] if row["id"] != "claude-code-max"]
        self.assertTrue(all(row["authority"] == "SHARED_ALL_CARRIERS" for row in shared))

    def test_shared_business_gmail_is_explicit(self) -> None:
        gmail = self.catalog["account_roles"]["business_gmail"]
        self.assertEqual(gmail["address"], "tokenjunkielabs@gmail.com")
        self.assertEqual(gmail["sharing"], "ALL_CARRIERS")

    def test_github_shipping_identity_is_distinct(self) -> None:
        github = self.catalog["account_roles"]["github"]
        self.assertEqual(github["identities"], ["woahwhattheheck", "tokenjunkielabs"])
        self.assertEqual(github["ship_target"], "woahwhattheheck")
        self.assertEqual(github["non_ship_identity"], "tokenjunkielabs")

    def test_repository_fleet_reconciles_nine_repositories(self) -> None:
        fleet = self.catalog["github_portfolio"]
        self.assertEqual(fleet["accessible_repositories"], 9)
        self.assertEqual(fleet["public_repositories"], 4)
        self.assertEqual(fleet["private_repositories"], 5)
        self.assertEqual(len(fleet["repositories"]), 9)

    def test_tool_skill_and_automation_counts_reconcile(self) -> None:
        tools = self.catalog["tool_fleet"]
        self.assertEqual(tools["callable_tools"], 405)
        self.assertEqual(tools["connected_app_tools"], 390)
        self.assertEqual(sum(tools["app_family_counts"].values()), 390)
        self.assertEqual(tools["fully_paginated_skills"], 104)
        self.assertEqual(sum(tools["skill_groups"].values()), 104)
        self.assertEqual(tools["automations"], {"total": 13, "enabled": 6, "disabled": 7})

    def test_cursor_has_usable_shared_route(self) -> None:
        rows = {row["id"]: row for row in self.catalog["providers"]}
        cursor = rows["cursor-ultra-pool"]
        self.assertEqual(cursor["allocation"], "CALLABLE_WITH_CONSTRAINT")
        self.assertEqual(cursor["authority"], "SHARED_ALL_CARRIERS")
        self.assertIn("one depleted and one currently usable", cursor["value"])

    def test_exhausted_grok_surfaces_wait_for_reset(self) -> None:
        rows = {row["id"]: row for row in self.catalog["providers"]}
        self.assertEqual(rows["supergrok-heavy"]["allocation"], "WAIT_FOR_RESET")
        self.assertEqual(rows["grokbot-token-pools"]["allocation"], "WAIT_FOR_RESET")

    def test_agentmail_is_an_activation_not_a_claimed_inbox(self) -> None:
        row = {row["id"]: row for row in self.catalog["providers"]}["agentmail"]
        self.assertEqual(row["allocation"], "ACTIVATE_FIRST")
        self.assertIn("no first inbox yet", row["value"])

    def test_catalog_is_deterministic_and_input_is_not_mutated(self) -> None:
        before = copy.deepcopy(self.source)
        first = inventory.compile_catalog(self.source)
        second = inventory.compile_catalog(copy.deepcopy(self.source))
        self.assertEqual(first, second)
        self.assertEqual(self.source, before)

    def test_secret_shapes_are_rejected(self) -> None:
        bad = copy.deepcopy(self.source)
        bad["providers"][0]["evidence"] = "api_key=definitely-secret-value"
        with self.assertRaises(inventory.CapabilityInventoryError):
            inventory.compile_catalog(bad)

    def test_duplicate_resource_is_rejected(self) -> None:
        bad = copy.deepcopy(self.source)
        bad["providers"].append(copy.deepcopy(bad["providers"][0]))
        with self.assertRaises(inventory.CapabilityInventoryError):
            inventory.compile_catalog(bad)

    def test_second_owner_only_resource_is_rejected(self) -> None:
        bad = copy.deepcopy(self.source)
        bad["providers"][0]["authority"] = "OWNER_ONLY"
        bad["providers"][0]["route_state"] = "OWNER_HANDLED"
        with self.assertRaises(inventory.CapabilityInventoryError):
            inventory.compile_catalog(bad)

    def test_cli_verify_and_self_test(self) -> None:
        self.assertEqual(inventory.main(["--verify"]), 0)
        self.assertEqual(inventory.main(["--self-test"]), 0)
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "catalog.json"
            self.assertEqual(inventory.main(["--output", str(out)]), 0)
            self.assertEqual(out.read_text(encoding="utf-8"), CATALOG.read_text(encoding="utf-8"))

if __name__ == "__main__":
    unittest.main()

