#!/usr/bin/env python3
"""One-shot exact-preimage carrier for the TITAN operating-stock prefix repair."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

BASE = "0c1b997f13f429969b2874c90f9fdab11de3401a"
PREIMAGE_BLOB = "781aa90da0d85d0ba23c665e29d6087d182c085e"
ROOT = Path("revenue/kaggriculture/cloud-execution-lab")
SOURCE = ROOT / "operating_stock.py"
TESTS = ROOT / "test_operating_stock_prefix.py"
RECEIPT = Path("p/sol-prefix-titan-operating-stock-executable-prefix-20260909-01.md")


def git_blob(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replace_once(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one exact preimage, found {count}")
    return source.replace(old, new, 1)


def apply() -> None:
    data = SOURCE.read_bytes()
    actual = git_blob(data)
    if actual != PREIMAGE_BLOB:
        raise SystemExit(f"source preimage drift: {actual}")
    Path("/tmp/operating_stock.pre.py").write_bytes(data)
    source = data.decode("utf-8")

    source = replace_once(
        source,
        """    report = {'changed': False, 'reason': 'no_fertilizer_sale'}
    orders = selected.get('market') or []
    offered = sum(max(0, int(o[2])) for o in orders
                  if o and len(o) > 2 and o[:2] == ['SELL', 'FERTILIZER'])
    if not offered:
        return selected, report
    now = int(observation['step']); day = now // 24
    cfg = configuration or {}
""",
        """    report = {'changed': False, 'reason': 'no_fertilizer_sale'}
    orders = selected.get('market') or []
    cfg = configuration or {}
    # The official interpreter truncates every player's queue before
    # processing it. Inactive tail rows are data, not current actions.
    max_orders = max(1, int(cfg.get('maxMarketOrdersPerTurn', 10)))
    active_orders = orders[:max_orders]
    offered = sum(max(0, int(o[2])) for o in active_orders
                  if o and len(o) > 2 and o[:2] == ['SELL', 'FERTILIZER'])
    if not offered:
        return selected, report
    now = int(observation['step']); day = now // 24
""",
        "active-prefix setup",
    )
    source = replace_once(
        source,
        "    if any(o and o[0] == 'HIRE' for o in orders):\n",
        "    if any(o and o[0] == 'HIRE' for o in active_orders):\n",
        "current hire prefix",
    )
    source = replace_once(
        source,
        "        if any(o and o[0] == 'HIRE' for o in route[step].get('market', [])):\n",
        "        if any(o and o[0] == 'HIRE'\n               for o in (route[step].get('market') or [])[:max_orders]):\n",
        "future hire prefix",
    )
    source = replace_once(
        source,
        """    deposits = sum(max(0, int(o[2])) for o in orders
                   if o and len(o) > 2 and o[0] in ('BUY_PRODUCT', 'BUY_ANIMAL'))
""",
        """    deposits = sum(max(0, int(o[2])) for o in active_orders
                   if o and len(o) > 2 and o[0] in ('BUY_PRODUCT', 'BUY_ANIMAL'))
""",
        "current arrival prefix",
    )
    source = replace_once(
        source,
        "        for order in row.get('market', []):\n",
        "        for order in (row.get('market') or [])[:max_orders]:\n",
        "future arrival prefix",
    )
    source = replace_once(
        source,
        "    reservation_bound = min(len(obligations), max(0, int(cfg.get('maxMarketOrdersPerTurn', 10))))\n",
        "    reservation_bound = min(len(obligations), max_orders)\n",
        "shared prefix bound",
    )
    source = replace_once(
        source,
        "    for index, order in enumerate(out['market']):\n",
        "    for index, order in enumerate(out['market'][:max_orders]):\n",
        "rewrite only active prefix",
    )
    SOURCE.write_text(source, encoding="utf-8")
    TESTS.write_text(TEST_SOURCE, encoding="utf-8")


def receipt() -> None:
    if not SOURCE.is_file() or not TESTS.is_file():
        raise SystemExit("patched source/tests missing")
    RECEIPT.parent.mkdir(parents=True, exist_ok=True)
    RECEIPT.write_text(
        f"""# TITAN operating-stock executable-prefix repair

- Operation: `titan-operating-stock-executable-prefix-20260909-01`
- Base: `{BASE}`
- Exact source preimage Git blob: `{PREIMAGE_BLOB}`
- Official interpreter contract: each market queue is truncated to `q[:max_orders]` before any order is processed.

## Defect

`protect_operating_stock()` correctly modeled a bounded fertilizer reservation, but several current/future scans consumed the complete serialized market list. Rows beyond `maxMarketOrdersPerTurn` are inactive in the official engine. Tail HIRE/BUY rows could therefore veto a productive reservation, tail SELL rows could be treated as offers, and a successful proposal could rewrite inactive tail bytes.

## Repair

