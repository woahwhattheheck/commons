#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Fail-closed current-V4 TOWNPROCURE source/subsumption audit.

This module does not alter an action. It asks whether current production exposes a
WHEAT purchase that can lawfully be moved earlier across deterministic town demand
while preserving existing source constraints.

The answer is COLD only when (a) the complete authenticated Arlene route bank has no
authored BUY_PRODUCT WHEAT row and (b) the only current dynamic constructor is the
annual-crop input repair, whose exact source already retries every callback from its
first lawful due point and reconciles the previous receipt before that retry.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

import current_wheat_buy_census

SCHEMA = "titan.v4.market-baseline.townprocure-current-subsumption.v1"
PINS = {
    "crop_release.py": "dd318e5bbe6245913c3dcb8c07d0752fd1ebd735",
    "spatial_tempo.py": "edbc423023479dbe2e78131495334384a87b607f",
    "titan_runtime.py": "6d9720f4aa1e6b46e92ee5183897074d8e9ea5a0",
    "TITAN-CONFIG.json": "3a3bef83899d3010fad623b628d9e95d9978111b",
    "town_wheat_timing.py": "abdbdc74ddc2be60cc46ae53b069998fdb3bff3b",
    "TOWN-WHEAT-TIMING.json": "7678df8a763addb00e61eb3adff5a1dd219f2dde",
}
ENGINE_BLOB = "3c202c7ee921da239356789e266b694635103fc4"
ARLENE_BLOB = "bdb9cf58148a3c7961c085f4902759537decabf6"
DUE_STEP = 455
REPAIR_UNITS = 3


class AuditError(RuntimeError):
    pass


def _lab_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _git_blob(path: Path, cwd: Path) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(path)], cwd=cwd, text=True
    ).strip()


def _require(source: str, needles: tuple[str, ...], label: str) -> None:
    missing = [needle for needle in needles if needle not in source]
    if missing:
        raise AuditError(f"{label}: source anchors missing: {missing!r}")


def _first_multiple_at_or_after(step: int, interval: int) -> int:
    if type(step) is not int or step < 0:
        raise ValueError("step must be a nonnegative integer")
    if type(interval) is not int or interval <= 0:
        raise ValueError("interval must be a positive integer")
    return step + ((-step) % interval)


