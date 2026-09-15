from __future__ import annotations

import copy
import unittest

from research.nih_spark_pubmed_2026 import (
    ContractError,
    RETRIEVAL_TOP_K,
    SCHEMA_ANSWER,
    bm25_retrieve,
    build_run_receipt,
    evaluate_bundle,
    text_sha256,
    verify_run_receipt,
)
from research.nih_spark_pubmed_2026 import retrieval_authority as authority


def _document(document_id: str, text: str) -> dict:
    return {
        "document_id": document_id,
        "version": "v1",
        "license": "synthetic-test-only",
        "provenance": "post-merge predecessor killer",
        "title": document_id,
        "text_sha256": text_sha256(text),
        "passages": [{"passage_id": "P1", "text": text}],
    }


CORPUS = {
    "schema": "nih.spark.pubmed.corpus/v1",
    "documents": [
        *[_document(f"D-DECOY-{index}", "alpha alpha alpha alpha") for index in range(5)],
        _document("D-TARGET", "alpha"),
    ],
}
CASES = {
    "schema": "nih.spark.pubmed.cases/v1",
    "cases": [
        {
            "query_id": "Q-DEPTH",
            "query": "alpha",
            "expected_document_ids": ["D-TARGET"],
            "expected_answerability": "UNANSWERABLE",
            "expected_contradiction_document_sets": [],
        }
    ],
}
ANSWERS = {
    "Q-DEPTH": {
        "schema": SCHEMA_ANSWER,
        "query_id": "Q-DEPTH",
        "answerability": "UNANSWERABLE",
        "claims": [],
        "contradiction_groups": [],
        "follow_up_actions": [
            "Inspect the highest-ranked source passage.",
            "Compare another independently sourced document.",
            "Record unresolved uncertainty before acting.",
        ],
    }
}


class RetrievalAuthorityTests(unittest.TestCase):
    def canonical(self) -> dict:
        return {
            "Q-DEPTH": bm25_retrieve(
                CORPUS,
                "alpha",
                top_k=RETRIEVAL_TOP_K,
            )
        }

    def test_canonical_retrieval_depth_is_receipt_bound(self):
        retrievals = self.canonical()
        self.assertEqual(len(retrievals["Q-DEPTH"]), RETRIEVAL_TOP_K)
        self.assertNotIn(
            "D-TARGET",
            {row["document_id"] for row in retrievals["Q-DEPTH"]},
        )
        evaluation = evaluate_bundle(CORPUS, CASES, retrievals, ANSWERS)
        self.assertEqual(evaluation["retrieval_top_k"], RETRIEVAL_TOP_K)
        self.assertEqual(evaluation["retrieval_hit_at_k"], 0.0)
        receipt = build_run_receipt(
            corpus=CORPUS,
            cases=CASES,
            retrievals=retrievals,
            answers=ANSWERS,
            evaluation=evaluation,
            source_version="authority-v1",
        )
        self.assertEqual(receipt["retrieval_top_k"], RETRIEVAL_TOP_K)
        self.assertTrue(
            verify_run_receipt(
                receipt,
                corpus=CORPUS,
                cases=CASES,
                retrievals=retrievals,
                answers=ANSWERS,
                evaluation=evaluation,
                source_version="authority-v1",
            )
        )

    def test_injected_expected_document_cannot_mint_perfect_receipt(self):
        forged = self.canonical()
        forged["Q-DEPTH"] = [
            {"document_id": "D-TARGET", "passage_id": "P1", "score": 999.0},
            *forged["Q-DEPTH"][: RETRIEVAL_TOP_K - 1],
        ]
        predecessor = authority._BASE_EVALUATE(CORPUS, CASES, forged, ANSWERS)
        self.assertEqual(predecessor["retrieval_hit_at_k"], 1.0)
        self.assertEqual(predecessor["retrieval_mrr"], 1.0)
        with self.assertRaisesRegex(ContractError, "canonical BM25 evidence"):
            evaluate_bundle(CORPUS, CASES, forged, ANSWERS)

    def test_rank_after_k_and_rescored_rows_are_rejected(self):
        over_depth = self.canonical()
        over_depth["Q-DEPTH"].append(
            {"document_id": "D-TARGET", "passage_id": "P1", "score": 0.000001}
        )
        predecessor = authority._BASE_EVALUATE(CORPUS, CASES, over_depth, ANSWERS)
        self.assertEqual(predecessor["retrieval_hit_at_k"], 1.0)
        with self.assertRaisesRegex(ContractError, "retrieval_top_k=5"):
            evaluate_bundle(CORPUS, CASES, over_depth, ANSWERS)

        rescored = self.canonical()
        rescored = copy.deepcopy(rescored)
        rescored["Q-DEPTH"][0]["score"] += 1.0
        with self.assertRaisesRegex(ContractError, "canonical BM25 evidence"):
            evaluate_bundle(CORPUS, CASES, rescored, ANSWERS)


if __name__ == "__main__":
    unittest.main()
