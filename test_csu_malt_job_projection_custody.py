from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parent
PRODUCT = ROOT / "revenue" / "production-lims" / "csu-malt-method-expansion"
MODULE_PATH = PRODUCT / "csu_malt_expansion.py"
FIXTURE = PRODUCT / "fixtures" / "csu_80_submissions.json"
MANIFEST = PRODUCT / "fixtures" / "manifest.json"
EXPECTED_JOBS = 130
EXPECTED_BYTES = 22066
EXPECTED_SHA256 = "884c230e73f27253f26feb572833ffa47d56f7262648d79a12179a055fe163dd"
PROJECTION_FIELDS = (
    "job_id",
    "sample_id",
    "method_id",
    "method_version",
    "unit",
    "route",
    "week_route",
)


def _load_module():
    spec = importlib.util.spec_from_file_location("csu_malt_expansion_bd11", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _projection(jobs) -> list[dict[str, object]]:
    return [
        {field: job[field] for field in PROJECTION_FIELDS}
        for _, job in sorted(jobs.items())
    ]


def _canonical_bytes(value) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("utf-8")


class CSUMaltJobProjectionCustodyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mod = _load_module()
        cls.rows, cls.manifest = cls.mod.load(FIXTURE, MANIFEST)
        cls.ledger, cls.statuses, _ = cls.mod.run(copy.deepcopy(cls.rows), cls.manifest)
        cls.mod.verify(cls.rows, cls.manifest, cls.ledger, cls.statuses)
        cls.jobs = _projection(cls.ledger.jobs)

    def test_manifest_binds_exact_per_job_measurement_projection(self) -> None:
        encoded = _canonical_bytes(self.jobs)
        self.assertEqual(len(self.jobs), EXPECTED_JOBS)
        self.assertEqual(len(encoded), EXPECTED_BYTES)
        self.assertEqual(hashlib.sha256(encoded).hexdigest(), EXPECTED_SHA256)
        self.assertEqual(self.manifest["expanded_job_projection_bytes"], EXPECTED_BYTES)
        self.assertEqual(self.manifest["expanded_job_projection_sha256"], EXPECTED_SHA256)

    def test_method_version_or_unit_drift_breaks_frozen_projection(self) -> None:
        for field, changed in (("method_version", "2026.2"), ("unit", "mg/kg")):
            with self.subTest(field=field):
                drifted = copy.deepcopy(self.jobs)
                drifted[0][field] = changed
                self.assertEqual(len(drifted), EXPECTED_JOBS)
                digest = hashlib.sha256(_canonical_bytes(drifted)).hexdigest()
                self.assertNotEqual(digest, EXPECTED_SHA256)


if __name__ == "__main__":
    unittest.main()
