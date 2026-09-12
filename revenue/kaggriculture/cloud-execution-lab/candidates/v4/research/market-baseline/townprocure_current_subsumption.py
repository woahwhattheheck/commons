#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Fail-closed current-V4 TOWNPROCURE source/subsumption audit.

This module does not alter an action. It asks whether current production exposes a
WHEAT purchase that can lawfully be moved earlier across deterministic town demand
while preserving existing source constraints.

The answer is COLD only when (a) the complete authenticated Arlene route bank has no
authored BUY_PRODUCT WHEAT row and (b) the exact enabled selected-action chain proves
that the annual-crop input repair is the only live dynamic WHEAT-buy constructor. That
repair already retries every callback from its first lawful due point and reconciles
the previous receipt before the next proposal.

All theorem inputs are single-read snapshots: Git object identity, JSON parsing, and
source-anchor analysis are derived from the same captured bytes. Pathnames are never
reopened after authentication.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import current_wheat_buy_census

SCHEMA = "titan.v4.market-baseline.townprocure-current-subsumption.v3"
PINS = {
    "main.py": "4a8cf7bcda1f0fea231a144692cb84a779a9e73e",
    "titan_runtime.py": "6d9720f4aa1e6b46e92ee5183897074d8e9ea5a0",
    "frozen_selected.py": "fc7baf5c179818a55037f6a61d92984d81d1a21c",
    "scheduler.py": "a483b24dd72b580d7d8811636b54d2d44f391575",
    "terminal_history_join.py": "f878320d293dbf08fda24dc66f1805702a6c763c",
    "redundant_hire.py": "9ded2a9b636793df0511103da802bd3f26dbbb94",
    "seed_budget.py": "eaa244ba05104535f9922a5f76d623a76c187096",
    "pressure_priority.py": "7261674962d10fc8bc6af5ff73ff9212c40f61ad",
    "operating_stock.py": "781aa90da0d85d0ba23c665e29d6087d182c085e",
    "early_capital.py": "1161859ac5af617eca65aec3f732b5c1396cad37",
    "spatial_tempo.py": "edbc423023479dbe2e78131495334384a87b607f",
    "crop_release.py": "dd318e5bbe6245913c3dcb8c07d0752fd1ebd735",
    "TITAN-CONFIG.json": "3a3bef83899d3010fad623b628d9e95d9978111b",
    "town_wheat_timing.py": "abdbdc74ddc2be60cc46ae53b069998fdb3bff3b",
    "TOWN-WHEAT-TIMING.json": "7678df8a763addb00e61eb3adff5a1dd219f2dde",
}
ENGINE_BLOB = "3c202c7ee921da239356789e266b694635103fc4"
ARLENE_BLOB = "bdb9cf58148a3c7961c085f4902759537decabf6"
DUE_STEP = 455
REPAIR_UNITS = 3

EXPECTED_FEATURES = {
    "consumer": "frozen",
    "seed": True,
    "funding": True,
    "terminal_route": False,
    "committed": True,
    "terminal_history": False,
    "redundant_hire": True,
    "fourth_quadrant": False,
    "market_pressure": True,
    "committed_seed_retry": False,
    "operating_stock": True,
    "idle_fertilizer": True,
    "crop_release": True,
    "early_capital": True,
}


class AuditError(RuntimeError):
    pass


def _lab_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _git_blob_bytes(data: bytes) -> str:
    if not isinstance(data, bytes):
        raise TypeError("Git blob input must be bytes")
    header = b"blob " + str(len(data)).encode("ascii") + b"\0"
    return hashlib.sha1(header + data).hexdigest()


def _read_snapshot(path: Path) -> bytes:
    """Read a theorem input exactly once."""
    return path.read_bytes()


def _capture_pinned_sources(paths: dict[str, Path]) -> tuple[dict[str, bytes], dict[str, str]]:
    snapshots: dict[str, bytes] = {}
    observed: dict[str, str] = {}
    for name, path in paths.items():
        data = _read_snapshot(path)
        snapshots[name] = data
        observed[name] = _git_blob_bytes(data)
    drift = {
        name: {"expected": PINS[name], "observed": blob}
        for name, blob in observed.items()
        if blob != PINS[name]
    }
    if drift:
        raise AuditError(f"current source drift: {drift}")
    return snapshots, observed


def _snapshot_text(snapshot: bytes, label: str) -> str:
    try:
        return snapshot.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise AuditError(f"{label}: authenticated bytes are not UTF-8") from exc