One engine-matching `max_orders = max(1, int(...))` now defines the active prefix. Current offers, HIRE boundaries, arrival bounds, replenishment barriers, the reservation cap, and final FERTILIZER sale edits all use only that prefix. Every tail row and index remains exact.

## Verification

- patched prefix contracts: 7/7 PASS;
- exact preimage restored as a mutant: KILLED by the new contracts;
- complete `test_operating_stock.py` plus prefix tests: PASS;
- present neighboring feed-stock, crop-release, and early-capital modules: PASS;
- Python compile: PASS;
- source SHA-256: `{sha256(SOURCE)}`;
- regression SHA-256: `{sha256(TESTS)}`.

No runtime/config/current archive, Kaggle/provider state, spend, leaderboard, game rule, or opponent code changed. No playing-strength or score claim is made. This repair removes false negatives and tail mutation from an already-enabled mechanism; P24/config bisection should evaluate the repaired candidate before attributing operating-stock value.
""",
        encoding="utf-8",
    )


TEST_SOURCE = r'''# SPDX-License-Identifier: Apache-2.0
"""Executable market-prefix regressions for operating-stock retention."""
from copy import deepcopy
import unittest

from test_operating_stock import OperatingStockTests


class OperatingStockPrefixTests(unittest.TestCase):
    def fixture(self):
        case = OperatingStockTests(
            methodName='test_reserve_actual_consumption_not_oversized_pickup_request'
        )
        case.setUp()
        return case

    @staticmethod
    def padded(first, tail, width=10):
        return [deepcopy(first), *([[] for _ in range(width - 1)]), deepcopy(tail)]

    def assert_reserved_with_tail(self, case, tail):
        original_tail = deepcopy(tail)
        case.selected['market'] = self.padded(['SELL', 'FERTILIZER', 9], tail)
        result, report = case.propose()
        self.assertTrue(report['changed'], report)
        self.assertEqual(report['reason'], 'reserve_reachable_fertilizer')
        self.assertEqual(result['market'][0], ['SELL', 'FERTILIZER', 7])
        self.assertEqual(result['market'][10], original_tail)
        self.assertEqual(result['market'][1:10], [[] for _ in range(9)])
        return result, report

    def test_inactive_current_hire_tail_does_not_block(self):
        self.assert_reserved_with_tail(self.fixture(), ['HIRE'])

    def test_inactive_current_purchase_tail_does_not_consume_capacity(self):
        self.assert_reserved_with_tail(self.fixture(), ['BUY_ANIMAL', 'COW', 100])

    def test_inactive_future_hire_tail_does_not_cut_service_horizon(self):
        case = self.fixture()
        case.route[462]['market'] = [[] for _ in range(10)] + [['HIRE']]
        result, report = case.propose()
        self.assertTrue(report['changed'], report)
        self.assertEqual(result['market'], [['SELL', 'FERTILIZER', 7]])

    def test_inactive_future_purchase_tail_is_not_replenishment(self):
        case = self.fixture()
        case.route[462]['market'] = (
            [[] for _ in range(10)] + [['BUY_PRODUCT', 'FERTILIZER', 3]]
        )
        result, report = case.propose()
        self.assertTrue(report['changed'], report)
        self.assertEqual(result['market'], [['SELL', 'FERTILIZER', 7]])

    def test_inactive_fertilizer_sale_tail_is_preserved_byte_for_byte(self):
        self.assert_reserved_with_tail(self.fixture(), ['SELL', 'FERTILIZER', 5])

    def test_sale_only_in_inactive_tail_is_not_an_offer(self):
        case = self.fixture()
        case.selected['market'] = [[] for _ in range(10)] + [['SELL', 'FERTILIZER', 9]]
        original = deepcopy(case.selected)
        result, report = case.propose()
        self.assertIs(result, case.selected)
        self.assertEqual(result, original)
        self.assertFalse(report['changed'])
        self.assertEqual(report['reason'], 'no_fertilizer_sale')

    def test_configured_two_order_prefix_ignores_slot_two_tail(self):
        case = self.fixture()
        case.selected['market'] = [
            ['SELL', 'FERTILIZER', 9], [], ['HIRE'], ['BUY_ANIMAL', 'COW', 100]
        ]
        original_tail = deepcopy(case.selected['market'][2:])
        result, report = case.propose(config={'maxMarketOrdersPerTurn': 2})
        self.assertTrue(report['changed'], report)
        self.assertEqual(result['market'][:2], [['SELL', 'FERTILIZER', 7], []])
        self.assertEqual(result['market'][2:], original_tail)
        self.assertEqual(report['reservation_bound'], 2)


if __name__ == '__main__':
    unittest.main(verbosity=2)
'''


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("apply", "receipt"))
    args = parser.parse_args()
    apply() if args.mode == "apply" else receipt()


if __name__ == "__main__":
    main()
