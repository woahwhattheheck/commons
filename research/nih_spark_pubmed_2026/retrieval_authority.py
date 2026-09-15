from __future__ import annotations

import importlib.abc
import importlib.machinery
import sys
from typing import Any, Mapping

from . import baseline as _base

RETRIEVAL_TOP_K = 5

# Capture the landed generation before installing the public authority wrappers.
_BASE_EVALUATE = _base.evaluate_bundle
_BASE_BUILD_RUN_RECEIPT = _base.build_run_receipt
_BASELINE_MODULE_NAME = _base.__name__
_RELOAD_FINDER_MARKER = "nih.spark.pubmed/retrieval-authority-reload-v1"


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
    # Every supported baseline reload generation is re-bound to this evaluator
    # before importlib.reload() returns, so deterministic authority is retained.
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


def _install_baseline_authority(module: Any = _base) -> None:
    if module is not _base:
        raise ImportError("unexpected NIH SPARK baseline module generation")
    module.evaluate_bundle = evaluate_bundle
    module.build_run_receipt = build_run_receipt
    module.verify_run_receipt = verify_run_receipt


class _BaselineReloadLoader(importlib.abc.Loader):
    """Delegate one ordinary baseline reload, then restore authority atomically."""

    def __init__(self, delegate: Any) -> None:
        self._delegate = delegate

    def create_module(self, spec: Any) -> Any:
        creator = getattr(self._delegate, "create_module", None)
        return creator(spec) if creator is not None else None

    def exec_module(self, module: Any) -> None:
        executor = getattr(self._delegate, "exec_module", None)
        if executor is None:
            raise ImportError("NIH SPARK baseline reload loader lacks exec_module")
        executor(module)
        _install_baseline_authority(module)


class _BaselineReloadFinder(importlib.abc.MetaPathFinder):
    """Wrap only importlib.reload() of the already-authorized baseline object."""

    _nih_spark_retrieval_authority_marker = _RELOAD_FINDER_MARKER

    def find_spec(self, fullname: str, path: Any, target: Any = None) -> Any:
        if fullname != _BASELINE_MODULE_NAME or target is not _base:
            return None
        spec = importlib.machinery.PathFinder.find_spec(fullname, path, target)
        if spec is None or spec.loader is None or not hasattr(spec.loader, "exec_module"):
            raise ImportError("NIH SPARK baseline reload source loader unavailable")
        spec.loader = _BaselineReloadLoader(spec.loader)
        return spec


def _install_reload_finder() -> None:
    # retrieval_authority itself may be reloaded. Remove any prior generation of
    # this narrowly-scoped finder so the current authority functions own reload.
    sys.meta_path[:] = [
        finder
        for finder in sys.meta_path
        if getattr(finder, "_nih_spark_retrieval_authority_marker", None)
        != _RELOAD_FINDER_MARKER
    ]
    sys.meta_path.insert(0, _BaselineReloadFinder())


# Package import executes __init__ before any supported submodule import can
# complete. The reload finder closes the ordinary importlib.reload split-generation
# escape by reinstalling this authority before a baseline reload returns.
_install_reload_finder()
_install_baseline_authority()
