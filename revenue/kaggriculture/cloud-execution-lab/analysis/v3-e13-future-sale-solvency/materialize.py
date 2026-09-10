#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Materialize the E13 future-sale solvency repair into a disconnected candidate.

The canonical source tree is read-only.  This tool authenticates the exact active
FrozenSelected source and pinned interpreter, replaces exactly one function by
AST span, compiles the result, and emits a deterministic receipt.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
from typing import Iterable

OPERATION = "TITAN-V3-E13-FUTURE-SALE-SOLVENCY-CLOSURE-20260910-01"
SOURCE_REL = Path("revenue/kaggriculture/cloud-execution-lab/frozen_selected.py")
ENGINE_REL = Path(
    "revenue/kaggriculture/cloud-execution-lab/reference/engine/kaggriculture.py"
)
EXPECTED_SOURCE_GIT_BLOB = "fc7baf5c179818a55037f6a61d92984d81d1a21c"
EXPECTED_ENGINE_GIT_BLOB = "3c202c7ee921da239356789e266b694635103fc4"
TARGET_FUNCTION = "funded_minimum_now"


class MaterializationError(RuntimeError):
    """Raised when exact-source or one-function custody cannot be proved."""


def git_blob_sha(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def find_repo_root(start: Path | None = None) -> Path:
    origin = (start or Path(__file__).resolve()).resolve()
    candidates: Iterable[Path] = (origin, *origin.parents)
    for candidate in candidates:
        if candidate.is_file():
            candidate = candidate.parent
        if (candidate / SOURCE_REL).is_file() and (candidate / ENGINE_REL).is_file():
            return candidate
    raise MaterializationError(
        f"could not locate repository root containing {SOURCE_REL} and {ENGINE_REL}"
    )


def _function_byte_span(source: bytes, function_name: str) -> tuple[int, int]:
    try:
        text = source.decode("utf-8")
        tree = ast.parse(text)
    except (UnicodeDecodeError, SyntaxError) as exc:
        raise MaterializationError(f"source parse failed: {exc}") from exc

    matches = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == function_name
    ]
    if len(matches) != 1:
        raise MaterializationError(
            f"expected exactly one top-level {function_name!r}, found {len(matches)}"
        )
    node = matches[0]
    if node.end_lineno is None:
        raise MaterializationError("Python AST did not report a function end line")

    lines = text.splitlines(keepends=True)
    start = len("".join(lines[: node.lineno - 1]).encode("utf-8"))
    end = len("".join(lines[: node.end_lineno]).encode("utf-8"))
    return start, end


REPLACEMENT_FUNCTION = r'''def funded_minimum_now(obs, config, base, farm, private, route, end,
                       current, targets, item, stress_units=32):
    """Smallest current sale preserving bounded inherited acquisition fills.

    E13's legacy prefix remains authoritative through the turn before the first
    future positive-cash SELL.  This successor additionally protects only fixed
    acquisitions on *strictly later turns* than that funding sale, crediting the
    exact represented future receipts rather than treating any positive receipt
    as a complete working-capital reset.  Acquisitions on the funding turn stay
    outside this repair so the separately owned order-aware escrow lane remains
    untouched.
    """
    now = int(obs['step'])
    baseline = max(0, int(current.get(item, 0)))
    max_orders = int(config.get('maxMarketOrdersPerTurn', 10))
    certificate = {
        'item': item, 'baseline_now': baseline, 'prefix_end': end,
        'funding_turn': None, 'stress_units': int(stress_units),
        'fallback': False,
    }
    try:
        reference_market = materialize_sales(
            base['market'], current, private['shed'], targets, max_orders)
        scout = _funding_trace(
            obs, config, farm, private, route, now, end,
            reference_market, stress_units=0)
        prefix_end, funding_turn = _funding_prefix_end(scout, now, end)
        certificate['prefix_end'] = prefix_end
        certificate['funding_turn'] = funding_turn
        if prefix_end == end:
            reference = scout
        else:
            reference = _funding_trace(
                obs, config, farm, private, route, now, prefix_end,
                reference_market, stress_units=0)

        prefix_required = {
            key: units for key, units in reference['acquisitions'] if units > 0}
        post_funding_required = (
            {
                key: units
                for key, units in scout['acquisitions']
                if units > 0 and key[0] > funding_turn
            }
            if funding_turn is not None
            else {}
        )
        required = dict(prefix_required)
        required.update(post_funding_required)
        comparison_end = end if post_funding_required else prefix_end

        certificate['prefix_reference_acquisitions'] = sum(
            prefix_required.values())
        certificate['post_funding_acquisitions'] = sum(
            post_funding_required.values())
        certificate['reference_acquisitions'] = sum(required.values())
        certificate['protected_acquisition_rows'] = len(required)
        certificate['comparison_end'] = comparison_end
        certificate['reference_terminal_cash'] = reference['cash']
        certificate['solvency_reference_terminal_cash'] = scout['cash']
        if not required:
            certificate['minimum_now'] = 0
            return 0, certificate

        for quantity in range(baseline + 1):
            totals = dict(current)
            totals[item] = quantity
            candidate_market = materialize_sales(
                base['market'], totals, private['shed'], targets, max_orders)
            traces = [
                _funding_trace(
                    obs, config, farm, private, route, now, comparison_end,
                    candidate_market, stress_units=0),
                _funding_trace(
                    obs, config, farm, private, route, now, comparison_end,
                    candidate_market, stress_units=stress_units),
            ]
            safe = True
            for trace in traces:
                filled = dict(trace['acquisitions'])
                if any(
                    filled.get(key, 0) < units
                    for key, units in required.items()
                ):
                    safe = False
                    break
            if safe:
                certificate['minimum_now'] = quantity
                certificate['scenario_terminal_cash'] = [
                    trace['cash'] for trace in traces]
                return quantity, certificate
    except Exception as exc:
        certificate['error'] = f'{type(exc).__name__}: {exc}'[:500]
    certificate['fallback'] = True
    certificate['minimum_now'] = baseline
    return baseline, certificate
'''.strip("\n") + "\n"


