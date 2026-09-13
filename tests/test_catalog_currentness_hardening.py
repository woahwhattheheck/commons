import contextlib
import copy
import io
import tempfile
import unittest
from pathlib import Path

from revenue.catalog_currentness.audit import CatalogCurrentnessError, compile_currentness, strict_json_loads
from revenue.catalog_currentness.cli import main as cli_main
from tests.test_catalog_currentness import AS_OF, fixture


class CatalogCurrentnessHardeningTests(unittest.TestCase):
    def test_cross_case_repo_path_artifact_conflict_rejected(self):
        raw = fixture()
        extra = copy.deepcopy(raw["catalogs"][0]["entries"][0])
        extra.update(entryId="case-other", artifactId="other", repository="ORG/PRODUCT")
        raw["catalogs"][0]["entries"].append(extra)
        with self.assertRaises(CatalogCurrentnessError):
            compile_currentness(raw, as_of=AS_OF)

    def test_cross_case_snapshot_alias_is_ambiguous(self):
        raw = fixture()
        extra = copy.deepcopy(raw["providerSnapshots"][0])
        extra.update(snapshotId="product-main-case", repository="ORG/PRODUCT")
        raw["providerSnapshots"].append(extra)
        receipt = compile_currentness(raw, as_of=AS_OF)
        self.assertEqual(receipt["state"], "HOLD")
        self.assertIn("AMBIGUOUS_REPOSITORY_SNAPSHOT", {x["code"] for x in receipt["findings"]})

    def test_strict_json_rejects_duplicate_key(self):
        with self.assertRaises(CatalogCurrentnessError):
            strict_json_loads('{"schema":"a","schema":"b"}')

    def test_strict_json_rejects_nonfinite_number(self):
        with self.assertRaises(CatalogCurrentnessError):
            strict_json_loads('{"x":NaN}')

    def test_cli_rejects_duplicate_key_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, out = root / "input.json", root / "out"
            source.write_text('{"schema":"a","schema":"b"}', encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                code = cli_main([str(source), "--as-of", AS_OF, "--out", str(out)])
            self.assertEqual(code, 2)
            self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
