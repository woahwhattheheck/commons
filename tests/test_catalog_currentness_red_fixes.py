from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from revenue.catalog_currentness.audit import CatalogCurrentnessError, compile_currentness
from revenue.catalog_currentness.cli import main as cli_main

AS_OF = "2026-09-13T10:15:00Z"
A64, B64, C64 = (c * 64 for c in "abc")
A40, B40 = (c * 40 for c in "ab")


def fixture() -> dict:
    return {
        "schema": "commons-catalog-currentness-input/v1",
        "catalogs": [{
            "catalogId": "products",
            "family": "PRODUCT",
            "catalogDigestSha256": A64,
            "entries": [{
                "entryId": "product-v1",
                "artifactId": "product",
                "repository": "Org/Product",
                "releaseCommitSha": A40,
                "sourcePath": "src/product.py",
                "sourceContentSha256": B64,
                "sourceEvidenceSha256": C64,
                "version": "1.0.0",
                "currentnessPolicy": "FOLLOW_DEFAULT_BRANCH",
            }],
        }],
        "providerSnapshots": [{
            "snapshotId": "product-main",
            "repository": "org/product",
            "defaultBranch": "main",
            "defaultBranchHeadSha": B40,
            "capturedAt": "2026-09-13T10:00:00Z",
            "complete": True,
            "providerEvidenceSha256": A64,
            "paths": [{"sourcePath": "src/product.py", "contentSha256": B64}],
        }],
    }


class CatalogCurrentnessRedFixTests(unittest.TestCase):
    def test_case_variant_repository_matches_single_snapshot(self):
        receipt = compile_currentness(fixture(), as_of=AS_OF)
        self.assertEqual(receipt["state"], "READY_FOR_HUMAN_CATALOG_CURRENTNESS_REVIEW")
        self.assertEqual(receipt["counts"]["current"], 1)

    def test_case_variant_repo_path_artifact_conflict_rejected(self):
        value = fixture()
        other = copy.deepcopy(value["catalogs"][0]["entries"][0])
        other["entryId"] = "other-v1"
        other["artifactId"] = "other"
        other["repository"] = "org/product"
        value["catalogs"][0]["entries"].append(other)
        with self.assertRaisesRegex(CatalogCurrentnessError, "conflicting artifact identity"):
            compile_currentness(value, as_of=AS_OF)

    def test_case_variant_snapshot_alias_is_ambiguous(self):
        value = fixture()
        other = copy.deepcopy(value["providerSnapshots"][0])
        other["snapshotId"] = "product-main-two"
        other["repository"] = "ORG/PRODUCT"
        value["providerSnapshots"].append(other)
        receipt = compile_currentness(value, as_of=AS_OF)
        self.assertEqual(receipt["state"], "HOLD")
        self.assertIn("AMBIGUOUS_REPOSITORY_SNAPSHOT", {row["code"] for row in receipt["findings"]})

    def test_cli_rejects_duplicate_json_keys(self):
        text = json.dumps(fixture())
        needle = '"schema": "commons-catalog-currentness-input/v1"'
        text = text.replace(needle, needle + ", " + needle, 1)
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "input.json"
            out = Path(tmp) / "out"
            source.write_text(text, encoding="utf-8")
            self.assertEqual(cli_main([str(source), "--as-of", AS_OF, "--out", str(out)]), 2)
            self.assertFalse(out.exists())

    def test_cli_rejects_nonfinite_json(self):
        text = json.dumps(fixture()).replace('"complete": true', '"complete": NaN', 1)
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "input.json"
            out = Path(tmp) / "out"
            source.write_text(text, encoding="utf-8")
            self.assertEqual(cli_main([str(source), "--as-of", AS_OF, "--out", str(out)]), 2)
            self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
