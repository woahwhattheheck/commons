# SPDX-License-Identifier: Apache-2.0
"""Build one immutable production-v3 R04 route-matrix candidate."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from build_delivery import archive_bytes, digest, members
from build_production_recovery import (
    CANDIDATE_SHA,
    DELIVERY_SHA,
    V31_SHA,
    compose,
)
from route_matrix import (
    FINAL_PLAN_STEP,
    ROUTE_STEP,
    TERMINAL_PLAN,
    force_plan_at,
)

ROUTER = "r04_full_router.py"
ROUTER_SHA256 = "41ea55c5f20c43cd58c5099fbadb212de62ec95a95dfc2e6e1e19c3d4d55b39a"


def build(v31_archive, delivery_archive, plan_index, selection_step=ROUTE_STEP):
    """Compose exact production-v3, then force one authenticated route choice."""
    v31 = members(v31_archive, V31_SHA)
    delivery = members(delivery_archive, DELIVERY_SHA)
    overlay = Path(__file__).with_name("production_recovery_overlay.txt").read_bytes()
    files = compose(v31, delivery, overlay, "v3")
    if digest(archive_bytes(files)) != CANDIDATE_SHA:
        raise ValueError("production-v3 baseline identity drift")

    before = files[ROUTER]
    if digest(before) != ROUTER_SHA256:
        raise ValueError("production-v3 R04 router identity drift")
    after = force_plan_at(before, plan_index, selection_step)

    exact_terminal_control = (
        selection_step == FINAL_PLAN_STEP and plan_index == TERMINAL_PLAN
    )
    if (after == before) != exact_terminal_control:
        raise ValueError("route forcing identity contract violated")

    files = dict(files)
    files[ROUTER] = after
    return files, before, after


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v31", type=Path, required=True)
    parser.add_argument("--delivery", type=Path, required=True)
    parser.add_argument("--plan-index", type=int, required=True)
    parser.add_argument(
        "--selection-step",
        type=int,
        choices=(ROUTE_STEP, FINAL_PLAN_STEP),
        default=ROUTE_STEP,
        help="R04 plan-selection boundary to force (default: step 144)",
    )
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--tar", type=Path, required=True)
    args = parser.parse_args()
    receipt_path = args.out.parent / (args.out.name + "-manifest.json")
    if any(path.exists() for path in (args.out, args.tar, receipt_path)):
        parser.error("Use new output directory, archive and manifest paths")

    files, before, after = build(
        args.v31, args.delivery, args.plan_index, args.selection_step
    )
    packed = archive_bytes(files)
    args.out.mkdir(parents=True)
    for name, body in files.items():
        path = args.out / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
    args.tar.parent.mkdir(parents=True, exist_ok=True)
    with args.tar.open("xb") as stream:
        stream.write(packed)

    changed_members = [] if after == before else [ROUTER]
    receipt = {
        "schema": "titan-v5-route-matrix-build/v1",
        "baseline_candidate_archive_sha256": CANDIDATE_SHA,
        "v31_archive_sha256": V31_SHA,
        "delivery_archive_sha256": DELIVERY_SHA,
        "plan_index": args.plan_index,
        "selection_step": args.selection_step,
        "selection_kind": (
            "shop_pair" if args.selection_step == ROUTE_STEP else "terminal"
        ),
        "route_step": ROUTE_STEP,
        "final_plan_step": FINAL_PLAN_STEP,
        "terminal_plan": TERMINAL_PLAN,
        "changed_members": changed_members,
        "router_before_sha256": digest(before),
        "router_after_sha256": digest(after),
        "candidate_archive_sha256": digest(packed),
        "files": {name: digest(body) for name, body in sorted(files.items())},
        "kaggle_submission_hold": True,
    }
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "plan_index": args.plan_index,
        "selection_step": args.selection_step,
        "candidate_archive_sha256": digest(packed),
        "members": len(files),
    }))


if __name__ == "__main__":
    main()
