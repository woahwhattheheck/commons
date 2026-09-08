#!/usr/bin/env python3
"""Verify the exact current-TITAN responsive-opponent shard and its active variants."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
from typing import Any

ORDER = (
    "arlene",
    "apex",
    "arlene_sale_cadence",
    "apex_crop_demand",
    "arlene_labor_cadence",
)
EXPECTED = {
    "archive_sha256": "87d7b8bf7c4e9467f4b6b46887abe2eb03735c42453cdbf4f2cac12c5962acc7",
    "archive_bytes": 292007,
    "candidate_sha256": "a4ecdb513b48fa51877fe509597a84dd753dfe71d2d76a406ee3dc51475a9008",
    "arlene_sha256": "1dc166ae2bf0c56a44fac4482f469b8812968c4cb32459cb9860f5077897a7d4",
    "apex_sha256": "1f7cd5fb8a16585936d2562a3667f85bb6661688718ef58f73006de66148354a",
    "apex_so_sha256": "859857b1e6139026460fd50ee83bfe9022d4f73f01c40b7cca4aeea4d9af673c",
    "variant_sha256": "69df8c159d8f0b48377052d1637c49727ec551a8774f9f0215984fa89acd0746",
    "variant_git_blob": "374a23ffb3cf6cc1c67571df74fde9f84467e832",
    "engine_ref": "28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c",
    "seed": 9969137,
    "outcomes": {
        "arlene": (117312.0, 117036.0, 276.0, 0),
        "apex": (117585.0, 115447.0, 2138.0, 0),
        "arlene_sale_cadence": (104723.0, 14090.0, 90633.0, 122),
        "apex_crop_demand": (121763.0, 106976.0, 14787.0, 20),
        "arlene_labor_cadence": (181040.0, 0.0, 181040.0, 54),
    },
    "paired_effects": {
        "arlene_sale_cadence": (-12589.0, -102946.0, 90357.0),
        "apex_crop_demand": (4178.0, -8471.0, 12649.0),
        "arlene_labor_cadence": (63728.0, -117036.0, 180764.0),
    },
    "candidate_action_differences_vs_intact": {
        "arlene_sale_cadence": 184,
        "apex_crop_demand": 0,
        "arlene_labor_cadence": 192,
    },
    "trace_sha256": {
        ("arlene", 0): "d4d0aa9c14adda2c76815e74486f9673ec3ea22fc227277ae97be07b4a09fa68",
        ("arlene", 1): "9818f17685df48c7e15e7747c42829c7535d8b32e0ec9bd42a610726419036a3",
        ("apex", 0): "919fb5e9ee710d85b13901483692d741641006b832f9b68dd3c02be012aef5a7",
        ("apex", 1): "c4e8949e40d79cfbacc4d67091e08886779935121b9da2ee4ad9190d3cfd81c9",
        ("arlene_sale_cadence", 0): "ba90c71c17e966a501d93072ab655799c3f6425ee2b4271e45678dbb7b87fe09",
        ("arlene_sale_cadence", 1): "01aff3a8084098e964c847d619c7b8b501184f961f384446b97ef138c18b3b75",
        ("apex_crop_demand", 0): "85f138f4aedc65ce12f170b3c28d1ea42a4e077a28a269babc1948d26e947f06",
        ("apex_crop_demand", 1): "331d8ad6f6b40ed0aa1855ee86b30581240bf90603dd0dd75d9fddc6f3016e2e",
        ("arlene_labor_cadence", 0): "285b6754d046cd7462fd33ab6217d3bd22a9f921712414eee0d34cee080907dc",
        ("arlene_labor_cadence", 1): "ff287fd6e25c88376d006adbe341bb60044678ca347af0a71ec8f35535b3b640",
    },
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def digest(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def load_trace(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            try:
                rows.append(json.loads(line))
            except Exception as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSON: {exc}") from exc
    return rows


def normalized_actions(rows: list[dict[str, Any]], candidate_seat: int) -> tuple[list[Any], list[Any]]:
    return (
        [row["actions"][candidate_seat] for row in rows],
        [row["actions"][1 - candidate_seat] for row in rows],
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=Path("results/RESULTS.json"))
    parser.add_argument("--trace-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("results/VERIFICATION.json"))
    args = parser.parse_args()

    report = json.loads(args.results.read_text())
    require(report["archive"]["sha256"] == EXPECTED["archive_sha256"], "archive digest")
    require(report["archive"]["bytes"] == EXPECTED["archive_bytes"], "archive size")
    require(report["candidate"]["sha256"] == EXPECTED["candidate_sha256"], "candidate digest")
    require(report["opponent_sources"]["arlene"]["sha256"] == EXPECTED["arlene_sha256"], "Arlene digest")
    require(report["opponent_sources"]["apex"]["sha256"] == EXPECTED["apex_sha256"], "Apex digest")
    require(report["opponent_sources"]["apex"]["agent_so_sha256"] == EXPECTED["apex_so_sha256"], "Apex binary digest")
    require(report["variants"]["sha256"] == EXPECTED["variant_sha256"], "variant digest")
    require(report["variants"]["git_blob"] == EXPECTED["variant_git_blob"], "variant Git blob")
    require(report["engine_ref"] == EXPECTED["engine_ref"], "engine ref")
    require(report["seed"] == EXPECTED["seed"], "seed")
    require(report["summary"]["independent_seeds"] == 1, "independent seed count")
    require(report["summary"]["mirrored_seat_records"] == 10, "seat record count")
    require(report["summary"]["scheduled"] == report["summary"]["completed"] == 10, "completion count")
    require(report["summary"]["failed"] == 0, "failure count")
    require((report["summary"]["wins"], report["summary"]["ties"], report["summary"]["losses"]) == (10, 0, 0), "WTL")

    games = {(game["opponent"], int(game["candidate_seat"])): game for game in report["games"]}
    require(set(games) == {(name, seat) for name in ORDER for seat in (0, 1)}, "game cell set")
    traces: dict[tuple[str, int], list[dict[str, Any]]] = {}
    file_receipts: dict[str, Any] = {}
    action_digests: dict[str, Any] = {}
    mirror_exceptions: dict[str, Any] = {}

    for name in ORDER:
        expected_candidate, expected_rival, expected_margin, expected_changes = EXPECTED["outcomes"][name]
        for seat in (0, 1):
            game = games[(name, seat)]
            require(game["seed"] == EXPECTED["seed"], f"{name}/seat{seat}: seed")
            require(game["status"] == "complete" and game["failure"] is None, f"{name}/seat{seat}: completion")
            require(game["verdict"] == "W", f"{name}/seat{seat}: verdict")
            require(game["candidate_cash"] == expected_candidate, f"{name}/seat{seat}: candidate cash")
            require(game["rival_cash"] == expected_rival, f"{name}/seat{seat}: rival cash")
            require(game["margin"] == expected_margin, f"{name}/seat{seat}: margin")
            require(game["opponent_changed_turns"] == expected_changes, f"{name}/seat{seat}: changed turns")
            expected_scores = [expected_candidate, expected_rival]
            if seat == 1:
                expected_scores.reverse()
            require(game["scores"] == expected_scores, f"{name}/seat{seat}: score order")
            require(game["steps"] == 719, f"{name}/seat{seat}: transition count")
            relative = Path(game["action_trace"]["path"])
            trace_path = relative if relative.is_absolute() else args.trace_dir / relative.name
            require(trace_path.is_file(), f"missing {trace_path}")
            actual_hash = sha256(trace_path)
            require(actual_hash == EXPECTED["trace_sha256"][(name, seat)], f"{name}/seat{seat}: trace hash")
            rows = load_trace(trace_path)
            require(len(rows) == 719, f"{name}/seat{seat}: trace rows")
            require([row["step"] for row in rows] == list(range(719)), f"{name}/seat{seat}: ordered steps")
            traces[(name, seat)] = rows
            file_receipts[trace_path.name] = {"bytes": trace_path.stat().st_size, "sha256": actual_hash}

        left, right = traces[(name, 0)], traces[(name, 1)]
        left_candidate, left_opponent = normalized_actions(left, 0)
        right_candidate, right_opponent = normalized_actions(right, 1)
        require(left_candidate == right_candidate, f"{name}: candidate action mirror")
        opponent_differences = [index for index, pair in enumerate(zip(left_opponent, right_opponent, strict=True)) if pair[0] != pair[1]]
        if name in ("arlene", "apex", "apex_crop_demand"):
            require(opponent_differences == [], f"{name}: opponent action mirror")
        elif name == "arlene_sale_cadence":
            require(opponent_differences == [693], "sale-cadence mirror exception")
            require(left_opponent[693]["hands"][0] == ["COLLECT_FERTILIZER"], "sale seat0 exception action")
            require(right_opponent[693]["hands"][0] == ["DIG"], "sale seat1 exception action")
        else:
            require(opponent_differences == [676], "labor-cadence mirror exception")
            require(left_opponent[676]["farmer"] == ["HARVEST"], "labor seat0 exception action")
            require(right_opponent[676]["farmer"] == ["DIG"], "labor seat1 exception action")
        mirror_exceptions[name] = opponent_differences

        for left_row, right_row in zip(left, right, strict=True):
            require(left_row["bank_before"] == list(reversed(right_row["bank_before"])), f"{name}: bank-before mirror")
            require(left_row["bank_after"] == list(reversed(right_row["bank_after"])), f"{name}: bank-after mirror")
            require(left_row["status_after"] == list(reversed(right_row["status_after"])), f"{name}: status mirror")
            require(left_row["reward_after"] == list(reversed(right_row["reward_after"])), f"{name}: reward mirror")
        require(
            [row["bank"] for row in games[(name, 0)]["daily_bank"]]
            == [list(reversed(row["bank"])) for row in games[(name, 1)]["daily_bank"]],
            f"{name}: daily bank mirror",
        )
        action_digests[name] = {
            "candidate": digest(left_candidate),
            "opponent_seat0": digest(left_opponent),
            "opponent_seat1": digest(right_opponent),
        }

    action_difference_counts: dict[str, Any] = {}
    for variant_name, intact_name in (
        ("arlene_sale_cadence", "arlene"),
        ("apex_crop_demand", "apex"),
        ("arlene_labor_cadence", "arlene"),
    ):
        expected_candidate_delta, expected_rival_delta, expected_margin_delta = EXPECTED["paired_effects"][variant_name]
        counts = []
        for seat in (0, 1):
            variant_game = games[(variant_name, seat)]
            intact_game = games[(intact_name, seat)]
            require(variant_game["candidate_cash"] - intact_game["candidate_cash"] == expected_candidate_delta, f"{variant_name}/seat{seat}: candidate delta")
            require(variant_game["rival_cash"] - intact_game["rival_cash"] == expected_rival_delta, f"{variant_name}/seat{seat}: rival delta")
            require(variant_game["margin"] - intact_game["margin"] == expected_margin_delta, f"{variant_name}/seat{seat}: margin delta")
            variant_candidate, _ = normalized_actions(traces[(variant_name, seat)], seat)
            intact_candidate, _ = normalized_actions(traces[(intact_name, seat)], seat)
            count = sum(left != right for left, right in zip(variant_candidate, intact_candidate, strict=True))
            require(count == EXPECTED["candidate_action_differences_vs_intact"][variant_name], f"{variant_name}/seat{seat}: candidate action difference count")
            counts.append(count)
        require(counts[0] == counts[1], f"{variant_name}: paired candidate difference count")
        action_difference_counts[variant_name] = counts[0]

    interruption = report["interruption"]
    require(interruption["kind"] == "outer_execution_timeout", "interruption kind")
    require(interruption["completed_before_interruption"] == 4, "interruption completed count")
    require(interruption["policy_or_engine_failure_observed"] is False, "interruption failure classification")
    require(all(item["identical_decompressed_trace"] for item in interruption["intact_trace_reproduction"].values()), "interrupted intact trace reproduction")

    verification = {
        "schema_version": 1,
        "successful": True,
        "independent_seeds": 1,
        "mirrored_seat_records": 10,
        "seed": EXPECTED["seed"],
        "wtl": {"wins": 10, "ties": 0, "losses": 0},
        "checks": {
            "source_archive_variant_and_engine_pins": True,
            "ten_complete_games": True,
            "all_candidate_seat_mirrors": True,
            "all_economic_status_reward_mirrors": True,
            "active_variant_turn_counts": True,
            "paired_variant_cash_and_margin_effects": True,
            "crop_demand_candidate_actions_unchanged": True,
            "interrupted_intact_traces_reproduced": True,
        },
        "active_variant_turns": {
            name: EXPECTED["outcomes"][name][3]
            for name in ("arlene_sale_cadence", "apex_crop_demand", "arlene_labor_cadence")
        },
        "candidate_action_differences_vs_intact": action_difference_counts,
        "opponent_seat_mirror_exception_steps": mirror_exceptions,
        "normalized_action_digests": action_digests,
        "files": file_receipts,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(json.dumps(verification, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, args.output)
    print(json.dumps(verification, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
