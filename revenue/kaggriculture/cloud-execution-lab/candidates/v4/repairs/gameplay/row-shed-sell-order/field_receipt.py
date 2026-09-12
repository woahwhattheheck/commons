# SPDX-License-Identifier: Apache-2.0
"""Returned-action-bound reducer for the TITAN V4 row-shed field gate.

The row-shed transform runs before later SELL/funding finalizers. Its internal
diagnostic is therefore only a candidate witness. Promotion to a natural
reorder witness requires the exact ranked leading SELL block to survive in the
action ultimately returned to the engine.

This module is evidence-only. It never imports or mutates gameplay code.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
from typing import Any


def _plain_nonnegative_int(value: Any) -> bool:
    return type(value) is int and value >= 0


def _score_token(score: Any):
    if not isinstance(score, dict):
        return None
    index = score.get("original_index")
    item = score.get("item")
    requested = score.get("requested")
    impact = score.get("impact")
    if not _plain_nonnegative_int(index):
        return None
    if not isinstance(item, str) or not item:
        return None
    if not _plain_nonnegative_int(requested):
        return None
    if type(impact) is not int:
        return None
    return index, ("SELL", item, requested), impact


def classify_record(record: Any) -> dict[str, Any]:
    """Classify one telemetry record at the final returned-action boundary."""
    base = {
        "classification": "invalid_record",
        "internal_reorder": False,
        "returned_reorder": False,
    }
    if not isinstance(record, dict):
        return base

    diag = record.get("diagnostics")
    if not isinstance(diag, dict) or diag.get("status") != "applied":
        base["classification"] = "not_applied"
        return base

    scores = diag.get("scores")
    if not isinstance(scores, list) or len(scores) < 2:
        base["classification"] = "invalid_scores"
        return base

    parsed = [_score_token(score) for score in scores]
    if any(value is None for value in parsed):
        base["classification"] = "invalid_scores"
        return base

    indices = [value[0] for value in parsed]
    if indices != list(range(len(parsed))):
        base["classification"] = "invalid_original_indices"
        return base

    original_tokens = [value[1] for value in parsed]
    if len(set(original_tokens)) != len(original_tokens):
        # Diagnostics do not carry a row identity stronger than verb/item/qty.
        # A duplicate signature could be swapped without being observable here.
        base["classification"] = "ambiguous_duplicate_sell_signature"
        return base

    ranked = sorted(parsed, key=lambda value: value[2], reverse=True)
    ranked_indices = [value[0] for value in ranked]
    ranked_tokens = [value[1] for value in ranked]
    base.update(
        original_order=indices,
        ranked_order=ranked_indices,
        expected_ranked_prefix=[list(token) for token in ranked_tokens],
    )
    if ranked_indices == indices:
        base["classification"] = "identity_rank"
        return base

    base["internal_reorder"] = True
    returned = record.get("returned_market")
    if not isinstance(returned, list) or len(returned) < len(ranked_tokens):
        base["classification"] = "returned_market_missing_or_short"
        return base

    final_prefix = []
    for row in returned[: len(ranked_tokens)]:
        if not isinstance(row, list) or len(row) != 3:
            base["classification"] = "returned_prefix_malformed_or_extended"
            return base
        verb, item, requested = row
        if (verb != "SELL" or not isinstance(item, str) or not item
                or not _plain_nonnegative_int(requested)):
            base["classification"] = "returned_prefix_not_exact_sell"
            return base
        final_prefix.append((verb, item, requested))

    base["returned_prefix"] = [list(token) for token in final_prefix]
    if final_prefix != ranked_tokens:
        base["classification"] = "internal_reorder_not_returned"
        return base

    base["classification"] = "returned_reorder_witness"
    base["returned_reorder"] = True
    return base


def reduce_records(records: Any) -> dict[str, Any]:
    if not isinstance(records, list):
        raise ValueError("telemetry records must be a list")

    applied = 0
    internal = 0
    returned = []
    blocked: dict[str, int] = {}
    for record in records:
        if isinstance(record, dict):
            diag = record.get("diagnostics")
            if isinstance(diag, dict) and diag.get("status") == "applied":
                applied += 1

        result = classify_record(record)
        if result["internal_reorder"]:
            internal += 1
        if result["returned_reorder"]:
            returned.append({
                "step": record.get("step") if isinstance(record, dict) else None,
                "player": record.get("player") if isinstance(record, dict) else None,
                **result,
            })
        elif result["classification"] not in ("not_applied", "identity_rank"):
            reason = result["classification"]
            blocked[reason] = blocked.get(reason, 0) + 1

    return {
        "applied_callbacks": applied,
        "internal_reorder_callbacks": internal,
        "returned_reorder_callbacks": len(returned),
        "returned_reorder_witness": bool(returned),
        "returned_reorder_witnesses": returned,
        "blocked_callback_counts": dict(sorted(blocked.items())),
    }


def _load_jsonl(path: Path) -> list[Any]:
    if not path.is_file():
        return []
    records = []
    for number, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as error:
            raise ValueError(f"invalid telemetry JSON on line {number}: {error}") from error
    return records


def build_receipt(field_receipt: Any, records: list[Any]) -> dict[str, Any]:
    if not isinstance(field_receipt, dict):
        raise ValueError("field receipt must be an object")

    reduced = reduce_records(records)
    receipt = deepcopy(field_receipt)
    old_verdict = receipt.get("verdict")
    old_reorder_callbacks = receipt.get("natural_reorder_callbacks")
    old_reorder_witness = receipt.get("natural_reorder_witness")

    receipt["schema"] = "titan-v4-row-shed-postimage-field/v2-returned-action-bound"
    receipt["returned_action_gate"] = {
        "required": True,
        "binding": "exact-leading-sell-prefix",
        "duplicate_sell_signature_policy": "hold",
        "old_unbound_verdict": old_verdict,
        "old_unbound_reorder_callbacks": old_reorder_callbacks,
        "old_unbound_reorder_witness": old_reorder_witness,
    }
    receipt["applied_callbacks"] = reduced["applied_callbacks"]
    receipt["internal_reorder_callbacks"] = reduced["internal_reorder_callbacks"]
    receipt["natural_reorder_callbacks"] = reduced["returned_reorder_callbacks"]
    receipt["natural_reorder_witness"] = reduced["returned_reorder_witness"]
    receipt["reorder_witnesses"] = reduced["returned_reorder_witnesses"][:20]
    receipt["returned_action_blocked_callback_counts"] = reduced["blocked_callback_counts"]

    # Preserve the v1 field economics as evidence, never as promotion authority.
    receipt["economics_are_promotion_authority"] = False
    receipt["production_activated"] = False
    receipt["promotion_authorized"] = False

    if reduced["returned_reorder_witness"]:
        receipt["verdict"] = "NATURAL_REORDER_WITNESS_RETURNED_ACTION_BOUND"
    elif reduced["applied_callbacks"]:
        receipt["verdict"] = "NATURAL_ENGAGEMENT_NO_RETURNED_REORDER_IN_PANEL"
    else:
        receipt["verdict"] = "HOLD_NO_NATURAL_ENGAGEMENT_IN_PANEL"
    return receipt


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--telemetry", type=Path, required=True)
    parser.add_argument("--field-receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    field = json.loads(args.field_receipt.read_text())
    records = _load_jsonl(args.telemetry)
    receipt = build_receipt(field, records)
    args.output.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n")
    print(json.dumps({
        "verdict": receipt["verdict"],
        "applied_callbacks": receipt["applied_callbacks"],
        "internal_reorder_callbacks": receipt["internal_reorder_callbacks"],
        "natural_reorder_callbacks": receipt["natural_reorder_callbacks"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
