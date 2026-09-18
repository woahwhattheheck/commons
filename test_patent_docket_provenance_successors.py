#!/usr/bin/env python3
"""Regression coverage for known additive patent-docket provenance successors."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("patent_docket", ROOT / "host/patent_docket.py")
patent_docket = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(patent_docket)


class PatentDocketProvenanceSuccessorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.docket, cls.schema = patent_docket.load(ROOT)

    def test_current_docket_validates_without_repinning_historical_provenance(self):
        result = patent_docket.validate(ROOT, self.docket, self.schema)
        self.assertEqual(result["status"], "VALID")
        self.assertEqual(result["entries"], 3)

    def test_known_successors_restore_exact_historical_provenance_blobs(self):
        expected = {
            "ground/INVENTION_BURST_INDEX.md": (
                self.docket["inventor_provenance"]["blob_sha"],
                ["spy-ground-live-cash-v1"],
            ),
            "GRANTS.md": (
                self.docket["status_provenance"]["blob_sha"],
                ["bass-grants-live-cash-v2"],
            ),
        }
        for path, (blob_sha, labels) in expected.items():
            raw = (ROOT / path).read_bytes()
            normalized, applied = patent_docket._normalize_provenance_successors(
                path, raw
            )
            self.assertEqual(patent_docket._git_blob_oid(normalized), blob_sha)
            self.assertEqual(applied, labels)

    def test_unknown_successor_is_not_normalized(self):
        path = "GRANTS.md"
        unknown = b"historical\nunrecognized successor\n"
        normalized, applied = patent_docket._normalize_provenance_successors(
            path, unknown
        )
        self.assertEqual(normalized, unknown)
        self.assertEqual(applied, [])

    def test_duplicate_known_successor_fails_ambiguous(self):
        path = "GRANTS.md"
        _, block = patent_docket.PROVENANCE_SUCCESSORS[path][0]
        with self.assertRaisesRegex(
            patent_docket.DocketError,
            "successor bass-grants-live-cash-v2 is ambiguous",
        ):
            patent_docket._normalize_provenance_successors(
                path, b"historical\n" + block + block
            )


if __name__ == "__main__":
    unittest.main()
