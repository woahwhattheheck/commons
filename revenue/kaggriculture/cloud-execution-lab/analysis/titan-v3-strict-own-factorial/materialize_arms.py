#!/usr/bin/env python3
"""Fail-closed materializer for the TITAN V3 strict×own 2×2 factor matrix.

The materializer deliberately patches the repository sources consumed by
``build_integrated.source_files()``. It never patches the generated archive or
its manifest. Each replacement must match exactly once, and every touched file
is fingerprinted before and after mutation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

ARM_FEATURES: dict[str, tuple[str, ...]] = {
    "incumbent": (),
    "strict-only": ("strict_dominance",),
    "own-only": ("own_value",),
    "combined": ("strict_dominance", "own_value"),
}

PRESSURE_PATH = Path(
    "revenue/kaggriculture/cloud-opponent-league/lark-responsive/pressure_priority.py"
)
RUNTIME_PATH = Path("revenue/kaggriculture/cloud-execution-lab/titan_runtime.py")
# build_integrated.py maps archive member selected_sell_core.py from this path.
PACKAGED_SELL_CORE_PATH = Path(
    "revenue/kaggriculture/cloud-execution-lab/"
    "reference/titan-current/latest/selected_sell_core.py"
)
TARGET_PATHS = (PRESSURE_PATH, RUNTIME_PATH, PACKAGED_SELL_CORE_PATH)


@dataclass(frozen=True)
class Replacement:
    path: Path
    label: str
    old: str
    new: str


STRICT_REPLACEMENTS = (
    Replacement(
        PRESSURE_PATH,
        "strict transform signature",
        (
            "def transform(action: dict, observation: Mapping,\n"
            "              configuration: Mapping | None = None, *, quote: PriceFunction,\n"
            "              rival_supply: Mapping[str, int] | None = None) -> dict:\n"
        ),
        (
            "def transform(action: dict, observation: Mapping,\n"
            "              configuration: Mapping | None = None, *, quote: PriceFunction,\n"
            "              rival_supply: Mapping[str, int] | None = None,\n"
            "              strict_dominance: bool = False) -> dict:\n"
        ),
    ),
    Replacement(
        PRESSURE_PATH,
        "strict transform documentation",
        (
            "    explicit zero means no rival flow. Present malformed values (including\n"
            "    ``None``) are barriers, so ambiguity cannot silently become proxy evidence.\n"
            "\n"
            "    Preserve all orders, quantities, duplicate lots, economic barriers,\n"
        ),
        (
            "    explicit zero means no rival flow. Present malformed values (including\n"
            "    ``None``) are barriers, so ambiguity cannot silently become proxy evidence.\n"
            "\n"
            "    ``strict_dominance`` performs a stable two-class partition. Positive\n"
            "    exposure may cross zero exposure, but positive lots retain parent order:\n"
            "    proxy magnitude cannot prove which exposed commodity is safe to demote.\n"
            "\n"
            "    Preserve all orders, quantities, duplicate lots, economic barriers,\n"
        ),
    ),
    Replacement(
        PRESSURE_PATH,
        "strict flag validation",
        (
            "    if not isinstance(action, dict) or not isinstance(action.get('market', []), list):\n"
            "        raise ValueError('parent policy must return an object with a market list')\n"
        ),
        (
            "    if not isinstance(strict_dominance, bool):\n"
            "        raise ValueError('strict_dominance must be boolean')\n"
            "    if not isinstance(action, dict) or not isinstance(action.get('market', []), list):\n"
            "        raise ValueError('parent policy must return an object with a market list')\n"
        ),
    ),
    Replacement(
        PRESSURE_PATH,
        "strict stable partition",
        (
            "        ranked = sorted(zip(orders[start:stop], scores[start:stop]), key=lambda p: -p[1])\n"
            "        orders[start:stop] = [order for order, _ in ranked]\n"
        ),
        (
            "        pairs = list(zip(orders[start:stop], scores[start:stop]))\n"
            "        if strict_dominance:\n"
            "            ranked = ([pair for pair in pairs if pair[1] > 0]\n"
            "                      + [pair for pair in pairs if pair[1] <= 0])\n"
            "        else:\n"
            "            ranked = sorted(pairs, key=lambda p: -p[1])\n"
            "        orders[start:stop] = [order for order, _ in ranked]\n"
        ),
    ),
    Replacement(
        RUNTIME_PATH,
        "canonical strict runtime call",
        "        result = pressure.transform(selected, obs, cfg, quote=mechanics.market_price)\n",
        (
            "        result = pressure.transform(\n"
            "            selected, obs, cfg, quote=mechanics.market_price,\n"
            "            strict_dominance=True)\n"
        ),
    ),
)

OWN_REPLACEMENTS = (
    Replacement(
        PACKAGED_SELL_CORE_PATH,
        "own-value score objective",
        "        return own_cash+carry-other_cash, own_cash,other_cash,remaining\n",
        "        return own_cash+carry, own_cash,other_cash,remaining\n",
    ),
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _replace_once(text: str, replacement: Replacement) -> str:
    count = text.count(replacement.old)
    if count != 1:
        raise ValueError(
            f"{replacement.label}: expected one source anchor in "
            f"{replacement.path}, found {count}"
        )
    if replacement.new in text:
        raise ValueError(
            f"{replacement.label}: replacement already present before application"
        )
    return text.replace(replacement.old, replacement.new, 1)


def _apply_group(root: Path, replacements: Iterable[Replacement]) -> list[dict]:
    grouped: dict[Path, list[Replacement]] = {}
    for replacement in replacements:
        grouped.setdefault(replacement.path, []).append(replacement)

    records: list[dict] = []
    for relative, file_replacements in grouped.items():
        path = root / relative
        before = path.read_bytes()
        text = before.decode("utf-8")
        labels: list[str] = []
        for replacement in file_replacements:
            text = _replace_once(text, replacement)
            labels.append(replacement.label)
        after = text.encode("utf-8")
        if after == before:
            raise AssertionError(f"{relative}: patch group made no byte change")
        path.write_bytes(after)
        records.append(
            {
                "path": relative.as_posix(),
                "labels": labels,
                "before_sha256": _sha256(before),
                "after_sha256": _sha256(after),
                "before_bytes": len(before),
                "after_bytes": len(after),
            }
        )
    return records


def verify_arm(root: Path, arm: str) -> None:
    if arm not in ARM_FEATURES:
        raise ValueError(f"unknown arm: {arm}")
    features = set(ARM_FEATURES[arm])
    pressure = (root / PRESSURE_PATH).read_text(encoding="utf-8")
    runtime = (root / RUNTIME_PATH).read_text(encoding="utf-8")
    own = (root / PACKAGED_SELL_CORE_PATH).read_text(encoding="utf-8")

    strict_markers = {
        "signature": "strict_dominance: bool = False",
        "partition": "[pair for pair in pairs if pair[1] > 0]",
        "runtime": "strict_dominance=True",
    }
    strict_expected = "strict_dominance" in features
    for label, marker in strict_markers.items():
        haystack = runtime if label == "runtime" else pressure
        count = haystack.count(marker)
        if count != int(strict_expected):
            raise AssertionError(
                f"{arm}: strict marker {label!r} count {count}; "
                f"expected {int(strict_expected)}"
            )

    old_ranking = (
        "ranked = sorted(zip(orders[start:stop], scores[start:stop]), "
        "key=lambda p: -p[1])"
    )
    old_call = "pressure.transform(selected, obs, cfg, quote=mechanics.market_price)"
    if pressure.count(old_ranking) != int(not strict_expected):
        raise AssertionError(f"{arm}: incumbent pressure ranking state is ambiguous")
    if runtime.count(old_call) != int(not strict_expected):
        raise AssertionError(f"{arm}: incumbent pressure call state is ambiguous")

    own_expected = "own_value" in features
    relative = "return own_cash+carry-other_cash, own_cash,other_cash,remaining"
    own_value = "return own_cash+carry, own_cash,other_cash,remaining"
    if own.count(relative) != int(not own_expected):
        raise AssertionError(f"{arm}: incumbent objective state is ambiguous")
    if own.count(own_value) != int(own_expected):
        raise AssertionError(f"{arm}: own-value objective state is ambiguous")

    for relative_path in TARGET_PATHS:
        compile(
            (root / relative_path).read_text(encoding="utf-8"),
            relative_path.as_posix(),
            "exec",
        )


def apply_arm(root: Path, arm: str) -> dict:
    root = root.resolve()
    if arm not in ARM_FEATURES:
        raise ValueError(f"unknown arm {arm!r}; choose from {sorted(ARM_FEATURES)}")
    for relative in TARGET_PATHS:
        path = root / relative
        if not path.is_file():
            raise FileNotFoundError(path)

    verify_arm(root, "incumbent")
    records: list[dict] = []
    features = set(ARM_FEATURES[arm])
    if "strict_dominance" in features:
        records.extend(_apply_group(root, STRICT_REPLACEMENTS))
    if "own_value" in features:
        records.extend(_apply_group(root, OWN_REPLACEMENTS))
    verify_arm(root, arm)

    return {
        "schema": "titan-v3-factorial-patch/v1",
        "arm": arm,
        "features": list(ARM_FEATURES[arm]),
        "touched_files": records,
        "packaged_sell_core_path": PACKAGED_SELL_CORE_PATH.as_posix(),
        "invariant": "patch repository sources consumed by build_integrated; never patch archive bytes",
    }


def _main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--arm", choices=sorted(ARM_FEATURES), required=True)
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    receipt = apply_arm(args.root, args.arm)
    encoded = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(encoded, encoding="utf-8")
    else:
        print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
