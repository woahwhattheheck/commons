# SPDX-License-Identifier: Apache-2.0
"""Fail-closed exact-source verifier for the stranded-HIRE payback successor."""
from __future__ import annotations

import ast
import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
SOURCE = HERE / "SOURCE.json"


def _fail(message: str) -> None:
    raise SystemExit(f"SOURCE CONTRACT FAILURE: {message}")


def _git(*args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", *args], cwd=ROOT, text=True, capture_output=True, check=False
    )
    if check and result.returncode:
        _fail(f"git {' '.join(args)}: {result.stderr.strip()}")
    return result.stdout.strip()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _regular(relative: str) -> Path:
    path = ROOT / relative
    if not path.is_file() or path.is_symlink():
        _fail(f"not a regular non-symlink file: {relative}")
    return path


def _load() -> dict[str, Any]:
    try:
        value = json.loads(SOURCE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _fail(f"invalid SOURCE.json: {exc}")
    if not isinstance(value, dict):
        _fail("SOURCE.json root must be an object")
    return value


def _one_function(tree: ast.Module, name: str) -> ast.FunctionDef:
    matches = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name]
    if len(matches) != 1:
        _fail(f"expected exactly one top-level {name}, found {len(matches)}")
    return matches[0]


def _calls(function: ast.FunctionDef) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(function):
        if not isinstance(node, ast.Call):
            continue
        target = node.func
        if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name):
            found.add(f"{target.value.id}.{target.attr}")
        elif isinstance(target, ast.Name):
            found.add(target.id)
    return found


def _structural_contract(data: dict[str, Any]) -> None:
    lab = ROOT / "revenue/kaggriculture/cloud-execution-lab"
    module_names = (
        "realized_hire_payback.py",
        "realized_hire_payback_common.py",
        "realized_hire_payback_market.py",
        "realized_hire_payback_replay.py",
        "realized_hire_payback_loop.py",
        "realized_hire_payback_finish.py",
    )
    module_paths = [lab / name for name in module_names]
    bridge_path = lab / "missing_hire_recovery.py"
    main_path = lab / "main.py"

    facade = ast.parse(module_paths[0].read_text(encoding="utf-8"), filename=str(module_paths[0]))
    function = _one_function(facade, "certify_realized_hire_payback")
    required_boundary_calls = {
        "m._spawn_hand",
        "m._decay_plants",
        "m._hire_cost",
        "replay_hired_lifetime",
        "finish_hire_payback",
    }
    missing = sorted(required_boundary_calls - _calls(function))
    if missing:
        _fail(f"certificate boundary lost calls: {missing}")

    source_text = "\n".join(path.read_text(encoding="utf-8") for path in module_paths)
    for token in (
        "m._apply_unit_action(",
        "m._spawn_hand(",
        "m._decay_plants(control_farm, now)",
        "m._hire_cost(",
        'getattr(m, "PRICE_FLOOR", 1)',
        'reason="step_sale_displacement"',
        'reason="per_product_sale_displacement"',
        '"rival_buy_can_raise_price"',
        "route_decision_checkpoint_in_horizon",
        "m.market_price(",
        'report.update(admit=True, reason="realized_payback_covers_hire")',
        "replay_hired_lifetime(ctx, report)",
        "finish_hire_payback(ctx, data, report)",
    ):
        if token not in source_text:
            _fail(f"certificate binding token missing: {token}")

    bridge_text = bridge_path.read_text(encoding="utf-8")
    for token in (
        "certify_payback",
        'payback.get("admit") is not True',
        'reason="inserted_prefix_and_payback_certified_hire"',
    ):
        if token not in bridge_text:
            _fail(f"bridge fail-closed token missing: {token}")

    main_text = main_path.read_text(encoding="utf-8")
    for token in (
        "from realized_hire_payback import certify_realized_hire_payback",
        "from scheduler import parent as route_parent, post_units",
        "certify_payback=certify_payback",
        "farm=farm",
        "private=private",
        "route=route",
        "market=obs['market']",
        "decision_steps=[row[0] for row in route_parent.DECISIONS]",
    ):
        if token not in main_text:
            _fail(f"entrypoint binding token missing: {token}")

    if data.get("promotion_authorized") is not False:
        _fail("promotion_authorized must be false")
    if data.get("hosted_leaderboard_claim") is not False:
        _fail("hosted_leaderboard_claim must be false")

def main() -> None:
    data = _load()
    parent = data.get("parent", {}).get("commit")
    if not isinstance(parent, str) or len(parent) != 40:
        _fail("invalid parent commit")
    head = _git("rev-parse", "HEAD")
    expected_head = os.environ.get("EXPECTED_HEAD")
    if expected_head and head != expected_head:
        _fail(f"event head mismatch: {head} != {expected_head}")
    ancestry = subprocess.run(
        ["git", "merge-base", "--is-ancestor", parent, head], cwd=ROOT, check=False
    )
    if ancestry.returncode:
        _fail(f"parent {parent} is not an ancestor of {head}")

    parent_blobs = data.get("parent_blobs")
    if not isinstance(parent_blobs, dict) or not parent_blobs:
        _fail("parent_blobs must be a nonempty object")
    for relative, expected in sorted(parent_blobs.items()):
        actual = _git("rev-parse", f"{parent}:{relative}")
        if actual != expected:
            _fail(f"parent blob drift for {relative}: {actual} != {expected}")

    allowed = data.get("allowed_paths")
    if not isinstance(allowed, list) or not allowed or len(allowed) != len(set(allowed)):
        _fail("allowed_paths must be a unique nonempty list")
    changed = set(filter(None, _git("diff", "--name-only", parent, head).splitlines()))
    if changed != set(allowed):
        _fail(
            "diff path mismatch: "
            f"missing={sorted(set(allowed) - changed)} "
            f"extra={sorted(changed - set(allowed))}"
        )

    current = data.get("current_sha256")
    if not isinstance(current, dict) or not current:
        _fail("current_sha256 must be a nonempty object")
    if set(current) - set(allowed):
        _fail("current_sha256 names a path outside allowed_paths")
    for relative, expected in sorted(current.items()):
        path = _regular(relative)
        actual = _sha256(path)
        if actual != expected:
            _fail(f"SHA-256 drift for {relative}: {actual} != {expected}")

    _structural_contract(data)
    print(json.dumps({
        "schema_version": 1,
        "claim_id": data.get("claim_id"),
        "parent": parent,
        "head": head,
        "changed_paths": sorted(changed),
        "verified_sha256": dict(sorted(current.items())),
        "promotion_authorized": False,
        "hosted_leaderboard_claim": False,
        "status": "source_contract_pass",
    }, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
