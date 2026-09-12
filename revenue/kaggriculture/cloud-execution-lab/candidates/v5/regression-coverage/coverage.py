# SPDX-License-Identifier: Apache-2.0
"""Verify the submitted V3.1 -> V4 regression-coverage ledger.

Evidence-only.  This checker authenticates historical Git objects and refuses a
ledger that leaves a changed score-facing symbol unnamed, assigns more than one
primary carrier, or mistakes a repository source ref for submitted-package
execution authority.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[5]
LEDGER_PATH = HERE / "COVERAGE.json"
ALLOWED = {
    "NO_CAUSAL_DELTA",
    "ACTIVE_CAUSAL_LANE",
    "DISPROVEN_NONCAUSAL",
    "SOURCE_REF_NOT_PACKAGE_AUTHORITY",
    "DECOMPOSITION_OWNED",
}


class CoverageError(RuntimeError):
    pass


def git_show(ref: str, path: str) -> bytes:
    proc = subprocess.run(
        ["git", "-C", str(REPO), "show", f"{ref}:{path}"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return proc.stdout


def git_blob_sha1(raw: bytes) -> str:
    return hashlib.sha1(f"blob {len(raw)}\0".encode("ascii") + raw).hexdigest()


def _fail(message: str) -> None:
    raise CoverageError(message)


def _symbol_map(raw: bytes) -> tuple[dict[str, str], str, dict[str, str]]:
    text = raw.decode("utf-8")
    tree = ast.parse(text)
    symbols: dict[str, str] = {}
    class_shells: dict[str, str] = {}
    module_nodes: list[ast.AST] = []

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            symbols[node.name] = ast.get_source_segment(text, node) or ""
            continue
        if isinstance(node, ast.ClassDef):
            non_methods: list[ast.AST] = []
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    key = f"{node.name}.{child.name}"
                    symbols[key] = ast.get_source_segment(text, child) or ""
                else:
                    non_methods.append(child)
            shell = ast.ClassDef(
                name=node.name,
                bases=node.bases,
                keywords=node.keywords,
                body=non_methods,
                decorator_list=node.decorator_list,
                type_params=getattr(node, "type_params", []),
            )
            class_shells[node.name] = ast.dump(shell, include_attributes=False)
            continue
        module_nodes.append(node)
    module_shell = ast.dump(ast.Module(body=module_nodes, type_ignores=[]), include_attributes=False)
    return symbols, module_shell, class_shells


def changed_symbols(before: bytes, after: bytes) -> set[str]:
    a, module_a, classes_a = _symbol_map(before)
    b, module_b, classes_b = _symbol_map(after)
    changed = {key for key in set(a) | set(b) if a.get(key) != b.get(key)}
    if module_a != module_b:
        changed.add("__module__")
    for name in set(classes_a) | set(classes_b):
        if classes_a.get(name) != classes_b.get(name):
            changed.add(f"{name}.__class__")
    return changed


def _validate_carrier(row: dict[str, Any]) -> None:
    classification = row["classification"]
    primary = row.get("primary_carrier")
    if classification == "ACTIVE_CAUSAL_LANE":
        if not isinstance(primary, dict) or set(primary) != {"pr", "lane"}:
            _fail(f"{row['id']}: active lane requires exactly one primary_carrier {{pr,lane}}")
        if not isinstance(primary["pr"], int) or primary["pr"] <= 0:
            _fail(f"{row['id']}: invalid carrier PR")
    elif primary is not None:
        _fail(f"{row['id']}: only ACTIVE_CAUSAL_LANE may have primary_carrier")
    if classification == "DISPROVEN_NONCAUSAL" and not row.get("evidence_reason"):
        _fail(f"{row['id']}: disproven row requires evidence_reason")
    if classification == "SOURCE_REF_NOT_PACKAGE_AUTHORITY" and not row.get("package_authority_row"):
        _fail(f"{row['id']}: source-ref trap requires package_authority_row")


def verify(ledger: dict[str, Any]) -> dict[str, Any]:
    if ledger.get("schema") != "titan-v5-v31-v4-regression-coverage/v1":
        _fail("unexpected ledger schema")
    rows = ledger.get("rows")
    if not isinstance(rows, list) or not rows:
        _fail("ledger rows must be a non-empty list")
    ids = [row.get("id") for row in rows]
    if any(not isinstance(value, str) or not value for value in ids) or len(set(ids)) != len(ids):
        _fail("row ids must be unique non-empty strings")
    rows_by_id = {row["id"]: row for row in rows}

    verified: list[dict[str, Any]] = []
    for row in rows:
        classification = row.get("classification")
        if classification not in ALLOWED:
            _fail(f"{row['id']}: unknown classification {classification!r}")
        _validate_carrier(row)
        if classification == "SOURCE_REF_NOT_PACKAGE_AUTHORITY":
            target = row["package_authority_row"]
            if target not in rows_by_id:
                _fail(f"{row['id']}: package authority row {target!r} is missing")

        path = row["path"]
        left = row["left"]
        right = row["right"]
        left_raw = git_show(left["ref"], path)
        right_raw = git_show(right["ref"], path)
        left_blob = git_blob_sha1(left_raw)
        right_blob = git_blob_sha1(right_raw)
        if left_blob != left["blob"]:
            _fail(f"{row['id']}: left blob drift {left_blob} != {left['blob']}")
        if right_blob != right["blob"]:
            _fail(f"{row['id']}: right blob drift {right_blob} != {right['blob']}")
        equal = left_blob == right_blob
        if classification == "NO_CAUSAL_DELTA" and not equal:
            _fail(f"{row['id']}: NO_CAUSAL_DELTA but blobs differ")
        if classification in {"ACTIVE_CAUSAL_LANE", "DISPROVEN_NONCAUSAL", "SOURCE_REF_NOT_PACKAGE_AUTHORITY", "DECOMPOSITION_OWNED"} and equal:
            _fail(f"{row['id']}: changed classification but blobs are identical")
        verified.append({"id": row["id"], "equal": equal, "left_blob": left_blob, "right_blob": right_blob})

    config = ledger["config_delta"]
    left_cfg = json.loads(git_show(config["left_ref"], config["path"]))
    right_cfg = json.loads(git_show(config["right_ref"], config["path"]))
    added = {key: right_cfg[key] for key in right_cfg.keys() - left_cfg.keys()}
    removed = {key: left_cfg[key] for key in left_cfg.keys() - right_cfg.keys()}
    changed = {key: [left_cfg[key], right_cfg[key]] for key in left_cfg.keys() & right_cfg.keys() if left_cfg[key] != right_cfg[key]}
    if added != config["expected_added"] or removed or changed:
        _fail(f"config delta drift: added={added!r} removed={removed!r} changed={changed!r}")

    decomposition_reports: list[dict[str, Any]] = []
    for item in ledger.get("decompositions", []):
        before = git_show(item["left_ref"], item["path"])
        after = git_show(item["right_ref"], item["path"])
        actual = changed_symbols(before, after)
        declared = set(item["semantic_units"])
        missing = sorted(actual - declared)
        stale = sorted(declared - actual)
        if missing or stale:
            _fail(
                f"{item['id']}: semantic decomposition mismatch; "
                f"MISSING={missing!r} STALE={stale!r} ACTUAL={sorted(actual)!r}"
            )
        for symbol, owner in item["semantic_units"].items():
            if not isinstance(owner, dict) or owner.get("status") not in {"ACTIVE_CAUSAL_LANE", "DISPROVEN_NONCAUSAL"}:
                _fail(f"{item['id']}:{symbol}: semantic unit needs active/disproven owner")
            if owner["status"] == "ACTIVE_CAUSAL_LANE":
                carrier = owner.get("primary_carrier")
                if not isinstance(carrier, dict) or set(carrier) != {"pr", "lane"}:
                    _fail(f"{item['id']}:{symbol}: active semantic unit needs one primary carrier")
            elif not owner.get("evidence_reason"):
                _fail(f"{item['id']}:{symbol}: disproven semantic unit needs evidence_reason")
        decomposition_reports.append({"id": item["id"], "symbols": sorted(actual)})

    return {
        "schema": ledger["schema"],
        "verified_rows": verified,
        "config_added": added,
        "decompositions": decomposition_reports,
        "unknown_rows": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", type=Path, default=LEDGER_PATH)
    args = parser.parse_args()
    ledger = json.loads(args.ledger.read_text(encoding="utf-8"))
    report = verify(ledger)
    print(json.dumps(report, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