def audit() -> dict:
    lab = _lab_root()
    market_baseline = Path(__file__).resolve().parent
    paths = {
        "crop_release.py": lab / "crop_release.py",
        "spatial_tempo.py": lab / "spatial_tempo.py",
        "titan_runtime.py": lab / "titan_runtime.py",
        "TITAN-CONFIG.json": lab / "TITAN-CONFIG.json",
        "town_wheat_timing.py": market_baseline / "town_wheat_timing.py",
        "TOWN-WHEAT-TIMING.json": market_baseline / "TOWN-WHEAT-TIMING.json",
    }
    observed = {name: _git_blob(path, lab) for name, path in paths.items()}
    drift = {
        name: {"expected": PINS[name], "observed": blob}
        for name, blob in observed.items()
        if blob != PINS[name]
    }
    if drift:
        raise AuditError(f"current source drift: {drift}")

    cfg = json.loads(paths["TITAN-CONFIG.json"].read_text(encoding="utf-8"))
    if cfg.get("crop_release") is not True:
        raise AuditError("crop_release is not current-default true")

    crop = paths["crop_release.py"].read_text(encoding="utf-8")
    spatial = paths["spatial_tempo.py"].read_text(encoding="utf-8")
    runtime = paths["titan_runtime.py"].read_text(encoding="utf-8")
    oracle = paths["town_wheat_timing.py"].read_text(encoding="utf-8")
    oracle_receipt = json.loads(
        paths["TOWN-WHEAT-TIMING.json"].read_text(encoding="utf-8")
    )
    if oracle_receipt.get("engine_git_blob") != ENGINE_BLOB:
        raise AuditError("TOWNFLASH engine pin drifted")

    _require(
        crop,
        (
            "wheat_reserve_required=3, input_repair_remaining=3",
            "'deposit_step': 455",
            "now<intent['deposit_step'] or now>576",
            "intent.get('input_repair_pending') or intent.get('input_repair_unknown')",
            "['BUY_PRODUCT','WHEAT',n]",
            "'existing_wheat_purchase_needs_its_own_receipt'",
            "'repair_requires_a_free_nonconflicting_slot'",
            "'repair_or_eod_delivery_lacks_shared_room'",
            "'repair_or_boundary_capital_not_funded'",
            "input_repair_pending=pending",
            "p['input_repair_remaining']-=n",
        ),
        "crop_release",
    )
    _require(
        spatial,
        (
            "selected,self._crop_repair,repair_report=propose_input_repair(",
            "final_unit_guard_canceled_unbound_repair",
        ),
        "spatial_tempo",
    )
    _require(
        runtime,
        (
            "self.spatial.observe_market_receipt(obs,",
            "self.spatial.observe_crop_receipts(obs,",
            "output=self.spatial.crop_market(obs,output,self._selected_snapshot(obs,output),",
            "returned=self.spatial.guard_crop_returned(obs,returned,post)",
            "returned = self._feed_stock_selected(obs, cfg or {}, returned)",
            "returned = self._early_capital_selected(obs, cfg or {}, returned)",
        ),
        "titan_runtime",
    )
    # Use the observation in the normal act path (the one immediately following
    # observe_market_receipt), not the separate finish-path fallback occurrence.
    market_receipt_at = runtime.find("self.spatial.observe_market_receipt(obs,")
    observe_at = runtime.find("self.spatial.observe_crop_receipts(obs,", market_receipt_at)
    crop_market_at = runtime.find(
        "output=self.spatial.crop_market(obs,output,self._selected_snapshot(obs,output),",
        observe_at,
    )
    if (
        market_receipt_at < 0
        or observe_at < 0
        or crop_market_at < 0
        or not market_receipt_at < observe_at < crop_market_at
    ):
        raise AuditError("normal act path no longer reconciles crop receipts before crop_market")
    _require(
        oracle,
        (
            "Exact public town drain scheduled after MARKET on this callback.",
            '"buy_before_is_never_worse": savings >= 0',
        ),
        "town_wheat_timing",
    )

    route = current_wheat_buy_census.census(expected_vendor_blob=ARLENE_BLOB)
    route_rows = int(route["wheat_buy_row_count"])
    center_interval = cfg.get("townCenterSellInterval", 24)
    if type(center_interval) is not int or center_interval <= 0:
        raise AuditError("unsupported townCenterSellInterval")
    first_center = _first_multiple_at_or_after(DUE_STEP, center_interval)
    if first_center != 456:
        raise AuditError(f"unexpected first center callback after repair due: {first_center}")

    dynamic = {
        "constructor": "crop_release.propose_input_repair",
        "enabled": True,
        "obligation_units": REPAIR_UNITS,
        "obligation_field": "input_repair_remaining",
        "first_due_step": DUE_STEP,
        "first_post_due_town_center_step": first_center,
        "market_precedes_same_callback_town": True,
        "reconciles_prior_receipt_before_next_proposal": True,
        "retry_cadence": "every callback while due and receipt-known",
        "safe_actions": [
            "withhold existing WHEAT SELL",
            "append BUY_PRODUCT WHEAT into free raw slot",
        ],
        "preserved_blockers": [
            "existing WHEAT purchase has separate receipt ownership",
            "pending or ambiguous prior repair receipt",
            "final selected unit snapshot binding",
            "free raw market slot",
            "shared shed/EOD carry room",
            "source-pinned variable-price bound",
            "current plus boundary capital funded with zero future-sale credit",
        ],
    }

    if route_rows:
        decision = "ROUTE_WHEAT_BUYS_REQUIRE_SEPARATE_TIMING_GATE"
        reason = (
            "authenticated Arlene tape contains WHEAT purchases outside crop-repair ownership"
        )
    else:
        decision = "SUBSUMED_NO_LAWFUL_RETIME"
        reason = (
            "no authenticated tape-authored WHEAT buy exists; the only current dynamic "
            "constructor retries from the first lawful due callback, so moving an observed "
            "later repair earlier would have to cross an existing safety/receipt blocker"
        )

    result = {
        "schema": SCHEMA,
        "decision": decision,
        "reason": reason,
        "source_git_blobs": observed,
        "engine_git_blob": ENGINE_BLOB,
        "arlene_git_blob": route["vendor_git_blob"],
        "route_wheat_buy_row_count": route_rows,
        "route_wheat_buy_steps": route["wheat_buy_steps"],
        "route_wheat_buy_quantities": route["wheat_buy_quantities"],
        "dynamic_crop_repair": dynamic,
        "limits": [
            "source/subsumption proof only; no gameplay action is mutated",
            "does not claim a repair naturally engages in a sampled game",
            "does not relax crop input receipt, funding, capacity, row or feed-stock ownership",
            "any future source/blob drift invalidates this disposition",
        ],
    }
    canonical = json.dumps(
        result, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    result["result_sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return result


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pretty", action="store_true")
    args = ap.parse_args(argv)
    try:
        result = audit()
    except (
        AuditError,
        OSError,
        subprocess.CalledProcessError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        print(
            f"townprocure-current-subsumption: {exc}",
            file=__import__("sys").stderr,
        )
        return 2
    print(json.dumps(result, sort_keys=True, indent=2 if args.pretty else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
