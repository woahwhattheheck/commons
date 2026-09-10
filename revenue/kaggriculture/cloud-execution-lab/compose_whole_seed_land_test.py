#!/usr/bin/env python3
"""Build the exact whole-seed/land composition test from immutable land donor."""
from __future__ import annotations

import hashlib
from pathlib import Path
import sys

DONOR_BLOB = '6b024738a0c26919773dd2e11c9d6c1bafc688a4'
COMPOSED_SOURCE_BLOB = '944f769c23f98ed65bfc33bf707452e46f3d7a06'
OUTPUT_BLOB = 'a53795540a375ccb11b3eb0de48fd242dc3bb84b'


def blob(data: bytes) -> str:
    return hashlib.sha1(
        b'blob ' + str(len(data)).encode() + b'\0' + data
    ).hexdigest()


def replace_once(text: str, old: str, new: str) -> str:
    assert text.count(old) == 1, (old, text.count(old))
    return text.replace(old, new, 1)


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit('usage: compose_whole_seed_land_test.py DONOR OUT')
    donor = Path(sys.argv[1])
    out = Path(sys.argv[2])
    data = donor.read_bytes()
    assert blob(data) == DONOR_BLOB, blob(data)
    text = data.decode()
    text = replace_once(
        text,
        '"""Atomic-parent and structural-target contracts for early-capital ordering."""',
        '"""Whole-row seed and structural land-target composition contracts."""',
    )
    text = replace_once(
        text,
        "EARLY_CAPITAL_BLOB = '21c4ac15583e45f6f55ef615d95fc3db93637194'",
        "EARLY_CAPITAL_BLOB = '944f769c23f98ed65bfc33bf707452e46f3d7a06'\n"
        "SEED_DONOR_HEAD = 'eef44eb74e427a2cfd96eedece6f99ed41ad330a'\n"
        "LAND_DONOR_HEAD = '69b07cf42d3111469e8523f84efd9014cc30c0a9'",
    )
    text = replace_once(
        text,
        'class EarlyCapitalRealTargetContracts(unittest.TestCase):',
        'class EarlyCapitalWholeSeedLandCompositionContracts(unittest.TestCase):',
    )
    methods = '''    def test_oversized_seed_row_cannot_jump_real_land_target(self):
        configuration = dict(CFG, maxMarketOrdersPerTurn=3)
        source = action([
            ['BUY_LAND'],
            ['BUY_SEED', 'WHEAT', 2],
            ['SELL', 'MELON', 1],
        ])
        observation = land_obs(
            ['NW', 'NE', 'SW'], money=760, shed={'MELON': 1})
        observation['private']['seeds']['WHEAT'] = 0

        fixed, report = order_early_capital(
            m, observation, configuration, source, future_wheat_route())

        self.assertTrue(report['changed'])
        self.assertEqual(report['certified_funding_rows'], [2])
        self.assertEqual(report['operating_seed_rows'], [])
        self.assertEqual(report['seed_allocations'], [])
        self.assertEqual(report['unmet_seed_demand'], {'WHEAT': 1})
        self.assertEqual(report['certified_land_rows'], [0])
        self.assertEqual(fixed['market'], [
            ['SELL', 'MELON', 1],
            ['BUY_LAND'],
            ['BUY_SEED', 'WHEAT', 2],
        ])
        self.assertCountEqual(fixed['market'], source['market'])

    def test_non_greedy_whole_row_cover_and_land_share_one_partition(self):
        configuration = dict(CFG, maxMarketOrdersPerTurn=4)
        source = action([
            ['BUY_LAND'],
            ['BUY_SEED', 'WHEAT', 1],
            ['BUY_SEED', 'WHEAT', 2],
            ['SELL', 'MELON', 1],
        ])
        observation = land_obs(
            ['NW', 'NE', 'SW'], money=760, shed={'MELON': 1})
        observation['private']['seeds']['WHEAT'] = 0
        route = future_wheat_route()
        route[3] = {
            'farmer': ['PLANT', 'WHEAT'],
            'hands': [],
            'market': [],
        }

        fixed, report = order_early_capital(
            m, observation, configuration, source, route)

        self.assertTrue(report['changed'])
        self.assertEqual(report['certified_funding_rows'], [3])
        self.assertEqual(report['operating_seed_rows'], [2])
        self.assertEqual(report['seed_allocations'], [{
            'index': 2,
            'crop': 'WHEAT',
            'requested': 2,
            'allocated': 2,
        }])
        self.assertEqual(report['unmet_seed_demand'], {})
        self.assertEqual(report['certified_land_rows'], [0])
        self.assertEqual(fixed['market'], [
            ['SELL', 'MELON', 1],
            ['BUY_SEED', 'WHEAT', 2],
            ['BUY_LAND'],
            ['BUY_SEED', 'WHEAT', 1],
        ])
        self.assertCountEqual(fixed['market'], source['market'])

'''
    text = replace_once(
        text,
        '    def test_fully_unlocked_land_does_not_activate_transform(self):\n',
        methods + '    def test_fully_unlocked_land_does_not_activate_transform(self):\n',
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text)
    actual = blob(out.read_bytes())
    assert actual == OUTPUT_BLOB, (actual, OUTPUT_BLOB)
    assert COMPOSED_SOURCE_BLOB in text
    print(actual)


if __name__ == '__main__':
    main()
