# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import build_productive_expansion as builder
import p01_productive_expansion_gate as gate


def fib(n):
    a, b = 1, 1
    for _ in range(n):
        a, b = b, a + b
    return a


# Exact submitted-R04 same-day parent-HIRE topology for the two route shapes.
_LOW = {
    18:(9,2), 19:(9,1), 20:(9,2), 21:(8,3), 22:(9,1), 23:(7,3),
    24:(9,1), 25:(6,4), 26:(7,3), 27:(0,10), 28:(9,2), 29:(9,2),
}
_HIGH = {
    18:(9,3), 19:(9,2), 20:(9,3), 21:(8,3), 22:(9,2), 23:(7,4),
    24:(9,2), 25:(6,5), 26:(7,4), 27:(0,10), 28:(9,2), 29:(9,2),
}


def _orders(count):
    return [['HIRE'] for _ in range(count)]


def fake_day_factory(plan_kind='low', hand_noise=0):
    table = _LOW if plan_kind == 'low' else _HIGH
    def native_day(native, day):
        prior, current = table[day]
        actions = []
        if prior:
            actions.append({'market': _orders(prior), 'hands': [['PASS']] * hand_noise})
        actions.append({'market': _orders(current), 'hands': [['PASS']] * hand_noise})
        return actions
    return native_day


def obs(price=140, inventory=10000, rival_tiles=None):
    own = {'tiles': [[None]]}
    rival = {'tiles': [rival_tiles or [None]]}
    return {
        'player': 0,
        'step': 432,
        'farms': [own, rival],
        'market': {'inventory': {'TOMATO': inventory}, 'prices': {'TOMATO': price}},
    }


class ProductiveExpansionGate(unittest.TestCase):
    def test_route_labor_cost_matches_exact_r04_hire_topology(self):
        self.assertEqual(gate.route_labor_cost(object(), fake_day_factory('low'), fib), 3694)
        self.assertEqual(gate.route_labor_cost(object(), fake_day_factory('high'), fib), 4668)

    def test_existing_hand_count_does_not_set_fibonacci_index(self):
        clean = gate.route_labor_cost(object(), fake_day_factory('low', 0), fib)
        noisy = gate.route_labor_cost(object(), fake_day_factory('low', 99), fib)
        self.assertEqual(clean, noisy)

    def test_fresh_day_resets_prior_hire_index(self):
        def native_day(native, day):
            # Three authored HIREs each independent day. If indices leaked across
            # dawn the second/third day would become much more expensive.
            return [{'market': _orders(3)}]
        expected = sum(gate.incremental_hire_cost(0, 3, gate._extra_workers(day), fib)
                       for day in range(18, 30))
        self.assertEqual(gate.route_labor_cost(object(), native_day, fib), expected)

    def test_same_action_parent_hires_shift_first_extra_hire(self):
        self.assertEqual(gate.incremental_hire_cost(1, 2, 1, fib), fib(3))
        self.assertEqual(fib(3), 3)  # fourth same-day HIRE costs three.

    def test_late_parent_hire_is_not_modeled_as_requestable(self):
        planned = [{'market': []} for _ in range(5)]
        planned[4]['market'] = [['HIRE']]
        with self.assertRaisesRegex(ValueError, 'last authored HIRE'):
            gate.authored_hire_context(planned)

    def test_visible_field_supply_counts_held_and_future_fertilized_ceiling(self):
        tile = {'crop':'TOMATO', 'planted_day':12, 'yield_units':3}
        self.assertEqual(gate.visible_rival_field_supply_bound(obs(rival_tiles=[tile])), 11)

    def test_seventy_dollar_case_is_rejected_by_modeled_full_execution_bound(self):
        market_price = lambda item, inv: 70
        record = gate.evaluate(obs(price=70), object(), fake_day_factory('low'), fib, market_price)
        self.assertFalse(record['decision'])
        self.assertEqual(record['modeled_cost_ceiling'], 8894)
        self.assertEqual(record['projected_gross_ceiling'], 5600)
        self.assertEqual(record['incremental_labor_cost_ceiling'], 3694)

    def test_high_quote_clean_field_can_admit(self):
        market_price = lambda item, inv: 140
        record = gate.evaluate(obs(price=140), object(), fake_day_factory('low'), fib, market_price)
        self.assertTrue(record['decision'])
        self.assertGreaterEqual(record['projected_gross_ceiling'], record['modeled_cost_ceiling'])

    def test_visible_field_supply_reduces_projected_gross(self):
        curve = lambda item, inv: max(1, 130 - max(0, inv - 10000))
        clean = gate.evaluate(obs(price=130), object(), fake_day_factory('low'), fib, curve)
        rival = {'crop':'TOMATO', 'planted_day':12, 'yield_units':3}
        crowded = gate.evaluate(obs(price=130, rival_tiles=[rival]), object(), fake_day_factory('low'), fib, curve)
        self.assertGreater(clean['projected_gross_ceiling'], crowded['projected_gross_ceiling'])
        self.assertEqual(crowded['visible_rival_field_supply_bound'], 11)

    def test_custom_curve_passthrough_is_identity_safe(self):
        record = gate.evaluate(obs(price=130), object(), fake_day_factory('low'), fib,
                               lambda item, inv: 129)
        self.assertIsNone(record['decision'])
        self.assertEqual(record['reason'], 'custom_market_curve')


