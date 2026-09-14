from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import acqatlas
import validate_strict

FIXTURE = ROOT / "fixtures" / "synthetic_procurements.jsonl"


class StrictFixtureValidationTests(unittest.TestCase):
    def test_public_fixture_strict_leave_one_out(self):
        docs = acqatlas.load_documents(FIXTURE)
        result = validate_strict.validate_leave_one_out_strict(docs, top_k=5)

        self.assertEqual(result["validation_mode"], "strict-held-out-idf-v1")
        self.assertEqual(result["labeled_documents"], 20)
        self.assertGreaterEqual(result["top1_accuracy"], 0.75)
        self.assertGreaterEqual(result["top5_recall"], 0.95)
        self.assertTrue(all(row["fit_document_count"] == 19 for row in result["rows"]))
        self.assertEqual(
            len({row["fit_document_manifest_sha256"] for row in result["rows"]}),
            20,
        )


if __name__ == "__main__":
    unittest.main()
