# SPDX-License-Identifier: Apache-2.0
"""Exact-source carrier for deterministic town consumption in funding traces.

The current funding trace replays future market orders but omits the official
engine's public town-consumption stage.  This module materializes a minimal
patch against one byte-pinned ``frozen_selected.py`` source and can emit a
machine-readable receipt for integration.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, MutableMapping, Sequence

EXPECTED_SOURCE_BLOB_SHA1 = "fc7baf5c179818a55037f6a61d92984d81d1a21c"
EXPECTED_ENGINE_BLOB_SHA1 = "3c202c7ee921da239356789e266b694635103fc4"

_FUNCTION_ANCHOR = (
    "def _funding_trace(obs, config, farm, private, route, now, end, current_market,\n"
    "                   stress_units=0):"
)
_RETURN_ANCHOR = (
    "    return {'cash': int(f['money']), 'acquisitions': acquisitions,\n"
    "            'executed_sales': executed_sales}"
)

_HELPER_SOURCE = '''def _funding_apply_town_consumption(inventory, shops, config, step):
    """Apply the official public town stage after one projected market stage."""
    shop_interval=max(1,int(config.get('townShopSellInterval',4)))
    center_interval=max(1,int(config.get('townCenterSellInterval',24)))
    if step % shop_interval == 0:
        for shop_name in shops:
            products=m.SHOPS[shop_name]
            multiplier=2 if len(products)==1 else 1
            for item in products:
                inventory[item]-=multiplier
    if step % center_interval == 0:
        for item in m.PRODUCTS:
            if item!='FERTILIZER':
                inventory[item]-=1'''

_CALL_SOURCE = '''        _funding_apply_town_consumption(
            inventory, obs.get('town', {}).get('unlocked_shops', ()),
            config, t)
'''


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def git_blob_sha1(text: str) -> str:
    """Return Git's canonical SHA-1 object id for one UTF-8 text blob."""
    payload = text.encode("utf-8")
    header = f"blob {len(payload)}\0".encode("ascii")
    return hashlib.sha1(header + payload).hexdigest()


def apply_public_town_consumption(
    inventory: MutableMapping[str, int],
    shops: Sequence[str],
    config: Mapping[str, Any],
    step: int,
    *,
    shop_products: Mapping[str, Sequence[str]],
    products: Sequence[str],
) -> None:
    """Pure oracle equivalent to the injected helper and official engine stage."""
    shop_interval = max(1, int(config.get("townShopSellInterval", 4)))
    center_interval = max(1, int(config.get("townCenterSellInterval", 24)))
    if step % shop_interval == 0:
        for shop_name in shops:
            sold = shop_products[shop_name]
            multiplier = 2 if len(sold) == 1 else 1
            for item in sold:
                inventory[item] -= multiplier
    if step % center_interval == 0:
        for item in products:
            if item != "FERTILIZER":
                inventory[item] -= 1


def materialize(source: str, *, require_expected_source: bool = True) -> str:
    """Return a compiled source postimage or raise on any closure drift."""
    if not isinstance(source, str):
        raise TypeError("source must be text")
    source_blob = git_blob_sha1(source)
    if require_expected_source and source_blob != EXPECTED_SOURCE_BLOB_SHA1:
        raise ValueError(
            f"source drift: expected Git blob {EXPECTED_SOURCE_BLOB_SHA1}, "
            f"got {source_blob}"
        )
    if source.count(_FUNCTION_ANCHOR) != 1:
        raise ValueError("funding trace function anchor count is not exactly one")
    if source.count(_RETURN_ANCHOR) != 1:
        raise ValueError("funding trace return anchor count is not exactly one")
    if "def _funding_apply_town_consumption(" in source:
        raise ValueError("town-consumption helper already present")

    patched = source.replace(
        _FUNCTION_ANCHOR,
        _HELPER_SOURCE + "\n\n\n" + _FUNCTION_ANCHOR,
        1,
    )
    patched = patched.replace(_RETURN_ANCHOR, _CALL_SOURCE + _RETURN_ANCHOR, 1)
    if patched.count("def _funding_apply_town_consumption(") != 1:
        raise ValueError("helper insertion failed")
    if patched.count("        _funding_apply_town_consumption(\n") != 1:
        raise ValueError("funding-loop call insertion failed")
    compile(patched, "<frozen_selected-town-consumption>", "exec")
    return patched


def receipt(source: str, patched: str) -> dict[str, Any]:
    return {
        "schema": "titan-v3-funding-town-consumption/v1",
        "complete": True,
        "source_blob_sha1": git_blob_sha1(source),
        "expected_source_blob_sha1": EXPECTED_SOURCE_BLOB_SHA1,
        "source_sha256": sha256_text(source),
        "engine_blob_sha1": EXPECTED_ENGINE_BLOB_SHA1,
        "patched_source_sha256": sha256_text(patched),
        "helper_count": patched.count("def _funding_apply_town_consumption("),
        "call_count": patched.count("        _funding_apply_town_consumption(\n"),
        "official_stage_order": "unit_actions->market->town_consume->decay->day_close",
        "canonical_runtime_modified": False,
        "hosted_strength_claim": False,
        "release_selection_claim": False,
    }


def _main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    args = parser.parse_args()

    source = args.source.read_text(encoding="utf-8")
    patched = materialize(source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(patched, encoding="utf-8")
    data = receipt(source, patched)
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(
        json.dumps(data, sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(data, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