class ProductiveExpansionPublication(unittest.TestCase):
    def _receipt(self):
        return {'schema': 'test', 'candidate_archive_sha256': 'abc'}

    def test_preexisting_receipt_reservation_leaves_no_orphan_tar(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); out=root/'out'; tar=root/'candidate.tar.gz'; receipt=root/'out-manifest.json'
            receipt.write_text('sentinel')
            with self.assertRaises(FileExistsError):
                builder._publish({'main.py': b'x'}, b'archive', self._receipt(), out, tar, receipt)
            self.assertFalse(tar.exists())
            self.assertFalse(out.exists())
            self.assertEqual(receipt.read_text(), 'sentinel')

    def test_archive_receipt_alias_rejected_before_publication(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); out=root/'out'; shared=root/'same'
            with self.assertRaisesRegex(ValueError, 'must be distinct'):
                builder._publish({'main.py': b'x'}, b'archive', self._receipt(), out, shared, shared)
            self.assertFalse(shared.exists())
            self.assertFalse(out.exists())

    def test_receipt_write_failure_rolls_back_owned_pair_and_output_tree(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); out=root/'out'; tar=root/'candidate.tar.gz'; receipt=root/'out-manifest.json'
            original = builder._write_reserved
            calls = {'n': 0}
            def fail_second(fd, payload):
                calls['n'] += 1
                if calls['n'] == 2:
                    raise OSError('injected receipt write failure')
                return original(fd, payload)
            with patch.object(builder, '_write_reserved', fail_second):
                with self.assertRaisesRegex(OSError, 'injected receipt'):
                    builder._publish({'main.py': b'x'}, b'archive', self._receipt(), out, tar, receipt)
            self.assertFalse(tar.exists())
            self.assertFalse(receipt.exists())
            self.assertFalse(out.exists())

    def test_success_publishes_both_final_files(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); out=root/'out'; tar=root/'candidate.tar.gz'; receipt=root/'out-manifest.json'
            builder._publish({'main.py': b'x'}, b'archive', self._receipt(), out, tar, receipt)
            self.assertEqual(tar.read_bytes(), b'archive')
            self.assertEqual((out/'main.py').read_bytes(), b'x')
            self.assertEqual(json_load(receipt)['schema'], 'test')


def json_load(path):
    import json
    return json.loads(path.read_text())


if __name__ == '__main__':
    unittest.main()
