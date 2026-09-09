#!/usr/bin/env python3
"""Apply the exact E07 variable-price BUY_PRODUCT source-boundary repair."""

from __future__ import annotations

import pathlib


LAB = pathlib.Path(__file__).resolve().parents[1]
SOURCE = LAB / "frozen_selected.py"
TESTS = LAB / "test_e07_same_turn_funding.py"

SOURCE_OLD = """    targets=set(targets)
    for source in range(target+1,len(original)):
"""
SOURCE_NEW = """    targets=set(targets)
    # A variable-price BUY_PRODUCT splits market interleaving.  A selected
    # sale after that boundary cannot safely fund an earlier fixed purchase.
    source_limit=barrier if barrier is not None else len(original)
    for source in range(target+1,source_limit):
"""

TEST_MARKER = "\n\nclass CanonicalSameTurnFundingBinding(unittest.TestCase):\n"
TEST_INSERT = """
    def test_later_variable_price_buy_blocks_sale_source_after_boundary(self):
        obs,base=fixture(shed={'MILK':1},money=0)
        base['market']=[[],['BUY_SEED','CARROT',1],
                        ['BUY_PRODUCT','WHEAT',1],['SELL','MILK',1]]
        original=deepcopy(base['market'])
        out,info=fund(obs,base,{'MILK'})
        self.assertEqual(out,original)
        self.assertEqual(info['reason'],'no-safe-prefix-sale')
        self.assertEqual(info['target_index'],1)
        self.assertEqual(sale_quantities(out),sale_quantities(original))
        self.assertEqual(base['market'],original)

    def test_sale_before_later_variable_price_buy_remains_eligible(self):
        obs,base=fixture(shed={'MILK':1},money=0)
        base['market']=[[],['BUY_SEED','CARROT',1],['SELL','MILK',1],
                        ['BUY_PRODUCT','WHEAT',1]]
        original=deepcopy(base['market'])
        out,info=fund(obs,base,{'MILK'})
        self.assertEqual(out,[['SELL','MILK',1],
                              ['BUY_SEED','CARROT',1],[],
                              ['BUY_PRODUCT','WHEAT',1]])
        self.assertTrue(info['applied'])
        self.assertEqual((info['source_index'],info['destination_index']),(2,0))
        self.assertEqual(sale_quantities(out),sale_quantities(original))
        self.assertEqual(base['market'],original)
"""


def replace_exactly_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one preimage, found {count}")
    return text.replace(old, new, 1)


def main() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    if "source_limit=barrier if barrier is not None else len(original)" in source:
        raise SystemExit("source repair already present; refuse duplicate mutation")
    source = replace_exactly_once(
        source, SOURCE_OLD, SOURCE_NEW, "frozen_selected.py"
    )

    tests = TESTS.read_text(encoding="utf-8")
    if "test_later_variable_price_buy_blocks_sale_source_after_boundary" in tests:
        raise SystemExit("boundary regression already present; refuse duplicate mutation")
    tests = replace_exactly_once(
        tests, TEST_MARKER, TEST_INSERT + TEST_MARKER,
        "test_e07_same_turn_funding.py",
    )

    SOURCE.write_text(source, encoding="utf-8")
    TESTS.write_text(tests, encoding="utf-8")


if __name__ == "__main__":
    main()
