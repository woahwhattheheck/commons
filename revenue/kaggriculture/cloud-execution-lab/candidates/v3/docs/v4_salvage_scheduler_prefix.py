#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Rebase the reviewed SELL-scheduler executable-prefix repairs onto current V4.

Consumes the mechanics proved by V3 carriers #12005 (cash_reserve) and #12018
(receipt_profile) without copying either stale scheduler postimage.  Only the
current V4 scheduler blob and the still-identical pinned official engine are
accepted.  The output is a source-ready postimage for the serial V4 integrator.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


SCHEDULER_GIT_BLOB = "da1b6fb571e79ba7dab54c8d816e45afb934e4d2"
ENGINE_GIT_BLOB = "3c202c7ee921da239356789e266b694635103fc4"

ENGINE_ANCHORS = (
    'max_orders = max(1, int(get(env.configuration, "maxMarketOrdersPerTurn", 10)))',
    'q = list(m) if isinstance(m, list) else []',
    'queues.append(q[:max_orders])',
)

HELPER_ANCHOR = "\n\nclass SellScheduler:\n"
HELPER = '''\


def _engine_market_prefix(action, config):
    """Mirror the official interpreter's raw queue truncation before parsing."""
    market = action.get("market", []) if isinstance(action, dict) else []
    queue = list(market) if isinstance(market, list) else []
    return queue[:max(1, int(config.get("maxMarketOrdersPerTurn", 10)))]


class SellScheduler:
'''

CASH_OLD = '''\
            orders=base['market'] if t==now else (route[t].get('market',[]) if t<len(route) else [])
            for order in orders:
'''
CASH_NEW = '''\
            market_action=base if t==now else (route[t] if t<len(route) else parent.PASS)
            orders=_engine_market_prefix(market_action,config)
            for order in orders:
'''

RECEIPT_INITIAL_OLD = '''\
        f,p=copy.deepcopy(farm),copy.deepcopy(private)
        for o in base['market']:
'''
RECEIPT_INITIAL_NEW = '''\
        f,p=copy.deepcopy(farm),copy.deepcopy(private)
        for o in _engine_market_prefix(base,config):
'''

RECEIPT_LOOP_OLD = '''\
            orders=base['market'] if t==now else (route[t].get('market',[]) if t<len(route) else [])
            for o in orders:
'''
RECEIPT_LOOP_NEW = '''\
            market_action=base if t==now else (route[t] if t<len(route) else parent.PASS)
            orders=_engine_market_prefix(market_action,config)
            for o in orders:
'''


class MaterializationError(RuntimeError):
    pass


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def _require_blob(data: bytes, expected: str, label: str) -> None:
    actual = git_blob_sha(data)
    if actual != expected:
        raise MaterializationError(f"{label} blob mismatch: expected {expected}, got {actual}")


def materialize_bytes(scheduler_bytes: bytes, engine_bytes: bytes) -> bytes:
    _require_blob(scheduler_bytes, SCHEDULER_GIT_BLOB, "scheduler")
    _require_blob(engine_bytes, ENGINE_GIT_BLOB, "engine")
    try:
        source = scheduler_bytes.decode("utf-8")
        engine = engine_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise MaterializationError("scheduler and engine must be strict UTF-8") from exc

    for anchor in ENGINE_ANCHORS:
        if engine.count(anchor) != 1:
            raise MaterializationError(f"official engine prefix anchor drift: {anchor!r}")

    checks = (
        (HELPER_ANCHOR, 1, "helper anchor"),
        ("def _engine_market_prefix(", 0, "preexisting helper"),
        (CASH_OLD, 1, "cash-reserve loop"),
        (RECEIPT_INITIAL_OLD, 1, "receipt current-market prepass"),
        (RECEIPT_LOOP_OLD, 1, "receipt market loop"),
    )
    for needle, expected, label in checks:
        found = source.count(needle)
        if found != expected:
            raise MaterializationError(f"{label}: expected {expected}, found {found}")

    candidate = source.replace(HELPER_ANCHOR, HELPER, 1)
    candidate = candidate.replace(CASH_OLD, CASH_NEW, 1)
    candidate = candidate.replace(RECEIPT_INITIAL_OLD, RECEIPT_INITIAL_NEW, 1)
    candidate = candidate.replace(RECEIPT_LOOP_OLD, RECEIPT_LOOP_NEW, 1)

    if candidate.count("def _engine_market_prefix(") != 1:
        raise MaterializationError("materialized helper cardinality drift")
    if candidate.count("_engine_market_prefix(") != 4:  # def + three consumers
        raise MaterializationError("materialized prefix consumer cardinality drift")
    for retired, label in (
        (CASH_OLD, "cash-reserve"),
        (RECEIPT_INITIAL_OLD, "receipt prepass"),
        (RECEIPT_LOOP_OLD, "receipt loop"),
    ):
        if retired in candidate:
            raise MaterializationError(f"retired {label} preimage survived")
    compile(candidate, "<v4-scheduler-prefix-salvage>", "exec")
    return candidate.encode("utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scheduler", type=Path)
    parser.add_argument("engine", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args(argv)
    if args.output.resolve(strict=False) in {
        args.scheduler.resolve(strict=False), args.engine.resolve(strict=False)
    }:
        raise MaterializationError("output must not alias a bound input")
    scheduler_before = args.scheduler.read_bytes()
    engine_before = args.engine.read_bytes()
    candidate = materialize_bytes(scheduler_before, engine_before)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(candidate)
    if args.scheduler.read_bytes() != scheduler_before or args.engine.read_bytes() != engine_before:
        args.output.unlink(missing_ok=True)
        raise MaterializationError("bound input changed during materialization")
    if args.output.read_bytes() != candidate:
        raise MaterializationError("output readback mismatch")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
