#!/usr/bin/env python3

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("path_manifest", ROOT / "host" / "path_manifest.py")
path_manifest = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(path_manifest)


class PathManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = path_manifest.load_manifest(ROOT / "architecture" / "path-manifest.json")
        cls.classifier = path_manifest.PathClassifier(cls.manifest)

    def test_manifest_is_descriptive(self):
        self.assertEqual(self.manifest["participation_effect"], "NONE")
        self.assertEqual(self.manifest["fallback"]["classification"], "UNMAPPED")

    def test_known_paths_share_one_classifier(self):
        expected = {
            "p/example-record.md": "CANONICAL_SOURCE",
            "p/example-record.html": "DERIVED_PROJECTION",
            "by/~ZXhhbXBsZQ.html": "DERIVED_PROJECTION",
            "projection/converged/v1/digest.json": "DERIVED_PROJECTION",
            "revenue/outcome_commerce/catalog.json": "SCHEMA_AND_CATALOG",
            "orchestration/jeffersonville/topology.json": "SCHEMA_AND_CATALOG",
            "host/titan_hands_windows/server.py": "EXECUTABLE_SOURCE",
            "muhl/containers/example.mno": "CORPUS_PAYLOAD",
            "commerce.html": "SCHEMA_AND_CATALOG",
        }
        for path, classification in expected.items():
            with self.subTest(path=path):
                self.assertEqual(self.classifier.classify(path)["classification"], classification)

    def test_unknown_path_is_visible_not_silent(self):
        row = self.classifier.classify("novel-format.payload")
        self.assertEqual(row["classification"], "UNMAPPED")
        self.assertIn("VISIBLE_DIAGNOSTIC", row["flags"])

    def test_glob_double_star_observes_root_and_nested(self):
        self.assertEqual(self.classifier.classify("sample.py")["classification"], "EXECUTABLE_SOURCE")
        self.assertEqual(self.classifier.classify("new/area/sample.py")["classification"], "EXECUTABLE_SOURCE")
        self.assertEqual(
            self.classifier.classify(".github/workflows/tests.yml")["subsystem"],
            "ci",
        )

    def test_report_is_deterministic_and_counts_tests(self):
        paths = ["test_alpha.py", "nested/test_beta.js", "p/one.md", "new.payload"]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "board_ingest.py").write_text("ASSET_PATHS = ['p', 'recent.json']\n", encoding="utf-8")
            first = path_manifest.build_report(root, self.manifest, paths=paths)
            second = path_manifest.build_report(root, self.manifest, paths=reversed(paths))
        self.assertEqual(first, second)
        self.assertEqual(first["tests"]["root_count"], 1)
        self.assertEqual(first["tests"]["nested_count"], 1)
        self.assertEqual(first["unmapped_paths"], ["new.payload"])
        self.assertEqual(first["generator_contracts"][0]["declared_count"], 2)

    def test_schema_and_manifest_are_valid_json(self):
        schema = json.loads((ROOT / "architecture" / "path-manifest.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(schema["properties"]["participation_effect"]["const"], "NONE")
        self.assertEqual(path_manifest.manifest_digest(self.manifest), path_manifest.manifest_digest(dict(self.manifest)))


if __name__ == "__main__":
    unittest.main()
