# SPDX-License-Identifier: Apache-2.0
"""Execution-bound facade over the V2 target-domain causal comparator."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

import compare
import execution_bind


class BoundCompareError(compare.CompareError):
    """A panel report is not bound to its self-checking package entrypoint."""


def candidate_identity(report: Mapping[str, Any], label: str) -> dict[str, Any]:
    candidate = report.get("candidate")
    if not isinstance(candidate, Mapping):
        raise BoundCompareError(f"{label} candidate identity missing")
    return {
        "entry": candidate.get("entry"),
        "callable": candidate.get("callable"),
        "sha256": candidate.get("sha256"),
    }


def validate_reports(
    control: Mapping[str, Any],
    candidate: Mapping[str, Any],
    normalized_binding: Mapping[str, Any],
) -> str:
    wrapper_sha = normalized_binding.get("wrapper_source_sha256")
    for label, report in (("control", control), ("candidate", candidate)):
        arm = normalized_binding[label]
        expected = {
            "entry": arm["entry"],
            "callable": arm["callable"],
            "sha256": arm["wrapper_sha256"],
        }
        actual = candidate_identity(report, label)
        if actual != expected:
            raise BoundCompareError(
                f"{label} report is not bound to {arm['package']} closure: "
                f"expected {expected!r}, got {actual!r}"
            )
    if normalized_binding["control"]["entry"] == normalized_binding["candidate"]["entry"]:
        raise BoundCompareError("control and candidate report entry names are not distinct")
    if normalized_binding["control"]["wrapper_sha256"] != wrapper_sha:
        raise BoundCompareError("control wrapper identity mismatch")
    if normalized_binding["candidate"]["wrapper_sha256"] != wrapper_sha:
        raise BoundCompareError("candidate wrapper identity mismatch")
    return str(wrapper_sha)


def bound_compare(
    control: Mapping[str, Any],
    candidate: Mapping[str, Any],
    receipt: Mapping[str, Any],
    binding: Mapping[str, Any],
    *,
    root: Path,
    git_head: str,
) -> dict[str, Any]:
    try:
        normalized = execution_bind.verify(root, binding, receipt)
    except execution_bind.BindingError as exc:
        raise BoundCompareError(str(exc)) from exc
    wrapper_sha = validate_reports(control, candidate, normalized)

    # The inherited comparator intentionally compares the shared environment and
    # grid. Its predecessor expected the identical 66-byte raw V2 entrypoint.
    # Both self-checking wrappers are byte-identical, so substituting their exact
    # verified hash preserves that theorem while this facade separately binds
    # the distinct filenames to the two distinct package closures.
    previous = compare.V2_ENTRY_SHA256
    compare.V2_ENTRY_SHA256 = wrapper_sha
    try:
        report = compare.compare(
            control, candidate, receipt, git_head=git_head
        )
    finally:
        compare.V2_ENTRY_SHA256 = previous
    report["execution_binding"] = normalized
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--binding", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = bound_compare(
            compare.strict_object(args.control),
            compare.strict_object(args.candidate),
            execution_bind.strict_object(args.receipt),
            execution_bind.strict_object(args.binding),
            root=args.root,
            git_head=args.head,
        )
    except (compare.CompareError, execution_bind.BindingError) as exc:
        report = {
            "schema_version": 1,
            "operation": execution_bind.OPERATION,
            "git_head": args.head,
            "verdict": "INVALID",
            "reason": str(exc),
            "exit_code": 2,
        }
    compare.atomic_write(
        args.output,
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
    )
    compare.atomic_write(args.markdown, compare.markdown(report))
    print(
        json.dumps(
            {
                "verdict": report["verdict"],
                "reason": report["reason"],
                "exit_code": report["exit_code"],
                "overall": report.get("overall"),
                "by_opponent": report.get("by_opponent"),
                "execution_binding": report.get("execution_binding"),
            },
            sort_keys=True,
            allow_nan=False,
        )
    )
    return int(report["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
