# SPDX-License-Identifier: Apache-2.0
"""Executable theorem for the V2 future-rival scenario admission seam."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

BASE_SCENARIOS = ("no_rival", "observed_paired", "observed_later_order")
FUTURE_SCENARIOS = ("observed_next_turn", "observed_before_delayed_batch")
# A candidate that improves every V1 scenario but is vetoed only by V2's two
# copied future stress placements. Values are relative gains in scheduler units.
WITNESS = {
    "no_rival": 12.0,
    "observed_paired": 9.0,
    "observed_later_order": 4.0,
    "observed_next_turn": -1.0,
    "observed_before_delayed_batch": -3.0,
}


class SeamError(ValueError):
    pass


def admitted(names: Iterable[str], gains: dict[str, float]) -> bool:
    selected = tuple(names)
    if not selected or len(selected) != len(set(selected)):
        raise SeamError("scenario names must be unique and nonempty")
    if set(selected) - set(gains):
        raise SeamError("scenario gain is missing")
    return min(float(gains[name]) for name in selected) > 0.0


def report() -> dict[str, object]:
    v1 = admitted(BASE_SCENARIOS, WITNESS)
    v2 = admitted((*BASE_SCENARIOS, *FUTURE_SCENARIOS), WITNESS)
    if not v1 or v2:
        raise SeamError("predecessor-discriminating witness no longer discriminates")
    return {
        "schema_version": 1,
        "claim": "mechanism_reachability_not_game_strength",
        "base_scenarios": list(BASE_SCENARIOS),
        "future_scenarios": list(FUTURE_SCENARIOS),
        "relative_gain_witness": WITNESS,
        "three_scenario_admitted": v1,
        "five_scenario_admitted": v2,
        "discriminator": "future_scenarios_alone_reverse_strict_positive_admission",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    value = report()
    payload = json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8", newline="\n")
    print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
