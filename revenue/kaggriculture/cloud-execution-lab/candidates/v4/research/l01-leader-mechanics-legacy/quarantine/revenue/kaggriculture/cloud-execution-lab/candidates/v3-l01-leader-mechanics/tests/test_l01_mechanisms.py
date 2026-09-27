# SPDX-License-Identifier: Apache-2.0
"""Identity (flag off) and mutation (flag on) tests for L01 mechanisms."""
import copy
import hashlib
import importlib.util
from collections import Counter
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
CANONICAL_MAIN = HERE / 'canonical_main.py'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope='module')
def mechanics():
    return load('l01_mechanics_under_test', HERE / 'l01_mechanics.py')


@pytest.fixture(scope='module')
def pristine_routes(mechanics):
    arlene = load('l01_arlene_pristine', HERE / 'reference/next-panel/vendor/arlene.py')
    assert arlene.MAIN == mechanics.MAIN
    return copy.deepcopy(arlene.routes()), arlene.MAIN


def test_canonical_main_bytes():
    expected = hashlib.sha256(CANONICAL_MAIN.read_bytes()).hexdigest()
    assert expected == '0dae922de836cdb590891d9bbca9a58e18114ebcc64e16fb5b264311f07133e5'


def test_flag_off_identity(mechanics, pristine_routes):
    routes, main = pristine_routes
    R = copy.deepcopy(routes)
    before = copy.deepcopy(R[main])
    act = Counter()
    reasons = []
    mechanics.patch_routes(R, {k: False for k in ('LAND', 'SHEEP', 'DAY0BUY', 'TRANCHE', 'LEANPLANT')}, act, reasons)
    assert reasons == [mechanics.NOOP]
    assert act == Counter()
    assert R[main] == before


def test_land_on_posts_74_98_keeps_fallback(mechanics, pristine_routes):
    routes, main = pristine_routes
    R = copy.deepcopy(routes)
    act = Counter(); reasons = []
    mechanics.patch_routes(R, {'LAND': True}, act, reasons)
    m74 = R[main][74]['market']
    m98 = R[main][98]['market']
    assert ['BUY_LAND'] in m74
    assert ['BUY_LAND'] in m98
    assert ['BUY_LAND'] in R[main][150]['market']
    assert ['BUY_LAND'] in R[main][265]['market']
    assert act['LAND'] >= 2
    # original no-op wheat sell at 74 remains
    assert any(o == ['SELL', 'WHEAT', 0] for o in m74)


def test_sheep_rewrites_cows_after_t1(mechanics, pristine_routes):
    routes, main = pristine_routes
    R = copy.deepcopy(routes)
    act = Counter(); reasons = []
    mechanics.patch_routes(R, {'SHEEP': True}, act, reasons)
    counts, events = mechanics.animal_buys(R[main])
    opening = [(t, a, n) for t, a, n in events if t == 1]
    assert ('COW', 2) in [(a, n) for _, a, n in opening]
    assert all(a != 'COW' for t, a, n in events if t > 1)
    assert counts['COW'] == 2
    assert counts['SHEEP'] == 12  # 5 original + 7 converted
    assert counts['GOOSE'] == 3
    assert act['SHEEP'] >= 1


def test_day0buy_replaces_wheat13(mechanics, pristine_routes):
    routes, main = pristine_routes
    R = copy.deepcopy(routes)
    act = Counter(); reasons = []
    mechanics.patch_routes(R, {'DAY0BUY': True}, act, reasons)
    wanted = [['BUY_PRODUCT', item, n] for item, n in mechanics.DAY0_BASKET]
    assert R[main][0]['market'] == wanted
    assert ['BUY_PRODUCT', 'WHEAT', 13] not in R[main][0]['market']
    assert act['DAY0BUY'] >= 1


def test_leanplant_last_92_wheat_to_pass(mechanics, pristine_routes):
    routes, main = pristine_routes
    R = copy.deepcopy(routes)
    before = mechanics.plant_counts(routes[main])
    assert before['WHEAT'] == 164
    assert sum(before.values()) == 240
    act = Counter(); reasons = []
    mechanics.patch_routes(R, {'LEANPLANT': True}, act, reasons)
    after = mechanics.plant_counts(R[main])
    assert after['WHEAT'] == 72
    assert after['MELON'] == before['MELON']
    assert after['STRAWBERRY'] == before['STRAWBERRY']
    assert after['CARROT'] == before['CARROT']
    assert sum(after.values()) == 148
    assert act['LEANPLANT'] >= 92


def test_tranche_enlarges_wheat_carrot_and_packs(mechanics):
    flags = {'TRANCHE': True}
    act = Counter()
    action = {'farmer': ['PASS'], 'hands': [], 'market': [['SELL', 'WHEAT', 3]]}
    obs = {'step': 696, 'day': 29, 'private': {'shed': {'WHEAT': 80, 'CARROT': 40, 'MILK': 5, 'EGG': 2}}}
    out = mechanics.apply_tranche(action, obs, flags, act, shed=obs['private']['shed'])
    wheat = [o for o in out['market'] if o and o[0] == 'SELL' and o[1] == 'WHEAT'][0]
    carrot = [o for o in out['market'] if o and o[0] == 'SELL' and o[1] == 'CARROT'][0]
    assert wheat[2] == 57
    assert carrot[2] == 32
    items = [o[1] for o in out['market'] if o and o[0] == 'SELL']
    assert 'MILK' in items and 'EGG' in items
    assert act['TRANCHE'] >= 3
    # original action object not mutated
    assert action['market'] == [['SELL', 'WHEAT', 3]]


def test_tranche_flag_off_identity(mechanics):
    flags = {'TRANCHE': False}
    act = Counter()
    action = {'farmer': ['PASS'], 'hands': [], 'market': [['SELL', 'WHEAT', 3]]}
    obs = {'step': 696, 'day': 29, 'private': {'shed': {'WHEAT': 80, 'CARROT': 40}}}
    out = mechanics.apply_tranche(action, obs, flags, act)
    assert out is action
    assert act == Counter()


def test_tranche_skips_terminal_step(mechanics):
    flags = {'TRANCHE': True}
    act = Counter()
    action = {'farmer': ['PASS'], 'hands': [], 'market': []}
    obs = {'step': 718, 'day': 29, 'private': {'shed': {'WHEAT': 80, 'CARROT': 40}}}
    out = mechanics.apply_tranche(action, obs, flags, act, shed=obs['private']['shed'])
    assert out is action
    assert act == Counter()
