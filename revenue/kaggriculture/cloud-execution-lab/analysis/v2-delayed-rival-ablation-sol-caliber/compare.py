# SPDX-License-Identifier: Apache-2.0
"""Compare frozen V2 with the delayed-rival stress-scenario ablation."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any, Mapping

HERE = Path(__file__).resolve().parent
BASE_COMPARATOR = (
    HERE.parent / "v2-target-domain-ablation-sol-bulwark" / "compare.py"
)

OPERATION = "titan-v2-delayed-rival-ablation-20260909-sol-caliber-01"
EXPECTED_BASE_COMPARATOR_BLOB = "6d66238b2ce1f11f26752049c106502be5ef0ec7"
EXPECTED_KIND = "delayed_rival_stress_scenarios"
EXPECTED_REMOVED_SCENARIOS = [
    "observed_next_turn",
    "observed_before_delayed_batch",
]
EXPECTED_MARKERS = {
    "tuple_rival_schedule_scoring",
    "full_continuation_value",
    "forced_feasibility_admission",
    "forced_feasibility_priority",
    "all_shed_target_domain",
    "per_index_queue_rewrite",
}


class CompareError(ValueError):
    """The reports, receipt, or inherited comparator are not exact."""


def git_blob_sha1(data: bytes) -> str:
    header = b"blob " + str(len(data)).encode("ascii") + b"\0"
    return hashlib.sha1(header + data).hexdigest()


def _load_base() -> ModuleType:
    try:
        data = BASE_COMPARATOR.read_bytes()
    except OSError as exc:
        raise CompareError(
            f"merged base comparator is unavailable: {BASE_COMPARATOR}: {exc}"
        ) from exc
    actual = git_blob_sha1(data)
    if actual != EXPECTED_BASE_COMPARATOR_BLOB:
        raise CompareError(
            "merged base comparator drift: "
            f"expected {EXPECTED_BASE_COMPARATOR_BLOB}, got {actual}"
        )
    spec = importlib.util.spec_from_file_location(
        "_sol_caliber_v2_delayed_rival_base_comparator",
        BASE_COMPARATOR,
    )
    if spec is None or spec.loader is None:
        raise CompareError("cannot construct base comparator import")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def strict_object(path: Path) -> dict[str, Any]:
    base = _load_base()
    try:
        return base.strict_object(path)
    except base.CompareError as exc:
        raise CompareError(str(exc)) from exc


def validate_receipt(receipt: Mapping[str, Any]) -> dict[str, Any]:
    if receipt.get("operation") != OPERATION:
        raise CompareError("materialization receipt operation mismatch")
    ablation = receipt.get("ablation")
    if not isinstance(ablation, Mapping):
        raise CompareError("materialization receipt ablation is missing")
    if ablation.get("kind") != EXPECTED_KIND:
        raise CompareError("materialization receipt ablation kind mismatch")
    if ablation.get("removed_scenario_names") != EXPECTED_REMOVED_SCENARIOS:
        raise CompareError("removed delayed-rival scenario identity mismatch")
    markers = ablation.get("preserved_v2_markers")
    if (
        not isinstance(markers, Mapping)
        or set(markers) != EXPECTED_MARKERS
        or any(value is not True for value in markers.values())
    ):
        raise CompareError("preserved V2 feature custody is incomplete")
    base = _load_base()
    try:
        return base.validate_receipt(receipt)
    except base.CompareError as exc:
        raise CompareError(str(exc)) from exc


def compare(
    control: Mapping[str, Any],
    candidate: Mapping[str, Any],
    receipt: Mapping[str, Any],
    *,
    git_head: str,
) -> dict[str, Any]:
    validate_receipt(receipt)
    base = _load_base()
    try:
        report = base.compare(
            control,
            candidate,
            receipt,
            git_head=git_head,
        )
    except base.CompareError as exc:
        raise CompareError(str(exc)) from exc
    report["operation"] = OPERATION
    report["hypothesis"] = {
        "source": "frozen_v2",
        "ablation": EXPECTED_KIND,
        "control_scenarios": [
            "no_rival",
            "observed_paired",
            "observed_later_order",
            *EXPECTED_REMOVED_SCENARIOS,
        ],
        "candidate_scenarios": [
            "no_rival",
            "observed_paired",
            "observed_later_order",
        ],
        "preserved_v2_markers": sorted(EXPECTED_MARKERS),
    }
    report["reason"] = str(report["reason"]).replace(
        "target-domain ablation",
        "delayed-rival stress-scenario ablation",
    )
    return report


def markdown(report: Mapping[str, Any]) -> str:
    base = _load_base()
    rendered = base.markdown(report)
    rendered = rendered.replace(
        "# TITAN V2 target-domain ablation",
        "# TITAN V2 delayed-rival stress-scenario ablation",
    )
    rendered = rendered.replace(
        "target-domain ablation",
        "delayed-rival stress-scenario ablation",
    )
    return rendered


def atomic_write(path: Path, text: str) -> None:
    base = _load_base()
    base.atomic_write(path, text)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = compare(
            strict_object(args.control),
            strict_object(args.candidate),
            strict_object(args.receipt),
            git_head=args.head,
        )
    except CompareError as exc:
        report = {
            "schema_version": 1,
            "operation": OPERATION,
            "git_head": args.head,
            "verdict": "INVALID",
            "reason": str(exc),
            "exit_code": 2,
        }
    atomic_write(
        args.output,
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
    )
    atomic_write(args.markdown, markdown(report))
    print(
        json.dumps(
            {
                "verdict": report["verdict"],
                "reason": report["reason"],
                "exit_code": report["exit_code"],
                "overall": report.get("overall"),
                "by_opponent": report.get("by_opponent"),
            },
            sort_keys=True,
        )
    )
    return int(report["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
