#!/usr/bin/env python3
"""Contract tests for the checksummed White Box archive inventory."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parent
INVENTORY_PATH = ROOT / "revenue/ip/whitebox_archive_inventory.json"
SCHEMA_PATH = ROOT / "revenue/ip/whitebox_archive_inventory.schema.json"
SPEC = importlib.util.spec_from_file_location(
    "whitebox_archive_inventory", ROOT / "host/whitebox_archive_inventory.py"
)
inventory_tool = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(inventory_tool)


class WhiteBoxArchiveInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inventory = inventory_tool.read_json(INVENTORY_PATH)

    def test_draft_2020_12_schema_and_full_contract(self):
        from test_outcome_commerce import MiniSchemaValidator

        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        self.assertIs(schema["additionalProperties"], False)
        MiniSchemaValidator(SCHEMA_PATH.parent).validate_file(
            self.inventory, SCHEMA_PATH.name
        )
        result = inventory_tool.validate_inventory(self.inventory)
        self.assertEqual(result["status"], "VALID")

    def test_exact_measured_archive_counts(self):
        archive = self.inventory["archive"]
        self.assertEqual(archive["file_count"], 7946)
        self.assertEqual(archive["directory_count"], 56)
        self.assertEqual(archive["total_bytes"], 16172446060)
        self.assertEqual(self.inventory["sensitive_data"]["scanned_files"], 7946)
        self.assertEqual(
            self.inventory["sensitive_data"]["scanned_bytes"], 16172446060
        )

    def test_exact_eight_model_groups_match_public_index(self):
        provenance = self.inventory["provenance"]
        self.assertEqual(len(provenance["public_index_model_ids"]), 8)
        self.assertTrue(
            all(model_id.endswith(".gguf") for model_id in provenance["public_index_model_ids"])
        )
        self.assertEqual(len(provenance["expected_model_groups"]), 8)
        self.assertEqual(
            provenance["expected_model_groups"], provenance["observed_model_groups"]
        )
        self.assertIs(provenance["model_groups_match_public_index"], True)

    def test_no_absolute_source_or_sensitive_match_values_are_published(self):
        rendered = json.dumps(self.inventory, ensure_ascii=False)
        self.assertNotIn("C:\\Users\\", rendered)
        self.assertNotIn("C:/Users/", rendered)
        self.assertIs(self.inventory["scope"]["source_absolute_path_published"], False)
        self.assertIs(self.inventory["scope"]["payload_files_published"], False)
        self.assertIs(
            self.inventory["sensitive_data"]["matched_values_published"], False
        )

    def test_transfer_and_sample_release_are_not_overclaimed(self):
        self.assertIs(self.inventory["license"]["transfer_cleared"], False)
        self.assertIn(
            self.inventory["license"]["status"],
            {"FOUND_REVIEW_REQUIRED", "NOT_LOCATED_REVIEW_REQUIRED"},
        )
        self.assertIs(
            self.inventory["sensitive_data"]["public_sample_release_cleared"],
            False,
        )
        self.assertIs(
            self.inventory["commercial_readiness"]["archive_license_offer_ready"],
            False,
        )
        self.assertIs(self.inventory["commercial_readiness"]["pricing_ready"], False)

    def test_tree_digest_detects_one_byte_manifest_drift(self):
        broken = copy.deepcopy(self.inventory)
        broken["files"][0]["size_bytes"] += 1
        with self.assertRaisesRegex(inventory_tool.InventoryError, "byte count drift"):
            inventory_tool.validate_inventory(broken)

    def test_transfer_clearance_injection_fails(self):
        broken = copy.deepcopy(self.inventory)
        broken["license"]["transfer_cleared"] = True
        with self.assertRaisesRegex(inventory_tool.InventoryError, "transfer clearance"):
            inventory_tool.validate_inventory(broken)

    def test_synthetic_scan_is_deterministic_and_never_publishes_match_values(self):
        with tempfile.TemporaryDirectory() as temporary:
            temp = Path(temporary)
            archive = temp / "archive"
            model = archive / "model-one"
            model.mkdir(parents=True)
            secret = b"sk_" + b"live_" + (b"A" * 32)
            (model / "artifact.pyc").write_bytes(b"left" + secret + b"right")
            (archive / "README.md").write_text("owner@example.test\n", encoding="utf-8")
            public_index = temp / "index.json"
            public_index.write_text('{"model-one": {}}\n', encoding="utf-8")
            kwargs = {
                "public_index": public_index,
                "inventory_date": "2026-08-26",
                "index_blob_sha": "1" * 40,
                "readme_blob_sha": "2" * 40,
            }
            with mock.patch.object(inventory_tool, "HASH_CHUNK_BYTES", 7):
                first = inventory_tool.scan_archive(archive, **kwargs)
                second = inventory_tool.scan_archive(archive, **kwargs)
            self.assertEqual(first, second)
            self.assertEqual(
                first["sensitive_data"]["status"],
                "POTENTIAL_SECRET_REVIEW_REQUIRED",
            )
            categories = {
                finding["category"] for finding in first["sensitive_data"]["findings"]
            }
            self.assertIn("STRIPE_LIVE_SECRET", categories)
            self.assertIn("POTENTIAL_EMAIL", categories)
            self.assertNotIn(secret.decode("ascii"), json.dumps(first))

    def test_cli_validate(self):
        completed = subprocess.run(
            [
                sys.executable,
                str(ROOT / "host/whitebox_archive_inventory.py"),
                "validate",
                str(INVENTORY_PATH),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(result["status"], "VALID")
        self.assertEqual(result["files"], 7946)


if __name__ == "__main__":
    unittest.main()