def build_candidate(source: bytes) -> bytes:
    if git_blob_sha(source) != EXPECTED_SOURCE_GIT_BLOB:
        raise MaterializationError(
            "active FrozenSelected source drift: "
            f"expected Git blob {EXPECTED_SOURCE_GIT_BLOB}, got {git_blob_sha(source)}"
        )
    required_anchors = (
        "def _funding_prefix_end(trace, now, end):",
        "if t > now and cash > 0:",
        "prefix_end, funding_turn = _funding_prefix_end(scout, now, end)",
        "reference = _funding_trace(",
        "for quantity in range(baseline + 1):",
    )
    text = source.decode("utf-8")
    missing = [anchor for anchor in required_anchors if anchor not in text]
    if missing:
        raise MaterializationError(f"authenticated source lacks anchors: {missing!r}")

    start, end = _function_byte_span(source, TARGET_FUNCTION)
    replacement = REPLACEMENT_FUNCTION.encode("utf-8")
    candidate = source[:start] + replacement + source[end:]
    if candidate == source:
        raise MaterializationError("candidate unexpectedly equals predecessor")
    try:
        compile(candidate, "<future-sale-solvency-candidate>", "exec")
    except SyntaxError as exc:
        raise MaterializationError(f"candidate compilation failed: {exc}") from exc

    _function_byte_span(candidate, TARGET_FUNCTION)
    candidate_text = candidate.decode("utf-8")
    if candidate_text.count("def funded_minimum_now(") != 1:
        raise MaterializationError("candidate target function cardinality is not one")
    if "comparison_end = end if post_funding_required else prefix_end" not in candidate_text:
        raise MaterializationError("candidate solvency boundary was not installed")
    return candidate


def materialize(root: Path, output: Path, receipt: Path) -> dict[str, object]:
    root = root.resolve()
    source_path = root / SOURCE_REL
    engine_path = root / ENGINE_REL
    source = source_path.read_bytes()
    engine = engine_path.read_bytes()

    source_blob = git_blob_sha(source)
    engine_blob = git_blob_sha(engine)
    if source_blob != EXPECTED_SOURCE_GIT_BLOB:
        raise MaterializationError(
            f"source Git blob mismatch: expected {EXPECTED_SOURCE_GIT_BLOB}, got {source_blob}"
        )
    if engine_blob != EXPECTED_ENGINE_GIT_BLOB:
        raise MaterializationError(
            f"engine Git blob mismatch: expected {EXPECTED_ENGINE_GIT_BLOB}, got {engine_blob}"
        )

    output = output.resolve()
    receipt = receipt.resolve()
    if output == source_path.resolve() or receipt == source_path.resolve():
        raise MaterializationError("refusing to overwrite canonical FrozenSelected source")
    if output == engine_path.resolve() or receipt == engine_path.resolve():
        raise MaterializationError("refusing to overwrite pinned interpreter source")
    if output == receipt:
        raise MaterializationError("candidate and receipt paths must differ")

    candidate = build_candidate(source)
    record: dict[str, object] = {
        "schema": "titan.v3.e13-future-sale-solvency.materialization.v1",
        "operation": OPERATION,
        "disposition": "SOURCE_REAL_ACTION_UNMEASURED",
        "source": {
            "path": SOURCE_REL.as_posix(),
            "git_blob_sha1": source_blob,
            "sha256": sha256(source),
            "bytes": len(source),
        },
        "engine": {
            "path": ENGINE_REL.as_posix(),
            "git_blob_sha1": engine_blob,
            "sha256": sha256(engine),
            "bytes": len(engine),
        },
        "candidate": {
            "function_replaced": TARGET_FUNCTION,
            "sha256": sha256(candidate),
            "bytes": len(candidate),
            "byte_delta": len(candidate) - len(source),
            "replacement_sha256": sha256(REPLACEMENT_FUNCTION.encode("utf-8")),
        },
        "custody": {
            "canonical_source_mutated": False,
            "canonical_engine_mutated": False,
            "replacement_count": 1,
            "post_sale_scope": "acquisition_turn_strictly_greater_than_funding_turn",
            "same_turn_order_aware_scope": "preserved_for_SOL_ESCROW",
            "canonical_runtime_or_archive_mutated": False,
        },
        "claims": {
            "gameplay_strength": False,
            "returned_action_activation": False,
            "score_causality": False,
            "promotion": False,
            "provider_or_kaggle_mutation": False,
        },
    }
    receipt_bytes = (
        json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")

    output.parent.mkdir(parents=True, exist_ok=True)
    receipt.parent.mkdir(parents=True, exist_ok=True)
    output_tmp = output.with_name(output.name + ".tmp")
    receipt_tmp = receipt.with_name(receipt.name + ".tmp")
    output_tmp.write_bytes(candidate)
    receipt_tmp.write_bytes(receipt_bytes)
    os.replace(output_tmp, output)
    os.replace(receipt_tmp, receipt)

    if source_path.read_bytes() != source or engine_path.read_bytes() != engine:
        raise MaterializationError("canonical source changed during materialization")
    if output.read_bytes() != candidate or receipt.read_bytes() != receipt_bytes:
        raise MaterializationError("written candidate or receipt failed readback")
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    args = parser.parse_args()
    root = args.root.resolve() if args.root else find_repo_root()
    record = materialize(root, args.output, args.receipt)
    print(json.dumps(record, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
