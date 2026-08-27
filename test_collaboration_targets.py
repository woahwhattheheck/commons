#!/usr/bin/env python3
"""Exact-evidence tests for the Commons collaboration target ledger."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("collaboration_targets", ROOT / "host/collaboration_targets.py")
targets = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(targets)


class CollaborationTargetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data, cls.schema = targets.load(ROOT)

    def test_schema_and_semantic_contract(self):
        from test_outcome_commerce import MiniSchemaValidator

        self.assertIs(self.schema["additionalProperties"], False)
        MiniSchemaValidator(ROOT / "revenue/ip").validate_file(self.data, "collaboration_targets.schema.json")
        result = targets.validate(ROOT, self.data, self.schema)
        self.assertEqual(result["status"], "VALID")
        self.assertEqual(result["targets"], 6)
        self.assertEqual(result["route_counts"], {route: 2 for route in targets.ROUTES})
        self.assertEqual(result["mapped_offers"], 3)

    def test_exact_target_order_and_immutable_source_shapes(self):
        self.assertEqual([target["id"] for target in self.data["targets"]], list(targets.TARGET_IDS))
        for target in self.data["targets"]:
            source = target["source"]
            self.assertEqual(
                source["immutable_url"],
                f"https://github.com/{source['repository']}/blob/{source['commit_sha']}/{source['readme_path']}",
            )

    def test_route_bucket_collapse_fails_closed(self):
        broken = copy.deepcopy(self.data)
        broken["targets"][0]["route"] = "VENDOR_INTEGRATION"
        with self.assertRaisesRegex(targets.CollaborationTargetError, "2/2/2"):
            targets.validate(ROOT, broken, self.schema)

    def test_duplicate_entity_fails_closed(self):
        broken = copy.deepcopy(self.data)
        broken["targets"][1]["entity"] = broken["targets"][0]["entity"]
        with self.assertRaisesRegex(targets.CollaborationTargetError, "duplicate entity"):
            targets.validate(ROOT, broken, self.schema)

    def test_offer_catalog_blob_drift_fails_closed(self):
        broken = copy.deepcopy(self.data)
        broken["offer_catalog_source"]["blob_sha"] = "0" * 40
        with self.assertRaisesRegex(targets.CollaborationTargetError, "offer catalog blob drift"):
            targets.validate(ROOT, broken, self.schema)

    def test_unmapped_offer_fails_closed(self):
        broken = copy.deepcopy(self.data)
        broken["targets"][0]["mapped_offer_id"] = "whitebox-archive-license"
        with self.assertRaisesRegex(targets.CollaborationTargetError, "mapped offer invalid"):
            targets.validate(ROOT, broken, self.schema)

    def test_contact_or_cash_claim_fails_closed(self):
        for key in ("contacted", "cash_received"):
            with self.subTest(key=key):
                broken = copy.deepcopy(self.data)
                broken["truth"][key] = True
                with self.assertRaisesRegex(targets.CollaborationTargetError, "may not invent"):
                    targets.validate(ROOT, broken, self.schema)

    def test_owner_archive_boundary_mutations_fail_closed(self):
        broken = copy.deepcopy(self.data)
        broken["targets"][3]["asset_boundary"] = "OWNER_ARCHIVE"
        with self.assertRaisesRegex(targets.CollaborationTargetError, "asset boundary drift"):
            targets.validate(ROOT, broken, self.schema)
        broken = copy.deepcopy(self.data)
        broken["targets"][3]["uses_owner_archive_payload"] = True
        with self.assertRaisesRegex(targets.CollaborationTargetError, "archive payload use"):
            targets.validate(ROOT, broken, self.schema)

    def test_immutable_url_drift_fails_closed(self):
        broken = copy.deepcopy(self.data)
        broken["targets"][2]["source"]["immutable_url"] = "https://github.com/huggingface/huggingface_hub"
        with self.assertRaisesRegex(targets.CollaborationTargetError, "immutable URL drift"):
            targets.validate(ROOT, broken, self.schema)

    def test_git_blob_sha_matches_git_hash_object_contract(self):
        raw = b"commons collaboration source\n"
        self.assertEqual(targets._git_blob_sha(raw), "48116fa33160f631f0ecb65792646bf39a1f1fea")

    def test_cli_validate(self):
        completed = subprocess.run(
            [sys.executable, str(ROOT / "host/collaboration_targets.py"), "validate", "--root", str(ROOT)],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(result["status"], "VALID")
        self.assertEqual(result["targets"], 6)


if __name__ == "__main__":
    unittest.main()
