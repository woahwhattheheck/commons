import unittest

from seller_regime_history import PublicRegimeHistory

PRODUCTS = ('CARROT', 'MILK')


def product_of(tile):
    if not isinstance(tile, dict):
        return None
    if tile.get('kind') == 'PLANT':
        return tile.get('crop')
    if tile.get('kind') == 'ANIMAL':
        return tile.get('product')
    return None


def tile(product='CARROT', yield_units=0):
    return {'kind': 'PLANT', 'crop': product, 'yield_units': yield_units}


def obs(step, *, rival_tile=None, inventory=None, player=0):
    rival_tile = {} if rival_tile is None else rival_tile
    inventory = {'CARROT': 10, 'MILK': 10} if inventory is None else inventory
    farm = {'tiles': [[rival_tile]]}
    empty = {'tiles': [[{}]]}
    return {
        'step': step,
        'player': player,
        'farms': [empty, farm] if player == 0 else [farm, empty],
        'market': {'inventory': dict(inventory)},
        'town': {'unlocked_shops': []},
    }


def no_absorption(product, step, shops, configuration):
    return 0


class RegimeHistoryTests(unittest.TestCase):
    def test_same_producer_yield_drop_is_harvest_evidence(self):
        h = PublicRegimeHistory()
        before = obs(0, rival_tile=tile(yield_units=4))
        after = obs(1, rival_tile=tile(yield_units=1))
        h.observe(before, after, {'market': []}, {}, products=PRODUCTS,
                  product_of=product_of, absorption=no_absorption)
        self.assertEqual(h.signal(1, 'CARROT')['short'], 3)

    def test_removed_producer_is_not_counted_as_harvest(self):
        h = PublicRegimeHistory()
        before = obs(0, rival_tile=tile(yield_units=4))
        after = obs(1, rival_tile={})
        h.observe(before, after, {'market': []}, {}, products=PRODUCTS,
                  product_of=product_of, absorption=no_absorption)
        self.assertEqual(h.signal(1, 'CARROT')['short'], 0)

    def test_one_event_does_not_extend_after_short_window(self):
        h = PublicRegimeHistory()
        h.harvests['CARROT'] = [(2, 9)]
        self.assertEqual(h.signal(12, 'CARROT')['stress'], 0)
        self.assertEqual(h.signal(12, 'CARROT')['long_rate'], 0)

    def test_repeated_events_form_bounded_long_memory(self):
        h = PublicRegimeHistory()
        h.harvests['CARROT'] = [(2, 9), (10, 9)]
        signal = h.signal(20, 'CARROT')
        self.assertEqual(signal['short'], 0)
        self.assertEqual(signal['repeat_support'], 2)
        self.assertEqual(signal['long_rate'], 6)
        self.assertEqual(signal['stress'], 6)

    def test_town_absorption_is_not_misattributed_to_rival(self):
        h = PublicRegimeHistory()
        before = obs(0, inventory={'CARROT': 10, 'MILK': 10})
        after = obs(1, inventory={'CARROT': 9, 'MILK': 10})
        h.observe(before, after, {'market': []}, {}, products=PRODUCTS,
                  product_of=product_of,
                  absorption=lambda p, *_: 1 if p == 'CARROT' else 0)
        self.assertEqual(h.flows.get('CARROT'), None)

    def test_own_requested_sale_is_removed_before_rival_lower_bound(self):
        h = PublicRegimeHistory()
        before = obs(0, inventory={'CARROT': 10, 'MILK': 10})
        after = obs(1, inventory={'CARROT': 18, 'MILK': 10})
        action = {'market': [['SELL', 'CARROT', 5]]}
        h.observe(before, after, action, {}, products=PRODUCTS,
                  product_of=product_of, absorption=no_absorption)
        self.assertEqual(h.flows['CARROT'], [(1, 3)])

    def test_missing_previous_action_keeps_residual_flow_unknown(self):
        h = PublicRegimeHistory()
        before = obs(0, inventory={'CARROT': 10, 'MILK': 10})
        after = obs(1, inventory={'CARROT': 20, 'MILK': 10})
        h.observe(before, after, None, {}, products=PRODUCTS,
                  product_of=product_of, absorption=no_absorption)
        self.assertEqual(h.flows.get('CARROT'), None)

    def test_mix_change_requires_persistence_and_resets_old_evidence(self):
        h = PublicRegimeHistory(change_confirmations=2)
        base = obs(0, rival_tile=tile('CARROT', 0))
        h.observe(None, base, None, {}, products=PRODUCTS,
                  product_of=product_of, absorption=no_absorption)
        h.harvests['CARROT'] = [(0, 8), (1, 8)]
        changed1 = obs(2, rival_tile=tile('MILK', 0))
        h.observe(base, changed1, {'market': []}, {}, products=PRODUCTS,
                  product_of=product_of, absorption=no_absorption)
        self.assertEqual(h.regime_step, 0)
        changed2 = obs(3, rival_tile=tile('MILK', 0))
        h.observe(changed1, changed2, {'market': []}, {}, products=PRODUCTS,
                  product_of=product_of, absorption=no_absorption)
        self.assertEqual(h.regime_step, 3)
        self.assertEqual(h.signal(3, 'CARROT')['stress'], 0)

    def test_stress_is_capacity_bounded(self):
        h = PublicRegimeHistory(capacity=100)
        h.harvests['CARROT'] = [(1, 500)]
        self.assertEqual(h.signal(1, 'CARROT')['stress'], 100)


if __name__ == '__main__':
    unittest.main()
