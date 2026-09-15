from __future__ import annotations

from typing import Any, Mapping

from . import baseline as _base

RETRIEVAL_TOP_K = 5

# Capture the landed generation before installing the public authority wrappers.
_BASE_EVALUATE = _base.evaluate_bundle
_BASE_BUILD_RUN_RECEIPT = _base.build_run_receipt


def _canonical_retrievals(corpus: Any, cases: Any) -> dict[str, list[dict[str, Any]]]:
    normalized_cases = _base.load_cases(cases)
    return {
        case["query_id"]: _base.bm25_retrieve(
            corpus,
            case["query"],
            top_k=RETRIEVAL_TOP_K,
        )
        for case in normalized_cases["cases"]
    }


def evaluate_bundle(
    corpus: Any,
    cases: Any,
    retrievals: Mapping[str, list[dict[str, Any]]],
    answers: Mapping[str, Any],
) -> dict[str, Any]:
    # Run the landed evaluator first so its exact schema/citation/error contract is
    # preserved for malformed evidence. Only structurally valid evidence reaches
    # the stronger deterministic-retrieval authority check below.
    evaluation = _BASE_EVALUATE(corpus, cases, retrievals, answers)

    if type(retrievals) is not dict:
        raise _base.ContractError("retrievals must be an exact object")
    canonical = _canonical_retrievals(corpus, cases)
    if retrievals != canonical:
        raise _base.ContractError(
            "retrievals differ from canonical BM25 evidence at retrieval_top_k=5"
        )

    return {
        **evaluation,
        "retrieval_top_k": RETRIEVAL_TOP_K,
    }


def build_run_receipt(
    *,
    corpus: Any,
    cases: Any,
    retrievals: Mapping[str, Any],
    answers: Mapping[str, Any],
    evaluation: Any,
    source_version: str,
) -> dict[str, Any]:
    # The landed builder resolves its evaluator through baseline module globals.
    # After the install at module end, this call therefore re-evaluates through
    # the canonical retrieval authority above before minting any receipt.
    receipt = _BASE_BUILD_RUN_RECEIPT(
        corpus=corpus,
        cases=cases,
        retrievals=retrievals,
        answers=answers,
        evaluation=evaluation,
        source_version=source_version,
    )
    payload = dict(receipt)
    payload.pop("receipt_sha256", None)
    payload["retrieval_top_k"] = RETRIEVAL_TOP_K
    payload["receipt_sha256"] = _base.semantic_sha256(payload)
    return payload


def verify_run_receipt(receipt: Any, **kwargs: Any) -> bool:
    return type(receipt) is dict and receipt == build_run_receipt(**kwargs)


# Package import executes __init__ before any supported submodule import can
# complete, so direct imports of baseline.evaluate_bundle/build_run_receipt after
# package initialization receive the same authority boundary instead of a bypass.
_base.evaluate_bundle = evaluate_bundle
_base.build_run_receipt = build_run_receipt
_base.verify_run_receipt = verify_run_receipt
