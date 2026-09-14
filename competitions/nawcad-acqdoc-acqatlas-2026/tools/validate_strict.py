#!/usr/bin/env python3
"""Leakage-free held-out validation for AcqAtlas.

Fit IDF only on each training fold, then project the held-out query into that
frozen feature space.  The held-out document's text may be scored, but it must
not alter document-frequency statistics used to fit the training vectors.
"""
from __future__ import annotations

import argparse
from collections import Counter
import math
from pathlib import Path
import sys
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import acqatlas

VALIDATION_MODE = "strict-held-out-idf-v1"


def project_tfidf(doc: acqatlas.Document, idf: dict[str, float]) -> dict[str, float]:
    """Project one document using IDF learned exclusively from a training fold."""
    counts = Counter(acqatlas.features(doc.title + "\n" + doc.text))
    weighted = {
        term: (1.0 + math.log(count)) * idf[term]
        for term, count in counts.items()
        if term in idf
    }
    norm = math.sqrt(sum(value * value for value in weighted.values())) or 1.0
    return {term: value / norm for term, value in sorted(weighted.items())}


def validate_leave_one_out_strict(
    docs: Sequence[acqatlas.Document], *, top_k: int = 5
) -> dict:
    labeled = [doc for doc in docs if doc.vehicle]
    if len(labeled) < 2:
        raise ValueError("validation requires at least two labeled documents")
    if top_k < 1:
        raise ValueError("top_k must be >=1")

    hits1 = hitsk = 0
    rows: list[dict] = []
    for target in sorted(labeled, key=lambda doc: doc.doc_id):
        train_docs = [doc for doc in docs if doc.doc_id != target.doc_id]
        train_vectors, idf = acqatlas.sparse_tfidf(train_docs)
        vectors = dict(train_vectors)
        vectors[target.doc_id] = project_tfidf(target, idf)
        token_counts = {
            doc.doc_id: Counter(acqatlas.tokenize(doc.title + "\n" + doc.text))
            for doc in [*train_docs, target]
        }
        recs = acqatlas.recommend_for(
            target,
            train_docs,
            vectors,
            token_counts,
            top_k=top_k,
            exclude_self=False,
        )
        predicted = [row["vehicle"] for row in recs]
        acceptable = set(
            target.acceptable_vehicles
            or ((target.vehicle,) if target.vehicle else ())
        )
        top1 = bool(predicted and predicted[0] in acceptable)
        topk_hit = any(vehicle in acceptable for vehicle in predicted)
        hits1 += int(top1)
        hitsk += int(topk_hit)
        rows.append(
            {
                "doc_id": target.doc_id,
                "actual": target.vehicle,
                "acceptable": sorted(acceptable),
                "predicted": predicted,
                "top1_hit": top1,
                f"top{top_k}_hit": topk_hit,
                "fit_document_count": len(train_docs),
                "fit_document_manifest_sha256": acqatlas.document_manifest_sha256(train_docs),
            }
        )

    return {
        "validation_mode": VALIDATION_MODE,
        "labeled_documents": len(labeled),
        "top1_accuracy": round(hits1 / len(labeled), 6),
        f"top{top_k}_recall": round(hitsk / len(labeled), 6),
        "rows": rows,
    }


def cli(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args(argv)
    docs = acqatlas.load_documents(args.input)
    result = validate_leave_one_out_strict(docs, top_k=args.top_k)
    print(acqatlas.canonical_json_bytes(result).decode("utf-8"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(cli())
