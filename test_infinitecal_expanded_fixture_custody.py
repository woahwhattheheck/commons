from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parent
PRODUCT = ROOT / "revenue" / "production-lims" / "infinitecal-crossstate-method-parity"
MODULE_PATH = PRODUCT / "infinitecal_parity.py"
FIXTURE = PRODUCT / "fixtures" / "infinitecal_180_records.json"
MANIFEST = PRODUCT / "fixtures" / "manifest.json"
EXPECTED_ROWS = 180
EXPECTED_BYTES = 102719
EXPECTED_SHA256 = "ea7fb4bfa3ecd2f989041f80991db21e7dbaa26a2a30ecf3dd1e052690d8abd8"


def _load_module():
    spec = importlib.util.spec_from_file_location("infinitecal_parity_bd09", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _canonical_expanded_bytes(records) -> bytes:
    return (json.dumps(records, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("utf-8")


class InfiniteCALExpandedFixtureCustodyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mod = _load_module()
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.records = cls.mod.load_fixture(FIXTURE, MANIFEST)

    def test_manifest_binds_exact_expanded_rows(self) -> None:
        expanded = _canonical_expanded_bytes(self.records)
        self.assertEqual(len(self.records), EXPECTED_ROWS)
        self.assertEqual(len(expanded), EXPECTED_BYTES)
        self.assertEqual(hashlib.sha256(expanded).hexdigest(), EXPECTED_SHA256)
        self.assertEqual(self.manifest["expanded_records_bytes"], EXPECTED_BYTES)
        self.assertEqual(self.manifest["expanded_records_sha256"], EXPECTED_SHA256)

    def test_coherent_generator_value_drift_breaks_frozen_digest(self) -> None:
        drifted = copy.deepcopy(self.records)
        drifted[0]["canonical"]["value"] = "9999.0000"
        drifted[0]["state_output"]["value"] = "9999.0000"
        expanded = _canonical_expanded_bytes(drifted)
        self.assertEqual(len(drifted), EXPECTED_ROWS)
        self.assertNotEqual(hashlib.sha256(expanded).hexdigest(), EXPECTED_SHA256)


if __name__ == "__main__":
    unittest.main()
