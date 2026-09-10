# SPDX-License-Identifier: Apache-2.0
"""Exact public-curve witness for the strict-pressure rounded plateau failure."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
from types import ModuleType
from typing import Any

from pressure_zero_exposure import stable_certified_partition
from materialize_pressure_certificate import git_blob_sha1


EXPECTED_MECHANICS_GIT_BLOB_SHA1 = "044a4f9c0a4a44dde10ada57563238bcaf82075d"
SCHEMA = "titan-v3-pressure-rounded-plateau-witness/v1"


def _load_mechanics(
    path: Path,
    *,
    expected_git_blob_sha1: str = EXPECTED_MECHANICS_GIT_BLOB_SHA1,
) -> tuple[ModuleType, bytes]:
    path = Path(path)
    try:
        info = path.lstat()
    except OSError as exc:
        raise ValueError("mechanics cannot be statted") from exc
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        raise ValueError("mechanics must be a regular non-symlink file")
    payload = path.read_bytes()
    actual = git_blob_sha1(payload)
    if actual != expected_git_blob_sha1:
        raise ValueError(
            f"mechanics git blob drift: expected {expected_git_blob_sha1}, got {actual}"
        )
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("mechanics must be UTF-8") from exc
    compile(text, str(path), "exec")
    name = f"_titan_pressure_mechanics_{actual}"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ValueError("mechanics import spec unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not callable(getattr(module, "market_price", None)):
        raise ValueError("mechanics lacks market_price")
    return module, payload


def build_witness(
    mechanics_path: Path,
    *,
    expected_git_blob_sha1: str = EXPECTED_MECHANICS_GIT_BLOB_SHA1,
) -> dict[str, Any]:
    """Reproduce the exact price plateau, false reorder, and repaired order."""

    mechanics, payload = _load_mechanics(
        mechanics_path,
        expected_git_blob_sha1=expected_git_blob_sha1,
    )
    quote = mechanics.market_price
    stock = 9999
    curves = {
        item: [quote(item, stock + offset, None) for offset in range(3)]
        for item in ("TOMATO", "MILK")
    }
    if curves != {"TOMATO": [60, 60, 57], "MILK": [169, 160, 158]}:
        raise ValueError(f"pinned public curve witness drifted: {curves!r}")

    parent = [["SELL", "TOMATO", 1], ["SELL", "MILK", 1]]
    market = {
        "prices": {item: values[0] for item, values in curves.items()},
        "inventory": {"TOMATO": stock, "MILK": stock},
        "params": None,
    }
    proxy_pressure = {
        item: float(values[0] - values[1])
        for item, values in curves.items()
    }
    proxy_candidate = sorted(
        parent,
        key=lambda row: -proxy_pressure[row[1]],
    )
    repaired, certificates = stable_certified_partition(
        parent,
        market,
        quote,
        2,
    )
    if [row[1] for row in proxy_candidate] != ["MILK", "TOMATO"]:
        raise ValueError("proxy predecessor no longer reorders")
    if repaired != parent:
        raise ValueError("bounded certificate failed to preserve parent order")

    # Official market orders execute in same-index lockstep.  Under the parent,
    # our TOMATO occupies slot 0 against the rival TOMATO lot.  Under the proxy
    # candidate, our MILK moves to slot 0 and our TOMATO is delayed to slot 1.
    parent_own = quote("TOMATO", 9999, None) + quote("MILK", 9999, None)
    parent_rival = quote("TOMATO", 10000, None) + quote("TOMATO", 10001, None)
    proxy_own = quote("MILK", 9999, None) + quote("TOMATO", 10001, None)
    proxy_rival = quote("TOMATO", 9999, None) + quote("TOMATO", 10000, None)
    parent_margin = parent_own - parent_rival
    proxy_margin = proxy_own - proxy_rival
    effect = {
        "own": proxy_own - parent_own,
        "rival": proxy_rival - parent_rival,
        "margin": proxy_margin - parent_margin,
    }
    if effect != {"own": -3, "rival": 3, "margin": -6}:
        raise ValueError(f"lockstep economic witness drifted: {effect!r}")

    witness = {
        "schema": SCHEMA,
        "mechanics_git_blob_sha1": git_blob_sha1(payload),
        "mechanics_sha256": hashlib.sha256(payload).hexdigest(),
        "public_inventory": stock,
        "curves": curves,
        "parent_order": [row[1] for row in parent],
        "proxy_pressure": proxy_pressure,
        "proxy_order": [row[1] for row in proxy_candidate],
        "certified_order": [row[1] for row in repaired],
        "certificates": [certificate.to_dict() for certificate in certificates],
        "parent": {
            "own": parent_own,
            "rival": parent_rival,
            "margin": parent_margin,
        },
        "proxy_candidate": {
            "own": proxy_own,
            "rival": proxy_rival,
            "margin": proxy_margin,
        },
        "proxy_effect": effect,
        "disposition": "PROXY_ZERO_UNSAFE_CERTIFIED_BOUND_PRESERVES_PARENT",
    }
    # Strict JSON is part of the retained evidence contract.
    json.dumps(witness, sort_keys=True, allow_nan=False)
    return witness


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mechanics", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    witness = build_witness(args.mechanics)
    output = args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(witness, sort_keys=True, indent=2, allow_nan=False) + "\n"
    temporary = output.with_name(f".{output.name}.{os.getpid()}.tmp")
    try:
        temporary.write_text(encoded, encoding="utf-8")
        os.replace(temporary, output)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
    if json.loads(output.read_text(encoding="utf-8")) != witness:
        raise ValueError("witness readback mismatch")
    print(json.dumps(witness, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
