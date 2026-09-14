from __future__ import annotations

from pathlib import Path
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import acqatlas
import validate_strict


class StrictValidationTests(unittest.TestCase):
    def setUp(self):
        self.docs = [
            acqatlas.Document("a-1", "Alpha one", "alpha apple cloud", "A"),
            acqatlas.Document("a-2", "Alpha two", "alpha apple platform", "A"),
            acqatlas.Document("b-1", "Beta one", "beta banana aircraft", "B"),
            acqatlas.Document("b-2", "Beta two", "beta banana avionics", "B"),
        ]

    def test_projection_uses_only_fitted_terms(self):
        projected = validate_strict.project_tfidf(
            acqatlas.Document("q", "Query", "known heldout-only", "A"),
            {"known": 2.0},
        )
        self.assertEqual(set(projected), {"known"})
        self.assertAlmostEqual(projected["known"], 1.0)

    def test_each_idf_fit_excludes_held_out_target(self):
        calls: list[tuple[str, ...]] = []
        original = acqatlas.sparse_tfidf

        def recording_fit(docs):
            calls.append(tuple(sorted(doc.doc_id for doc in docs)))
            return original(docs)

        with mock.patch.object(acqatlas, "sparse_tfidf", side_effect=recording_fit):
            result = validate_strict.validate_leave_one_out_strict(self.docs, top_k=2)

        ordered_targets = [doc.doc_id for doc in sorted(self.docs, key=lambda doc: doc.doc_id)]
        self.assertEqual(len(calls), len(ordered_targets))
        all_ids = {doc.doc_id for doc in self.docs}
        for target_id, fit_ids in zip(ordered_targets, calls):
            self.assertNotIn(target_id, fit_ids)
            self.assertEqual(set(fit_ids), all_ids - {target_id})
        self.assertEqual(result["validation_mode"], "strict-held-out-idf-v1")
        self.assertEqual(result["top1_accuracy"], 1.0)
        self.assertEqual(result["top2_recall"], 1.0)
        self.assertTrue(all(row["fit_document_count"] == 3 for row in result["rows"]))

    def test_rejects_nonpositive_top_k(self):
        with self.assertRaisesRegex(ValueError, "top_k"):
            validate_strict.validate_leave_one_out_strict(self.docs, top_k=0)


if __name__ == "__main__":
    unittest.main()
