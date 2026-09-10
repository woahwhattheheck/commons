#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Build the retained synthetic false-winner witness for the swarm gate."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from swarm_family_gate import analyze_family, make_registration_receipt

SOURCE_COMMIT = "2e2e7e52fd2d5c62117ac49c7f1eabb505078ffb"
ARM_IDS = ["synthetic-arm-a", "synthetic-arm-b", "synthetic-arm-c", "synthetic-arm-d"]
OPPONENTS = ["arlene", "v1"]
SEEDS = [2609101001, 2609101002, 2609101003, 2609101004, 2609101005]
SEATS = [0, 1]


def digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def build_registration() -> dict:
    return {
        "schema_version": 1,
        "family_id": "titan-v3-synthetic-four-arm-multiplicity-witness",
        "source_commit": SOURCE_COMMIT,
        "family_alpha": {"numerator": 1, "denominator": 20},
        "max_looks": 1,
        "execution": {
            "control_sha256": digest("synthetic control closure"),
            "engine_sha256": digest("synthetic official-engine identity"),
            "evaluator_sha256": digest("synthetic evaluator identity"),
            "loader_sha256": digest("synthetic loader identity"),
            "configuration_sha256": digest("synthetic configuration identity"),
            "opponents": OPPONENTS,
            "seeds": SEEDS,
            "seats": SEATS,
            "opponent_sha256": {
                opponent: digest(f"synthetic opponent {opponent}") for opponent in OPPONENTS
            },
        },
        "candidates": [
            {"arm_id": arm_id, "candidate_sha256": digest(f"synthetic closure {arm_id}")}
            for arm_id in ARM_IDS
        ],
    }


def build_panel(registration: dict) -> dict:
    registration_sha = make_registration_receipt(registration)["registration_sha256"]
    arms = []
    for arm_id in ARM_IDS:
        rows = []
        for opponent in OPPONENTS:
            for seed in SEEDS:
                for seat in SEATS:
                    cell = f"{opponent}:{seed}:{seat}"
                    rows.append(
                        {
                            "opponent": opponent,
                            "seed": seed,
                            "seat": seat,
                            "control_own": 100,
                            "control_rival": 90,
                            "candidate_own": 101,
                            "candidate_rival": 90,
                            "control_action_sha256": digest(f"synthetic control action {cell}"),
                            "candidate_action_sha256": digest(
                                f"synthetic candidate action {arm_id}:{cell}"
                            ),
                        }
                    )
        arms.append({"arm_id": arm_id, "rows": rows})
    return {
        "schema_version": 1,
        "family_id": registration["family_id"],
        "registration_sha256": registration_sha,
        "panel_id": "synthetic-four-arm-raw-5-of-5-positive",
        "look_index": 1,
        "arms": arms,
    }


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build(output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    registration = build_registration()
    registration_receipt = make_registration_receipt(registration)
    selection_receipt = analyze_family(registration, build_panel(registration))

    raw = {
        arm["arm_id"]: arm["seed_sign_tail"] for arm in selection_receipt["arms"]
    }
    adjusted = {
        arm["arm_id"]: arm["holm"]["adjusted_p"] for arm in selection_receipt["arms"]
    }
    if selection_receipt["decision"] != "MORE_EVIDENCE":
        raise RuntimeError("witness must not nominate an arm")
    if any((value["numerator"], value["denominator"]) != (1, 32) for value in raw.values()):
        raise RuntimeError("witness raw tails drifted")
    if any((value["numerator"], value["denominator"]) != (1, 8) for value in adjusted.values()):
        raise RuntimeError("witness adjusted tails drifted")

    summary = {
        "schema_version": 1,
        "kind": "synthetic-predecessor-killing-multiplicity-witness",
        "real_gameplay_evidence": False,
        "hypotheses": 4,
        "independent_seed_clusters_per_arm": 5,
        "raw_one_sided_sign_tail_each_arm": {"numerator": 1, "denominator": 32},
        "holm_adjusted_tail_each_arm": {"numerator": 1, "denominator": 8},
        "naive_individual_5_percent_calls": 4,
        "selection_safe_advance_calls": 0,
        "family_decision": selection_receipt["decision"],
        "registration_sha256": registration_receipt["registration_sha256"],
        "selection_receipt_sha256": selection_receipt["receipt_sha256"],
        "lesson": "screening four arms at uncorrected 5% cannot turn four raw 1/32 tails into a selected winner",
    }
    write_json(output_dir / "MULTIPLICITY-REGISTRATION-RECEIPT.json", registration_receipt)
    write_json(output_dir / "MULTIPLICITY-SELECTION-RECEIPT.json", selection_receipt)
    write_json(output_dir / "MULTIPLICITY-WITNESS-SUMMARY.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    print(json.dumps(build(args.output_dir), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
