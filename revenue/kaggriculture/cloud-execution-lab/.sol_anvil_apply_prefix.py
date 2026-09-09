#!/usr/bin/env python3
"""One-shot branch patcher. Deleted by its own successful workflow commit."""
from __future__ import annotations

import ast
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "frozen_selected.py"
TEST = ROOT / "test_frozen_active_prefix_funding.py"
RECEIPT = (
    ROOT.parents[2]
    / "p"
    / "titan-v3-frozen-active-prefix-funding-20260909-01.md"
)
EXPECTED_BLOB = "fc7baf5c179818a55037f6a61d92984d81d1a21c"


def git_blob_sha(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


TEST_CONTENT = r'''# SPDX-License-Identifier: Apache-2.0
"""Engine-prefix regression for frozen seller same-turn acquisition funding."""
from __future__ import annotations

import ast
import copy
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "frozen_selected.py"
ENGINE = HERE / "reference" / "engine" / "kaggriculture.py"


def load_subject():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"), filename=str(SOURCE))
    wanted = {"sale_quantities", "fund_same_turn_acquisition"}
    body = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in wanted]
    if {node.name for node in body} != wanted:
        raise AssertionError("subject functions missing from frozen_selected.py")
    module = ast.Module(body=body, type_ignores=[])
    ast.fix_missing_locations(module)
    namespace = {"copy": copy}
    exec(compile(module, str(SOURCE), "exec"), namespace)
    namespace["_market_prefix_state"] = prefix_state
    return namespace["fund_same_turn_acquisition"]


def prefix_state(orders, farm, private, market, shops, config, now, rival_quantity, stop):
    """Exact fixed-price fixture for the order-prefix boundary under test."""
    del market, shops, config, now, rival_quantity
    money = int(farm["money"])
    shed = dict(private["shed"])
    outcomes = {}
    stress = []
    stop = min(int(stop), len(orders) - 1)
    for index, order in enumerate(orders[: stop + 1]):
        if not order:
            continue
        if order[0] == "SELL" and len(order) > 2 and order[1] == "CARROT":
            sold = min(max(0, int(order[2])), max(0, int(shed.get("CARROT", 0))))
            shed["CARROT"] = max(0, int(shed.get("CARROT", 0)) - sold)
            money += sold * 35
            stress.append(
                {
                    "index": index,
                    "item": "CARROT",
                    "quantity": sold,
                    "receipt": sold * 35,
                    "scenario": "fixed-price-fixture",
                }
            )
        elif order[0] == "BUY_PRODUCT":
            return {
                "money": money,
                "outcomes": outcomes,
                "unsupported_index": index,
                "shed": shed,
                "inventory": {},
                "sale_stress": stress,
            }
        elif order[0] == "BUY_LAND":
            completed = int(money >= 1000)
            if completed:
                money -= 1000
            outcomes[index] = {"required": 1, "completed": completed, "cost_per_unit": 1000}
    return {
        "money": money,
        "outcomes": outcomes,
        "unsupported_index": None,
        "shed": shed,
        "inventory": {},
        "sale_stress": stress,
    }


class FrozenActivePrefixFundingTest(unittest.TestCase):
    def setUp(self):
        self.subject = load_subject()
        self.farm = {"money": 900, "hires_today": 0, "unlocked_quadrants": ["NW"]}
        self.private = {"shed": {"CARROT": 3}}
        self.config = {"maxMarketOrdersPerTurn": 10}

    def call(self, orders):
        return self.subject(
            orders,
            self.farm,
            self.private,
            {"inventory": {"CARROT": 1000}},
            [],
            self.config,
            0,
            {"CARROT"},
            lambda _item: 0,
        )

    def test_off_prefix_target_cannot_activate_sale_only(self):
        orders = [[] for _ in range(10)] + [["BUY_LAND"], ["SELL", "CARROT", 3]]
        transformed, info = self.call(orders)
        self.assertEqual(transformed, orders)
        self.assertIsNone(info)
        self.assertFalse(any(row for row in transformed[:10]))

    def test_off_prefix_sale_cannot_fund_live_target(self):
        orders = [[] for _ in range(8)] + [["BUY_LAND"], [], ["SELL", "CARROT", 3]]
        transformed, info = self.call(orders)
        self.assertEqual(transformed, orders)
        self.assertEqual(info["reason"], "no-safe-prefix-sale")
        self.assertEqual(info["target_index"], 8)

    def test_live_prefix_sale_still_funds_live_target(self):
        orders = [[] for _ in range(8)] + [["BUY_LAND"], ["SELL", "CARROT", 3]]
        transformed, info = self.call(orders)
        self.assertTrue(info["applied"])
        self.assertEqual((info["source_index"], info["destination_index"]), (9, 7))
        self.assertEqual(transformed[7], ["SELL", "CARROT", 3])
        self.assertEqual(transformed[8], ["BUY_LAND"])
        state = prefix_state(
            transformed,
            self.farm,
            self.private,
            {},
            [],
            self.config,
            0,
            lambda _item: 0,
            9,
        )
        self.assertEqual(state["outcomes"][8]["completed"], 1)

    def test_reference_engine_truncates_queue_before_market_processing(self):
        source = ENGINE.read_text(encoding="utf-8")
        self.assertIn("queues.append(q[:max_orders])", source)


if __name__ == "__main__":
    unittest.main()
'''


RECEIPT_CONTENT = '''# Titan V3 frozen-seller active-prefix funding repair

Operation: `titan-v3-frozen-active-prefix-funding-20260909-01`
Carrier: `SOL-ANVIL`
Base commit: `c63a7e0d64d300b390b46bcc5b5c4e1331c264b5`
Base `frozen_selected.py` blob: `fc7baf5c179818a55037f6a61d92984d81d1a21c`

## Defect

`fund_same_turn_acquisition` inspected the complete inherited market list even though the pinned engine constructs each queue as `q[:max_orders]`. A failing fixed acquisition outside that executable prefix could become the modeled target, and a still-later sale could be moved into an earlier executable empty slot. The emitted action then executed the sale while the acquisition it allegedly funded remained truncated. A live acquisition could likewise consume a sale source that was not part of the inherited executable queue.

## Repair

The helper now derives one `active_end` from `maxMarketOrdersPerTurn`, evaluates only that prefix, and limits candidate sale sources to it. Invalid/nonpositive limits fail closed without mutating the inherited action. Within-prefix sale funding behavior and total-sale preservation are unchanged.

## Verification

The one-shot workflow required the new four-test regression to fail against the predecessor before applying the patch, then pass afterward. Cases cover an off-prefix target, an off-prefix source, a positive within-prefix control, and a direct assertion against the pinned engine's `queues.append(q[:max_orders])` truncation.

This is an engine-semantics repair only. It makes no leaderboard, matchup, or playing-strength claim and does not alter any canonical archive, export, default flag, provider action, route, seed, or opponent logic.
'''


def write_support_files() -> None:
    TEST.write_text(TEST_CONTENT, encoding="utf-8")
    RECEIPT.parent.mkdir(parents=True, exist_ok=True)
    RECEIPT.write_text(RECEIPT_CONTENT, encoding="utf-8")


def apply_patch() -> None:
    raw = SOURCE.read_bytes()
    observed = git_blob_sha(raw)
    if observed != EXPECTED_BLOB:
        raise SystemExit(
            f"refusing stale patch: expected blob {EXPECTED_BLOB}, observed {observed}"
        )
    text = raw.decode("utf-8")
    old_intro = '''    original=copy.deepcopy(orders)
    if not original:return original,None
    baseline=_market_prefix_state(
        original,farm,private,market,shops,config,now,rival_quantity,len(original)-1)
'''
    new_intro = '''    original=copy.deepcopy(orders)
    if not original:return original,None
    try:
        max_orders=int(config.get('maxMarketOrdersPerTurn',10))
    except (TypeError,ValueError,OverflowError):
        return original,{'applied':False,'reason':'invalid-market-prefix-limit'}
    if max_orders<=0:
        return original,{'applied':False,'reason':'invalid-market-prefix-limit'}
    active_end=min(len(original),max_orders)
    baseline=_market_prefix_state(
        original,farm,private,market,shops,config,now,rival_quantity,active_end-1)
'''
    old_source = "    source_limit=barrier if barrier is not None else len(original)\n"
    new_source = "    source_limit=min(active_end,barrier if barrier is not None else active_end)\n"
    old_doc = '''    Producer order indexes never move. A sale can occupy an earlier empty slot or
    enlarge an earlier SELL of the same product. Total same-turn sale quantities
    are invariant, so this only realizes proceeds earlier; it never invents stock
    or future cash. BUY_PRODUCT is a hard boundary because its unit price changes
    with same-index market interleaving.
'''
    new_doc = '''    Only the engine-executable market prefix can define either the acquisition
    target or a funding sale source. Producer order indexes never move. A sale can
    occupy an earlier empty slot or enlarge an earlier SELL of the same product.
    Total same-turn sale quantities are invariant, so this only realizes proceeds
    earlier; it never invents stock or future cash. BUY_PRODUCT is a hard boundary
    because its unit price changes with same-index market interleaving.
'''
    for old, new, label in (
        (old_intro, new_intro, "active-prefix baseline"),
        (old_source, new_source, "active-prefix source bound"),
        (old_doc, new_doc, "active-prefix contract"),
    ):
        count = text.count(old)
        if count != 1:
            raise SystemExit(f"expected one {label} anchor, found {count}")
        text = text.replace(old, new, 1)
    SOURCE.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("support", "apply"))
    args = parser.parse_args()
    write_support_files()
    if args.mode == "apply":
        apply_patch()
