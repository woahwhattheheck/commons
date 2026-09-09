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
LAB = HERE.parent.parent
KAG = LAB.parent
ENGINE_DIR = LAB / "reference" / "engine"
LOADER_PATH = KAG / "20260907-offline-agent" / "evaluate.py"
EVALUATOR_PATH = KAG / "cloud-eval" / "evaluate.py"
V2_ENTRY_PATH = LAB / "runtime" / "variants" / "v2" / "candidate.py"
V1_ENTRY_PATH = LAB / "runtime" / "variants" / "v1" / "candidate.py"
ARLENE_PATH = (
    LAB / "runtime" / "variants" / "v1" / "reference" / "next-panel"
    / "vendor" / "arlene.py"
)
ENGINE_FILES = ("kaggriculture.py", "kaggriculture.json", "utils.py")
EXPECTED_ENGINE_REF = "28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c"
EXPECTED_SEEDS = [539131249, 1834999074, 2609097301, 2611092207]
EXPECTED_AGENT_RNG_SEED = 20260909

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


def sha256_file(path: Path, label: str) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise CompareError(f"cannot hash pinned {label}: {path}: {exc}") from exc


def _agent_fingerprint(path: Path) -> dict[str, str]:
    return {
        "entry": path.name,
        "callable": "agent",
        "sha256": sha256_file(path, str(path.relative_to(KAG))),
    }


def expected_report_custody() -> dict[str, Any]:
    """Derive the exact evaluator identities from this checked-out source tree."""
    return {
        "engine_ref": EXPECTED_ENGINE_REF,
        "engine_sha256": {
            name: sha256_file(ENGINE_DIR / name, f"engine/{name}")
            for name in ENGINE_FILES
        },
        "loader_sha256": sha256_file(LOADER_PATH, "offline loader"),
        "evaluator_sha256": sha256_file(EVALUATOR_PATH, "cloud evaluator"),
        "candidate": _agent_fingerprint(V2_ENTRY_PATH),
        "opponents": {
            "arlene": _agent_fingerprint(ARLENE_PATH),
            "v1": _agent_fingerprint(V1_ENTRY_PATH),
        },
        "seeds": list(EXPECTED_SEEDS),
        "agent_rng_seed": EXPECTED_AGENT_RNG_SEED,
    }


def validate_report_custody(report: Mapping[str, Any], label: str) -> dict[str, Any]:
    """Bind report-declared execution identity to exact on-disk workflow inputs."""
    if not isinstance(report, Mapping):
        raise CompareError(f"{label} report is not an object")
    expected = expected_report_custody()
    for key in (
        "engine_ref",
        "engine_sha256",
        "loader_sha256",
        "evaluator_sha256",
        "candidate",
        "opponents",
        "seeds",
        "agent_rng_seed",
    ):
        if report.get(key) != expected[key]:
            raise CompareError(f"{label} {key} does not match the exact workflow input")
    games = report.get("games")
    if not isinstance(games, list):
        raise CompareError(f"{label} games is not a list")
    for index, game in enumerate(games):
        if not isinstance(game, Mapping):
            raise CompareError(f"{label} game {index} is not an object")
        opponent = game.get("opponent")
        seed = game.get("seed")
        seat = game.get("candidate_seat")
        if opponent not in expected["opponents"]:
            raise CompareError(f"{label} game {index} opponent is outside the workflow grid")
        if type(seed) is not int or seed not in EXPECTED_SEEDS:
            raise CompareError(f"{label} game {index} seed is outside the literal workflow grid")
        if type(seat) is not int or seat not in (0, 1):
            raise CompareError(f"{label} game {index} candidate seat must be integer 0 or 1")
    return expected


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
    validate_report_custody(control, "control")
    validate_report_custody(candidate, "candidate")
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
