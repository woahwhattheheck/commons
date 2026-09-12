#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Authenticate the retained Apex V7 anti-clone market schedule.

Research/custody only: this module never chooses a TITAN action. It verifies the
exact independently retained public Apex source bytes and emits executable
source facts used by counter-ambush research. Any byte drift fails closed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

APEX_SHA256 = "1f7cd5fb8a16585936d2562a3667f85bb6661688718ef58f73006de66148354a"
APEX_BYTES = 24_996
SOURCE_ARTIFACT_ID = 10_030_763_484
SOURCE_ARTIFACT_RUN_ID = 34_155_238_754
SOURCE_ARTIFACT_SHA256 = "68f78694fa56976fa1476ffd1d1fb6b3bfd4935392dfd0023a170c7efcd35e62"
SOURCE_ARTIFACT_BYTES = 558_610
REGISTRY_PATH = "candidates/v4/research/reference-policy-bank/REFERENCE-POLICIES.json"
UPSTREAM_PATH = "cloud-frontier-policy/next-panel/vendor/apex/main.py"

# These are executable anchors, not comment-only claims. Exact SHA pinning makes
# them a human-readable theorem boundary rather than a substitute identity.
ANCHORS = {
    "clone_window": "if 2 <= step <= 10 and not state.get('is_clone', False):",
    "clone_threshold": "if opp_hands >= 3 and opp_structures >= 1:",
    "clone_latch": "state['is_clone'] = True",
    "clone_gate": "if is_clone:",
    "melon_249": "if step == 249 and melon_count >= 6 and len(market) < 10:",
    "melon_dedup": "not any(o[0] == 'SELL' and o[1] == 'MELON' for o in market)",
    "melon_order": "market.append(['SELL', 'MELON', min(melon_count, 12)])",
    "strawberry_381": "elif step == 381 and strawberry_count >= 6 and len(market) < 10:",
    "strawberry_403": "elif step == 403 and strawberry_count >= 6 and len(market) < 10:",
    "strawberry_499_501": "elif 499 <= step <= 501 and strawberry_count >= 8 and len(market) < 10:",
    "strawberry_order": "market.append(['SELL', 'STRAWBERRY', min(strawberry_count, 8)])",
    "fertilizer_522": "elif step == 522 and fert >= 18 and len(market) < 10:",
    "fertilizer_dedup": "not any(o[0] == 'SELL' and o[1] == 'FERTILIZER' for o in market)",
    "fertilizer_order": "market.append(['SELL', 'FERTILIZER', min(fert - 16, 4)])",
    "market_capacity": "len(market) < 10",
    "strawberry_dedup": "not any(o[0] == 'SELL' and o[1] == 'STRAWBERRY' for o in market)",
}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _line_receipts(text: str) -> dict[str, int]:
    lines = text.splitlines()
    out: dict[str, int] = {}
    missing: list[str] = []
    for name, needle in ANCHORS.items():
        hits = [i for i, line in enumerate(lines, 1) if needle in line]
        if not hits:
            missing.append(name)
        else:
            out[name] = hits[0]
    if missing:
        raise RuntimeError(f"apex executable contract drift: missing anchors {missing}")
    return out


def _schedule() -> dict[str, Any]:
    return {
        "clone_gate": {
            "observation_window_steps_inclusive": [2, 10],
            "opponent_hands_gte": 3,
            "opponent_animal_structures_gte": 1,
            "latched_true_for_episode": True,
        },
        "anti_clone_market_rows": [
            {
                "product": "MELON",
                "apex_steps_inclusive": [249, 249],
                "commented_clone_dump_step": 250,
                "minimum_private_stock": 6,
                "max_sell_units": 12,
                "market_rows_must_be_lt": 10,
                "deduplicates_same_product_sell": True,
            },
            {
                "product": "STRAWBERRY",
                "apex_steps_inclusive": [381, 381],
                "commented_clone_dump_step": 382,
                "minimum_private_stock": 6,
                "max_sell_units": 8,
                "market_rows_must_be_lt": 10,
                "deduplicates_same_product_sell": True,
            },
            {
                "product": "STRAWBERRY",
                "apex_steps_inclusive": [403, 403],
                "commented_clone_dump_step": 404,
                "minimum_private_stock": 6,
                "max_sell_units": 8,
                "market_rows_must_be_lt": 10,
                "deduplicates_same_product_sell": True,
            },
            {
                "product": "STRAWBERRY",
                "apex_steps_inclusive": [499, 501],
                "commented_clone_wave_step": 503,
                "minimum_private_stock": 8,
                "max_sell_units": 8,
                "market_rows_must_be_lt": 10,
                "deduplicates_same_product_sell": True,
            },
            {
                "product": "FERTILIZER",
                "apex_steps_inclusive": [522, 522],
                "commented_clone_dump_step": 523,
                "minimum_private_stock": 18,
                "sell_units_expression": "min(fert - 16, 4)",
                "preserved_private_stock_floor": 16,
                "market_rows_must_be_lt": 10,
                "deduplicates_same_product_sell": True,
            },
        ],
        "source_corrections": [
            "The step-522 comment says Fertilizer/Wheat dump, but the executable anti-clone branch appends only a FERTILIZER SELL row."
        ],
    }


def verify_apex_source(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    actual_sha = _sha256(data)
    if len(data) != APEX_BYTES or actual_sha != APEX_SHA256:
        raise RuntimeError(
            "apex source drift: "
            f"expected bytes={APEX_BYTES} sha256={APEX_SHA256}, "
            f"got bytes={len(data)} sha256={actual_sha}"
        )
    text = data.decode("utf-8")
    compile(text, str(path), "exec")
    lines = _line_receipts(text)
    return {
        "schema": "titan.v4.apex-source-custody.v1",
        "authenticated": True,
        "decision_authority": False,
        "runtime_activation": False,
        "source": {
            "path": UPSTREAM_PATH,
            "bytes": len(data),
            "sha256": actual_sha,
            "registry_path": REGISTRY_PATH,
        },
        "retained_artifact": {
            "artifact_id": SOURCE_ARTIFACT_ID,
            "workflow_run_id": SOURCE_ARTIFACT_RUN_ID,
            "zip_bytes": SOURCE_ARTIFACT_BYTES,
            "zip_sha256": SOURCE_ARTIFACT_SHA256,
        },
        "executable_anchor_lines": lines,
        "source_facts": _schedule(),
        "counter_ambush_implication": {
            "authenticated_apex_strawberry_front_run_steps": [381, 403, 499, 500, 501],
            "candidate_preemption_steps_for_first_two_rows": [380, 402],
            "field_economics_still_required": True,
            "promotion_bar": "terminal margin; source authentication alone is not a policy promotion",
        },
    }


def verify_artifact_zip(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    actual = _sha256(data)
    if len(data) != SOURCE_ARTIFACT_BYTES or actual != SOURCE_ARTIFACT_SHA256:
        raise RuntimeError(
            "source artifact drift: "
            f"expected bytes={SOURCE_ARTIFACT_BYTES} sha256={SOURCE_ARTIFACT_SHA256}, "
            f"got bytes={len(data)} sha256={actual}"
        )
    return {"artifact_zip_authenticated": True, "zip_bytes": len(data), "zip_sha256": actual}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("apex_source", type=Path)
    parser.add_argument("--artifact-zip", type=Path)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    receipt = verify_apex_source(args.apex_source)
    if args.artifact_zip is not None:
        receipt["retained_artifact"].update(verify_artifact_zip(args.artifact_zip))
    print(json.dumps(receipt, indent=2 if args.pretty else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
