# SPDX-License-Identifier: Apache-2.0
"""Exact submitted-V4 wrapper-prefix causal ablation.

Evidence tooling only.  The treatment authenticates the exact submitted V4 and
V3.1 ``titan_runtime.py`` sources, then replaces exactly three already-enabled
wrapper methods in V4 with their submitted-V3.1 counterparts:

* ``_seed_selected``
* ``_operating_stock_selected``
* ``_redundant_hire_selected``

Every byte outside those method spans remains submitted V4.  This deliberately
recreates the older full-authored-market reasoning as a causal treatment; it is
NOT a proposal to violate the official engine's executable-prefix semantics.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

SOURCE_PATH = "revenue/kaggriculture/cloud-execution-lab/titan_runtime.py"
CONFIG_PATH = "revenue/kaggriculture/cloud-execution-lab/TITAN-CONFIG.json"
V31_SOURCE_COMMIT = "a90d888f03987ef0b35cfd20ec3519c6144db08a"
V4_SOURCE_COMMIT = "4af1113154e78c662780e6658cd920daac7902e3"
V31_RUNTIME_GIT_BLOB = "a10ad66f990c430dc27299f518b04ea3fde9e39b"
V4_RUNTIME_GIT_BLOB = "998bf5da08f61f82eafaf5750c8a86fc3adad7fb"
V4_ARCHIVE_SHA256 = "4d9601552b5e25d02d8a33961c0bed54ed92d032dbcd4a72f6ab8e03515ed21b"
TARGET_METHODS = (
    "_seed_selected",
    "_operating_stock_selected",
    "_redundant_hire_selected",
)
SCHEMA = "titan-v5-v31-v4-runtime-prefix-ablation-v1"


class SourceAuthorityError(ValueError):
    """Exact historical source authority did not match the treatment contract."""


def git_blob_sha1(raw: bytes) -> str:
    return hashlib.sha1(f"blob {len(raw)}\0".encode("ascii") + raw).hexdigest()


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _decode_exact(raw: bytes, *, label: str) -> str:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SourceAuthorityError(f"{label} source is not UTF-8") from exc
    if "\r\n" in text:
        raise SourceAuthorityError(f"{label} source unexpectedly contains CRLF")
    return text


def method_span(text: str, name: str) -> tuple[int, int]:
    """Return the unique class-method byte span, excluding the next def newline."""
    needle = f"    def {name}("
    starts = []
    pos = 0
    while True:
        pos = text.find(needle, pos)
        if pos < 0:
            break
        starts.append(pos)
        pos += len(needle)
    if len(starts) != 1:
        raise SourceAuthorityError(
            f"{name}: expected one method definition, found {len(starts)}"
        )
    start = starts[0]
    end = text.find("\n    def ", start + len(needle))
    if end < 0:
        raise SourceAuthorityError(f"{name}: could not locate following method")
    return start, end


def method_text(text: str, name: str) -> str:
    start, end = method_span(text, name)
    return text[start:end]


def skeleton(text: str) -> str:
    """Remove target method bodies so non-treatment bytes can be compared exactly."""
    out = text
    for name in TARGET_METHODS:
        start, end = method_span(out, name)
        out = out[:start] + f"    # <{name}:runtime-prefix-treatment>" + out[end:]
    return out


def ablate_submitted_v4(v4_raw: bytes, v31_raw: bytes) -> tuple[bytes, dict[str, Any]]:
    """Replace only the three wrapper-prefix methods with exact V3.1 versions."""
    v4_blob = git_blob_sha1(v4_raw)
    v31_blob = git_blob_sha1(v31_raw)
    if v4_blob != V4_RUNTIME_GIT_BLOB:
        raise SourceAuthorityError(
            f"submitted V4 runtime blob mismatch: {v4_blob} != {V4_RUNTIME_GIT_BLOB}"
        )
    if v31_blob != V31_RUNTIME_GIT_BLOB:
        raise SourceAuthorityError(
            f"submitted V3.1 runtime blob mismatch: {v31_blob} != {V31_RUNTIME_GIT_BLOB}"
        )

    v4_text = _decode_exact(v4_raw, label="submitted V4")
    v31_text = _decode_exact(v31_raw, label="submitted V3.1")
    out = v4_text
    method_receipts: dict[str, dict[str, str]] = {}

    for name in TARGET_METHODS:
        old = method_text(v4_text, name)
        replacement = method_text(v31_text, name)
        if old == replacement:
            raise SourceAuthorityError(f"{name}: V3.1 and V4 method bytes unexpectedly equal")
        if out.count(old) != 1:
            raise SourceAuthorityError(
                f"{name}: expected one exact submitted-V4 method postimage match, found {out.count(old)}"
            )
        out = out.replace(old, replacement, 1)
        method_receipts[name] = {
            "v4_sha256": sha256(old.encode("utf-8")),
            "v31_sha256": sha256(replacement.encode("utf-8")),
        }

    # Strong causal-boundary assertion: nothing outside the three method spans moved.
    if skeleton(out) != skeleton(v4_text):
        raise AssertionError("treatment changed bytes outside the three target methods")
    for name in TARGET_METHODS:
        if method_text(out, name) != method_text(v31_text, name):
            raise AssertionError(f"{name}: treatment is not exact submitted-V3.1 method bytes")

    treatment = out.encode("utf-8")
    compile(treatment, f"{SOURCE_PATH}:runtime-prefix-ablated", "exec")
    if treatment == v4_raw:
        raise AssertionError("runtime-prefix treatment produced no source change")

    receipt: dict[str, Any] = {
        "schema": SCHEMA,
        "source_path": SOURCE_PATH,
        "control_source_commit": V4_SOURCE_COMMIT,
        "control_source_git_blob": V4_RUNTIME_GIT_BLOB,
        "control_source_sha256": sha256(v4_raw),
        "reference_v31_source_commit": V31_SOURCE_COMMIT,
        "reference_v31_source_git_blob": V31_RUNTIME_GIT_BLOB,
        "treatment_source_git_blob": git_blob_sha1(treatment),
        "treatment_source_sha256": sha256(treatment),
        "target_methods": list(TARGET_METHODS),
        "method_receipts": method_receipts,
        "control_archive_sha256": V4_ARCHIVE_SHA256,
        "causal_question": "submitted V4 executable-prefix wrapper semantics vs submitted V3.1 full-queue semantics",
    }
    return treatment, receipt


def _is_order(row: Any, *head: str) -> bool:
    return isinstance(row, list) and len(row) >= len(head) and tuple(row[: len(head)]) == head


def classify_structural_candidate(action: Mapping[str, Any], cfg: Mapping[str, Any]) -> dict[str, Any]:
    """Cheap, policy-inert natural-engagement screen for native returned actions.

    This does not claim an action divergence.  It identifies callbacks where the
    V3.1 full-queue and V4 prefix wrappers receive observably different scopes or
    activation gates, so an executor knows whether expensive paired replay is warranted.
    """
    market = action.get("market")
    if not isinstance(market, list):
        return {"candidate": False, "reason": "market_not_list"}
    try:
        cap = max(1, int(cfg.get("maxMarketOrdersPerTurn", 10)))
    except (TypeError, ValueError, OverflowError):
        return {"candidate": False, "reason": "invalid_market_cap"}

    prefix = market[:cap]
    suffix = market[cap:]
    old_seed = any(_is_order(row, "BUY_SEED") for row in market)
    new_seed = any(_is_order(row, "BUY_SEED") for row in prefix)
    old_fert = any(_is_order(row, "SELL", "FERTILIZER") for row in market)
    new_fert = any(_is_order(row, "SELL", "FERTILIZER") for row in prefix)
    old_hire = any(_is_order(row, "HIRE") for row in market)
    new_hire = any(_is_order(row, "HIRE") for row in prefix)
    nonempty_suffix = any(bool(row) for row in suffix)

    report = {
        "candidate": False,
        "reason": "no_scope_or_gate_delta",
        "cap": cap,
        "market_rows": len(market),
        "suffix_rows": len(suffix),
        "nonempty_suffix": nonempty_suffix,
        "seed_gate_delta": old_seed != new_seed,
        "seed_scope_candidate": bool(new_seed and nonempty_suffix),
        "operating_stock_gate_delta": old_fert != new_fert,
        "operating_stock_scope_candidate": bool(new_fert and nonempty_suffix),
        "redundant_hire_gate_delta": old_hire != new_hire,
    }
    report["candidate"] = any(
        bool(report[key])
        for key in (
            "seed_gate_delta",
            "seed_scope_candidate",
            "operating_stock_gate_delta",
            "operating_stock_scope_candidate",
            "redundant_hire_gate_delta",
        )
    )
    if report["candidate"]:
        report["reason"] = "wrapper_scope_or_gate_diff"
    return report


def _main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("v4_runtime", type=Path, help="exact submitted-V4 titan_runtime.py")
    parser.add_argument("v31_runtime", type=Path, help="exact submitted-V3.1 titan_runtime.py")
    parser.add_argument("output", type=Path, help="write treatment titan_runtime.py here")
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()

    treatment, receipt = ablate_submitted_v4(
        args.v4_runtime.read_bytes(), args.v31_runtime.read_bytes()
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(treatment)
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
