# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import build_productive_expansion as builder
import p01_productive_expansion_gate as gate
import publication_custody


def fib(n):
    a, b = 1, 1
    for _ in range(n):
        a, b = b, a + b
    return a


def noisy_day_factory(parent_hires=20, hand_noise=99):
    def native_day(native, day):
        return [{
            'market': [['HIRE'] for _ in range(parent_hires)],
            'hands': [['PASS'] for _ in range(hand_noise)],
        }]
    return native_day


def obs(hires_today=0, price=70, inventory=10000, rival_tiles=None):
    own = {'hires_today': hires_today, 'tiles': [[None]]}
    rival = {'hires_today': 0, 'tiles': [rival_tiles or [None]]}
    return {
        'player': 0,
        'step': 432,
        'farms': [own, rival],
        'market': {'inventory': {'TOMATO': inventory}, 'prices': {'TOMATO': price}},
    }


class ProductiveExpansionGate(unittest.TestCase):
    def test_first_two_fresh_day_hires_cost_two(self):
        self.assertEqual(gate.incremental_hire_cost(0, 0, 2, fib), 2)

    def test_same_action_parent_hire_shifts_only_same_day_append(self):
        self.assertEqual(gate.incremental_hire_cost(0, 1, 2, fib), 3)

    def test_fourth_same_day_hire_costs_fib_three(self):
        self.assertEqual(gate.incremental_hire_cost(3, 0, 1, fib), fib(3))
        self.assertEqual(fib(3), 3)

    def test_many_authored_future_hires_do_not_inflate_reject_floor(self):
        labor, by_day = gate.route_labor_cost_floor(
            obs(hires_today=0), object(), noisy_day_factory(parent_hires=30), fib
        )
        self.assertEqual(labor, 2)
        self.assertEqual(by_day, {18: 2})

    def test_future_days_are_not_consulted_by_reject_floor(self):
        calls = []
        def day18_only(native, day):
            calls.append(day)
            if day != 18:
                raise AssertionError('future conditional route spend is not floor authority')
            return [{'market': [], 'hands': []}]
        labor, by_day = gate.route_labor_cost_floor(
            obs(hires_today=0), object(), day18_only, fib
        )
        self.assertEqual(labor, 2)
        self.assertEqual(by_day, {18: 2})
        self.assertEqual(calls, [18])

    def test_large_standing_work_width_does_not_set_fibonacci_index(self):
        clean = gate.route_labor_cost_floor(
            obs(), object(), noisy_day_factory(parent_hires=0, hand_noise=0), fib
        )[0]
        noisy = gate.route_labor_cost_floor(
            obs(), object(), noisy_day_factory(parent_hires=0, hand_noise=200), fib
        )[0]
        self.assertEqual(clean, noisy)
        self.assertEqual(clean, 2)

    def test_current_hires_today_affects_only_day18_floor(self):
        labor, by_day = gate.route_labor_cost_floor(
            obs(hires_today=3), object(), noisy_day_factory(), fib
        )
        self.assertEqual(by_day, {18: fib(3) + fib(4)})
        self.assertEqual(by_day[18], 8)
        self.assertEqual(labor, 8)

    def test_flat_seventy_is_inconclusive_not_false_reject(self):
        record = gate.evaluate(
            obs(hires_today=0, price=70),
            object(),
            noisy_day_factory(),
            fib,
            lambda item, inv: 70,
        )
        self.assertIsNone(record['decision'])
        self.assertEqual(record['reason'], 'negative_payback_not_proven')
        self.assertEqual(record['labor_cost_floor'], 2)
        self.assertEqual(record['labor_cost_floor_by_day'], {18: 2})
        self.assertEqual(record['unavoidable_cost_floor'], 4502)
        self.assertEqual(record['gross_revenue_upper_bound'], 5600)

    def test_large_observed_same_day_ordinal_can_prove_negative(self):
        record = gate.evaluate(
            obs(hires_today=15, price=70),
            object(),
            noisy_day_factory(),
            fib,
            lambda item, inv: 70,
        )
        self.assertFalse(record['decision'])
        self.assertEqual(record['reason'], 'proven_negative_payback')
        self.assertEqual(record['labor_cost_floor'], 2584)
        self.assertEqual(record['unavoidable_cost_floor'], 7084)
        self.assertEqual(record['gross_revenue_upper_bound'], 5600)

    def test_visible_rival_field_is_telemetry_not_rejection_authority(self):
        curve = lambda item, inv: max(1, 130 - max(0, inv - 10000))
        clean = gate.evaluate(
            obs(price=130), object(), noisy_day_factory(), fib, curve
        )
        rival = {'crop': 'TOMATO', 'planted_day': 12, 'yield_units': 3}
        crowded = gate.evaluate(
            obs(price=130, rival_tiles=[rival]),
            object(),
            noisy_day_factory(),
            fib,
            curve,
        )
        self.assertEqual(crowded['visible_rival_field_projection'], 11)
        self.assertEqual(
            clean['gross_revenue_upper_bound'],
            crowded['gross_revenue_upper_bound'],
        )
        self.assertEqual(clean['decision'], crowded['decision'])
        self.assertGreater(
            clean['modeled_gross_visible_field'],
            crowded['modeled_gross_visible_field'],
        )

    def test_custom_curve_passthrough_is_identity_safe(self):
        record = gate.evaluate(
            obs(price=130),
            object(),
            noisy_day_factory(),
            fib,
            lambda item, inv: 129,
        )
        self.assertIsNone(record['decision'])
        self.assertEqual(record['reason'], 'custom_market_curve')

    def test_future_floor_quote_below_current_passthrough(self):
        def curve(item, inv):
            return 60 if inv < 10000 else 70
        record = gate.evaluate(
            obs(price=70), object(), noisy_day_factory(), fib, curve
        )
        self.assertIsNone(record['decision'])
        self.assertEqual(record['reason'], 'unsupported_market_curve')

    def test_town_drain_below_zero_is_included_in_gross_ceiling(self):
        def scarcity_curve(item, inv):
            return 70 + max(0, 1000 - inv)
        record = gate.evaluate(
            obs(hires_today=24, price=70, inventory=1000),
            object(),
            noisy_day_factory(),
            fib,
            scarcity_curve,
        )
        self.assertEqual(record['future_inventory_floor'], -3896)
        self.assertEqual(record['future_tomato_quote_ceiling'], 4966)
        self.assertEqual(record['gross_revenue_upper_bound'], 397280)
        self.assertEqual(record['labor_cost_floor'], 196418)
        self.assertEqual(record['unavoidable_cost_floor'], 200918)
        self.assertIsNone(record['decision'])
        self.assertEqual(record['reason'], 'negative_payback_not_proven')

    def test_market_param_override_passthrough(self):
        observation = obs()
        observation['market']['params'] = {'TOMATO': {'base': 999}}
        record = gate.evaluate(
            observation, object(), noisy_day_factory(), fib, lambda item, inv: 70
        )
        self.assertIsNone(record['decision'])
        self.assertEqual(record['reason'], 'custom_market_params')

    def test_missing_hires_today_passthrough(self):
        observation = obs()
        observation['farms'][0].pop('hires_today')
        record = gate.evaluate(
            observation,
            object(),
            noisy_day_factory(),
            fib,
            lambda item, inv: 70,
        )
        self.assertIsNone(record['decision'])
        self.assertEqual(record['reason'], 'unsupported_route_state')

    def test_wrapper_is_reject_only_and_exports_floor_telemetry(self):
        self.assertIn(b"record['decision'] is False", builder.WRAPPER)
        self.assertIn(b'p01_gross_upper_bound', builder.WRAPPER)
        self.assertIn(b'p01_unavoidable_cost_floor', builder.WRAPPER)
        self.assertNotIn(b'p01_gate_accepts', builder.WRAPPER)


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

    def test_shared_publication_failure_rolls_back_output_tree(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); out=root/'out'; tar=root/'candidate.tar.gz'; receipt=root/'out-manifest.json'
            with patch.object(publication_custody, 'publish_exclusive', side_effect=OSError('injected shared publication failure')) as shared:
                with self.assertRaisesRegex(OSError, 'injected shared publication failure'):
                    builder._publish({'main.py': b'x'}, b'archive', self._receipt(), out, tar, receipt)
            shared.assert_called_once()
            self.assertFalse(tar.exists())
            self.assertFalse(receipt.exists())
            self.assertFalse(out.exists())

    def test_success_delegates_pair_to_shared_publication_custody(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); out=root/'out'; tar=root/'candidate.tar.gz'; receipt=root/'out-manifest.json'
            original = publication_custody.publish_exclusive
            with patch.object(publication_custody, 'publish_exclusive', wraps=original) as shared:
                builder._publish({'main.py': b'x'}, b'archive', self._receipt(), out, tar, receipt)
            shared.assert_called_once()
            self.assertEqual(tar.read_bytes(), b'archive')
            self.assertEqual((out/'main.py').read_bytes(), b'x')
            self.assertEqual(json_load(receipt)['schema'], 'test')


def json_load(path):
    import json
    return json.loads(path.read_text())


if __name__ == '__main__':
    unittest.main()