def _snapshot_json(snapshot: bytes, label: str):
    try:
        return json.loads(_snapshot_text(snapshot, label))
    except json.JSONDecodeError as exc:
        raise AuditError(f"{label}: authenticated bytes are not valid JSON: {exc}") from exc


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
    repo_revenue = lab.parents[1]
    market_baseline = Path(__file__).resolve().parent
    paths = {
        "main.py": lab / "main.py",
        "titan_runtime.py": lab / "titan_runtime.py",
        "frozen_selected.py": lab / "frozen_selected.py",
        "scheduler.py": lab / "scheduler.py",
        "terminal_history_join.py": lab / "terminal_history_join.py",
        "redundant_hire.py": lab / "reference" / "titan-current" / "redundant_hire.py",
        "seed_budget.py": lab / "reference" / "integrated-selected" / "alder" / "seed_budget.py",
        "pressure_priority.py": repo_revenue / "kaggriculture" / "cloud-opponent-league" / "lark-responsive" / "pressure_priority.py",
        "operating_stock.py": lab / "operating_stock.py",
        "early_capital.py": lab / "early_capital.py",
        "spatial_tempo.py": lab / "spatial_tempo.py",
        "crop_release.py": lab / "crop_release.py",
        "TITAN-CONFIG.json": lab / "TITAN-CONFIG.json",
        "town_wheat_timing.py": market_baseline / "town_wheat_timing.py",
        "TOWN-WHEAT-TIMING.json": market_baseline / "TOWN-WHEAT-TIMING.json",
    }
    snapshots, observed = _capture_pinned_sources(paths)

    # Every semantic read below comes from the immutable authenticated snapshots.
    cfg = _snapshot_json(snapshots["TITAN-CONFIG.json"], "TITAN-CONFIG.json")
    feature_drift = {
        key: {"expected": value, "observed": cfg.get(key)}
        for key, value in EXPECTED_FEATURES.items()
        if cfg.get(key) != value
    }
    if feature_drift:
        raise AuditError(f"enabled-feature surface drift: {feature_drift}")

    main = _snapshot_text(snapshots["main.py"], "main.py")
    runtime = _snapshot_text(snapshots["titan_runtime.py"], "titan_runtime.py")
    frozen = _snapshot_text(snapshots["frozen_selected.py"], "frozen_selected.py")
    scheduler = _snapshot_text(snapshots["scheduler.py"], "scheduler.py")
    history = _snapshot_text(snapshots["terminal_history_join.py"], "terminal_history_join.py")
    redundant = _snapshot_text(snapshots["redundant_hire.py"], "redundant_hire.py")
    seed_budget = _snapshot_text(snapshots["seed_budget.py"], "seed_budget.py")
    pressure = _snapshot_text(snapshots["pressure_priority.py"], "pressure_priority.py")
    operating = _snapshot_text(snapshots["operating_stock.py"], "operating_stock.py")
    early = _snapshot_text(snapshots["early_capital.py"], "early_capital.py")
    spatial = _snapshot_text(snapshots["spatial_tempo.py"], "spatial_tempo.py")
    crop = _snapshot_text(snapshots["crop_release.py"], "crop_release.py")
    oracle = _snapshot_text(snapshots["town_wheat_timing.py"], "town_wheat_timing.py")
    oracle_receipt = _snapshot_json(
        snapshots["TOWN-WHEAT-TIMING.json"], "TOWN-WHEAT-TIMING.json"
    )
    if oracle_receipt.get("engine_git_blob") != ENGINE_BLOB:
        raise AuditError("TOWNFLASH engine pin drifted")

    _require(
        main,
        (
            "features = Features(**feature_data)",
            "return super()._market_pressure_selected(obs, cfg, returned)",
            "output = instance.act(observation, cfg, entry_started=entry_started)",
        ),
        "main",
    )
    _require(
        runtime,
        (
            "result = self._redundant_hire_selected(obs, cfg, result)",
            "result = self._seed_selected(obs, cfg, result)",
            "return self._committed_seed_retry_selected(obs, cfg, result)",
            "output = self._market_pressure_selected(obs, cfg, output)",
            "output = self._operating_stock_selected(obs, cfg, output)",
            "output=self.spatial.crop_market(obs,output,self._selected_snapshot(obs,output),",
            "returned = self._feed_stock_selected(obs, cfg or {}, returned)",
            "returned = self._early_capital_selected(obs, cfg or {}, returned)",
            "if not self.features.seed or not any(o and o[0] == 'BUY_SEED'",
            "if not self.features.redundant_hire:",
            "No units, quantities, economic barriers or suffix orders move.",
            "Reorder current-queue capital after feed-stock; no new producer.",
        ),
        "titan_runtime",
    )
    _require(
        frozen,
        (
            "Operating WHEAT/FERTILIZER and animal stock remain baseline-controlled.",
            "if o and o[0]=='SELL' and len(o)>2 and o[1] in PRODUCTS",
        ),
        "frozen_selected",
    )
    _require(scheduler, ("if p not in ('WHEAT','FERTILIZER')",), "scheduler")
    _require(history, ("if not self.terminal_enabled:return selected",), "terminal_history_join")
    _require(
        redundant,
        (
            "active_or_unknown_nonhire_order",
            "if isinstance(order, list) and order and order[0] == \"HIRE\"",
        ),
        "redundant_hire",
    )
    _require(seed_budget, ("if len(order) < 3 or order[0] != 'BUY_SEED':",), "seed_budget")
    _require(
        pressure,
        (
            "Preserve all orders, quantities, duplicate lots, economic barriers,",
            'SALE_ONLY_GOODS = frozenset(("CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL"))',
        ),
        "pressure_priority",
    )
    _require(
        operating,
        (
            "Reserve useful operating inputs already owned by the active producer.",
            "raise ValueError('unresolved_wheat_replenishment')",
            "Preserve up to two owned wheat units for the producer's reachable feeds.",
        ),
        "operating_stock",
    )
    _require(
        early,
        ("Purchases are never dropped or invented.", "Every original purchase stays on the tape."),
        "early_capital",
    )
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
            "returned['market']=[['SELL','FERTILIZER',1]]",
        ),
        "spatial_tempo",
    )

    _require(
        runtime,
        (
            "self.spatial.observe_market_receipt(obs,",
            "self.spatial.observe_crop_receipts(obs,",
            "returned=self.spatial.guard_crop_returned(obs,returned,post)",
        ),
        "titan_runtime_receipts",
    )
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

    mutators = {
        "frozen_selected": "SELL-only over baseline products; WHEAT/FERT/animal stock baseline-controlled",
        "redundant_hire": "HIRE-only admission/removal family; unknown nonhire rows are barriers",
        "seed_budget": "retains/reduces inherited BUY_SEED only",
        "committed_seed_retry": "disabled by exact config",
        "terminal_history": "history receipts active but terminal transform disabled and identity",
        "market_pressure": "reorders inherited sale-only goods; preserves orders and quantities",
        "operating_stock": "withholds already-owned FERT/WHEAT sales; refuses unresolved WHEAT replenishment",
        "spatial_idle_fertilizer": "may add one SELL FERTILIZER; no WHEAT acquisition",
        "crop_release": "sole source-bound dynamic BUY_PRODUCT WHEAT constructor",
        "feed_stock": "withholds already-owned WHEAT from sale; crop repair owns queue when active",
        "early_capital": "reorders inherited executable queue; never invents/drops purchases",
        "final_pressure": "same SELL-only pressure transform reapplied at returned-action boundary",
    }
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
        reason = "authenticated Arlene tape contains WHEAT purchases outside crop-repair ownership"
    else:
        decision = "SUBSUMED_NO_LAWFUL_RETIME"
        reason = (
            "authenticated tape has no WHEAT buy and the exact enabled transform chain has "
            "one dynamic WHEAT-buy constructor: crop input repair. It retries from the first "
            "lawful due callback, so moving an observed later repair earlier would have to "
            "cross an existing safety/receipt blocker."
        )

    result = {
        "schema": SCHEMA,
        "decision": decision,
        "reason": reason,
        "source_git_blobs": observed,
        "enabled_features": {key: cfg.get(key) for key in EXPECTED_FEATURES},
        "live_market_mutators": mutators,
        "engine_git_blob": ENGINE_BLOB,
        "arlene_git_blob": route["vendor_git_blob"],
        "route_wheat_buy_row_count": route_rows,
        "route_wheat_buy_steps": route["wheat_buy_steps"],
        "route_wheat_buy_quantities": route["wheat_buy_quantities"],
        "dynamic_crop_repair": dynamic,
        "limits": [
            "source/subsumption proof only; no gameplay action is mutated",
            "all source identity and semantic analysis derives from one immutable captured byte snapshot per path",
            "does not claim a repair naturally engages in a sampled game",
            "does not relax crop input receipt, funding, capacity, row or feed-stock ownership",
            "any future source/config/blob drift invalidates this disposition",
        ],
    }
    canonical = json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    result["result_sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return result


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pretty", action="store_true")
    args = ap.parse_args(argv)
    try:
        result = audit()
    except (AuditError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"townprocure-current-subsumption: {exc}", file=__import__("sys").stderr)
        return 2
    print(json.dumps(result, sort_keys=True, indent=2 if args.pretty else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
