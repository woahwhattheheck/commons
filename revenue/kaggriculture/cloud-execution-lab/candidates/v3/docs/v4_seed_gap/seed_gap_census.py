# SPDX-License-Identifier: Apache-2.0
"""Source-only seed-burst census; this is not a game/economic evaluator."""
from __future__ import annotations

import argparse
import ast
import base64
from collections import Counter
import hashlib
import json
import lzma
from pathlib import Path

TAPE_BLOB = 'a43289b9cc5e34a2481fddf652762a7d92f427ef'
ROUTER_BLOB = 'a3e2fe87c717d128e43c9b65bae2265f40d1d76d'
CROPS = ('WHEAT', 'CARROT', 'TOMATO', 'STRAWBERRY', 'MELON')


def git_blob(data):
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()


def load_tapes(path):
    """Verify exact source, then decode only the literal; execute no source code."""
    raw = Path(path).read_bytes()
    if git_blob(raw) != TAPE_BLOB:
        raise ValueError('frozen tape Git identity mismatch')
    tree = ast.parse(raw)
    values = [ast.literal_eval(node.value) for node in tree.body
              if isinstance(node, ast.Assign)
              and any(isinstance(t, ast.Name) and t.id == '_B85'
                      for t in node.targets)]
    if len(values) != 1 or type(values[0]) is not str:
        raise ValueError('expected one literal tape payload')
    tapes = json.loads(lzma.decompress(base64.b85decode(values[0])))
    if type(tapes) is not list or len(tapes) != 13 or any(
            type(tape) is not list or len(tape) != 719 for tape in tapes):
        raise ValueError('expected 13 x 719 frozen actions')
    return tapes, hashlib.sha256(raw).hexdigest()


def routed_actions(tapes, plan):
    """Freeze Policy's plan-0 prefix, selected middle, and plan-2 endgame."""
    if type(plan) is not int or not 0 <= plan < 13:
        raise ValueError('invalid plan')
    if len(tapes) != 13 or any(len(tape) != 719 for tape in tapes):
        raise ValueError('invalid tape dimensions')
    result = [tapes[0 if step < 144 else plan if step < 648 else 2][step]
              for step in range(718)]
    # Policy liquidates at 718: it has no PLANT or BUY_SEED effect.
    return result + [{'farmer': ['PASS'], 'hands': [], 'market': []}]


def seed_ledger(actions, *, extra_buys=None, cap=10, watch=()):
    """Atomic PLANT groups first; filled seed buys afterward. All tiles valid."""
    if type(cap) is not int or cap <= 0:
        raise ValueError('cap must be a positive plain int')
    extra_buys = {} if extra_buys is None else extra_buys
    stock, bought, planted = Counter(), Counter(), Counter()
    misses, snapshots = [], []
    for step, action in enumerate(actions):
        if type(action) is not dict or type(action.get('farmer')) is not list:
            raise ValueError('malformed action/farmer')
        hands, market = action.get('hands'), action.get('market')
        if type(hands) is not list or type(market) is not list:
            raise ValueError('malformed hands/market')
        demand = Counter()
        for row in [action['farmer'], *hands]:
            if type(row) is not list or not row:
                raise ValueError('malformed worker command')
            if row[0] == 'PLANT':
                if len(row) != 2 or type(row[1]) is not str or row[1] not in CROPS:
                    raise ValueError('malformed PLANT')
                demand[row[1]] += 1
        before = dict(stock)
        for crop, count in demand.items():
            if stock[crop] < count:
                misses.append({'step': step, 'crop': crop,
                               'requested': count, 'available': stock[crop]})
            else:
                stock[crop] -= count
                planted[crop] += count
        after_units = dict(stock)
        rows = list(market)
        for crop, count in extra_buys.get(step, ()):
            if len(rows) >= cap:
                raise ValueError('intervention has no executable market slot')
            rows.append(['BUY_SEED', crop, count])
        for row in rows[:cap]:
            if type(row) is not list or not row or row[0] != 'BUY_SEED':
                continue
            if (len(row) != 3 or type(row[1]) is not str or row[1] not in CROPS
                    or type(row[2]) is not int or row[2] <= 0):
                raise ValueError('malformed BUY_SEED')
            stock[row[1]] += row[2]
            bought[row[1]] += row[2]
        if step in watch:
            snapshots.append({'step': step, 'before_units': before,
                              'raw_plant_demand': dict(demand),
                              'after_units': after_units,
                              'after_market': dict(stock),
                              'executable_market': rows[:cap]})
    return {'bought': dict(bought), 'modeled_plants_completed': dict(planted),
            'ending_seeds': dict(stock), 'atomic_shortfalls': misses,
            'snapshots': snapshots}


def census(tapes, source_sha256):
    plans = []
    for plan in range(13):
        result = seed_ledger(routed_actions(tapes, plan))
        plans.append({'plan': plan, **result})
    actions = routed_actions(tapes, 10)
    base = seed_ledger(actions, watch=range(260, 264))
    candidate = seed_ledger(actions, extra_buys={261: [('WHEAT', 2)]},
                            watch=range(260, 264))
    return {
        'schema': 'titan-v4-seed-source-census/v1',
        'verdict': 'SOURCE_CANDIDATE_ONLY',
        'tape_blob': TAPE_BLOB, 'tape_sha256': source_sha256,
        'routing_source_blob': ROUTER_BLOB,
        'routing_source_commit': '465f4263da1c98acf78889d67cdd21b61dbba145',
        'routing': {'opening_plan': 0, 'select_at': 144,
                    'force_plan_2_at': 648, 'liquidation_step': 718},
        'assumptions': ['initial seed stock is zero',
                        'every executable BUY_SEED fills completely',
                        'all requested PLANT tiles are valid',
                        'same-crop PLANT requests form an atomic group',
                        'unit phase precedes market phase',
                        'no repair queues or runtime action transforms are modeled'],
        'limitations': ['not evidence of live activation or economic gain',
                        'actual earlier invalid tiles can conserve seeds',
                        'actual earlier buy failures can reduce seeds',
                        'require exact-current runtime and paired game checks before promotion'],
        'plans': plans,
        'route10_probe': {
            'shop_pair': ['YARN_STORE', 'PET_CAFE'],
            'intervention': {'step': 261, 'row': ['BUY_SEED', 'WHEAT', 2]},
            'baseline': base, 'candidate': candidate,
            'modeled_additional_wheat_plants':
                candidate['modeled_plants_completed'].get('WHEAT', 0)
                - base['modeled_plants_completed'].get('WHEAT', 0),
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('tapes', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    tapes, sha = load_tapes(args.tapes)
    result = census(tapes, sha)
    args.output.write_text(json.dumps(result, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
