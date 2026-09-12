# SPDX-License-Identifier: Apache-2.0
"""Independent source, envelope, OFF-identity and full-interpreter regressions."""
from __future__ import annotations
import argparse
import copy
import itertools
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import audit_sale_timing as audit
import compose_rival_timing as composer

RUNTIME = None
MUTANT = None
MUTATIONS = {
    'drop_before_alignment': ("for alignment in ('before', 'paired', 'after'):", "for alignment in ('paired', 'after'):"),
    'current_turn_only': ('for step in range(now, end + 1):', 'for step in range(now, now + 1):'),
    'default_on': ("get('sellRivalTimingEnvelope') is True", "get('sellRivalTimingEnvelope', True) is True"),
    'touch_forced_rescue': ("if (reference_feasible and _acceptance_rule(config) == 'strict'", "if (_acceptance_rule(config) == 'strict'"),
    'touch_relaxed_rules': ("reference_feasible and _acceptance_rule(config) == 'strict'", "reference_feasible"),
}


class SaleTimingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = (RUNTIME / 'selected_sell_core.py').read_bytes()
        cls.source = composer.compose(cls.data)
        if MUTANT:
            before, after = MUTATIONS[MUTANT]
            if cls.source.decode().count(before) != 1:
                raise ValueError('mutation anchor is not unique')
            cls.source = cls.source.decode().replace(before, after, 1).encode()
        cls.old = audit.load_core(RUNTIME)
        cls.new = audit.load_core(RUNTIME, source=cls.source)
        cls.rows = json.loads((audit.HERE / 'sale_timing_witnesses.json').read_text())['cases']
        cls.engine = audit.OfficialHarness(RUNTIME)

    def one(self):
        row = min(self.rows, key=lambda r:r['witness']['delta'])
        return audit.row_args(row), row

    def test_source_authentication(self):
        self.assertEqual(composer.git_blob(self.data), composer.EXPECTED_BLOB)
        self.assertEqual(audit.authenticate(RUNTIME), audit.PINS)

    def test_outside_bytes_preserved(self):
        restored = composer.compose(self.data).decode().replace(composer.HELPER, '', 1)
        restored = restored.replace(composer.INSERT, '', 1)
        self.assertEqual(restored.encode(), self.data)

    def test_source_drift_refused(self):
        for data in (self.data+b'\n', self.data.replace(b'no parent code', b'changed parent'), b''):
            with self.subTest(size=len(data)), self.assertRaises(ValueError):
                composer.compose(data)

    def test_reapplication_refused_not_silently_overwritten(self):
        with self.assertRaises(ValueError):
            composer.compose(composer.compose(self.data))

    def test_composed_source_compiles(self):
        for optimize in (0, 1, 2):
            compile(self.source, 'experiment', 'exec', optimize=optimize)

    def test_default_off_full_diagnostics_identity(self):
        for row in self.rows:
            args = audit.row_args(row)
            self.assertEqual(self.new.optimize_lot(**args), self.old.optimize_lot(**args))

    def test_only_literal_true_enables(self):
        args, _ = self.one()
        for value in (False, None, 0, 1, 'true'):
            arg = dict(args, config={**audit.CONFIG,'sellRivalTimingEnvelope':value})
            self.assertEqual(self.new.optimize_lot(**arg), self.old.optimize_lot(**arg))

    def test_all_initial_counterexamples_removed(self):
        for row in self.rows:
            args = audit.row_args(row)
            candidate, _ = self.new.optimize_lot(**dict(args, config={**audit.CONFIG, 'sellRivalTimingEnvelope':True}))
            result = audit.find_worst(self.old, args, candidate)
            self.assertGreaterEqual(result['worst']['delta'], 0, row)

    def test_fixed_total_single_burst_complete_unique(self):
        scenarios = self.new._single_burst_timing_envelope([('none',0,'paired')],716,718,6)
        self.assertEqual(len(scenarios),10)
        actual = {(r,a) for _,r,a in scenarios if isinstance(r,tuple)}
        expected = {(((t,6),),a) for t in range(716,719) for a in ('before','paired','after')}
        self.assertEqual(actual,expected)

    def test_existing_scenarios_not_relabelled_or_duplicated(self):
        seed=[('no_rival',0,'paired'),('observed_paired',6,'paired'),('delayed',((717,6),),'paired')]
        result=self.new._single_burst_timing_envelope(seed,716,718,6)
        self.assertEqual(result[:len(seed)],seed)
        self.assertEqual(len(result),10)
        self.assertEqual(len({name for name,_,_ in result}),len(result))

    def test_zero_rival_is_exact_noop(self):
        seed=[('zero',0,'paired')]
        self.assertEqual(self.new._single_burst_timing_envelope(seed,716,718,0),seed)

    def test_horizon_and_quantity_budget_refused_not_clipped(self):
        for now,end,rival in [(0,16,6),(1,0,6),(-1,1,6),(0,1,101),(0,1,-1),(0,1,1.5),(0.0,1,6)]:
            with self.subTest(now=now,end=end,rival=rival),self.assertRaises(ValueError):
                self.new._single_burst_timing_envelope([],now,end,rival)

    def test_sparse_own_dates_still_cover_intermediate_rival_turns(self):
        args,_=self.one()
        args=dict(args,dates=[716,718],config={**audit.CONFIG,'sellRivalTimingEnvelope':True})
        _,info=self.new.optimize_lot(**args)
        self.assertIn('timing_717_before',info['scenarios'])

    def test_relaxed_acceptance_rules_untouched(self):
        args,_=self.one()
        for rule in ('expected_downside','minimax_regret'):
            opts=dict(args,config={**audit.CONFIG,'sellRivalTimingEnvelope':True,'sellAcceptanceRule':rule})
            with patch.object(self.new,'_single_burst_timing_envelope',side_effect=RuntimeError('unexpected experiment')):
                self.assertEqual(self.new.optimize_lot(**opts),self.old.optimize_lot(**opts))

    def test_forced_capacity_rescue_untouched(self):
        args,_=self.one()
        args=dict(args,reference=((718,args['quantity']),),minimum_now=1,
                  config={**audit.CONFIG,'sellRivalTimingEnvelope':True})
        with patch.object(self.new,'_single_burst_timing_envelope',side_effect=RuntimeError('unexpected experiment')):
            self.assertEqual(self.new.optimize_lot(**args),self.old.optimize_lot(**args))
        self.assertTrue(self.old.optimize_lot(**args)[1]['forced_feasibility'])

    def test_infeasible_reference_callback_untouched(self):
        args,_=self.one()
        ref=args['reference']
        args=dict(args,capacity_ok=lambda plan:tuple(plan)!=ref,
                  config={**audit.CONFIG,'sellRivalTimingEnvelope':True})
        with patch.object(self.new,'_single_burst_timing_envelope',side_effect=RuntimeError('unexpected experiment')):
            self.assertEqual(self.new.optimize_lot(**args),self.old.optimize_lot(**args))

    def test_full_engine_all_witnesses_both_seats_and_alignments(self):
        for row in self.rows:
            for seat,alignment in itertools.product(range(2),('paired','before','after')):
                model=self.old.MarketPath(row['item'],row['inventory'],None,row['shops'],audit.CONFIG,row['now'],row['dates'][-1])
                rival=tuple(tuple(x) for x in row['witness']['rival_orders'])
                for plan in (row['reference'],row['plan']):
                    actual=self.engine.run(row,plan,seat,alignment)
                    expected=model.score(plan,row['quantity'],rival,alignment,row['dates'][-1]==718)
                    self.assertEqual(actual,expected)

    def test_worst_discriminator_is_actual_terminal_cash(self):
        args,row=self.one()
        self.assertEqual(row['dates'][-1],718)
        for seat in range(2):
            ref=self.engine.run(row,row['reference'],seat,'before')
            old=self.engine.run(row,row['plan'],seat,'before')
            plan,info=self.new.optimize_lot(**dict(args,config={**audit.CONFIG,'sellRivalTimingEnvelope':True}))
            new=self.engine.run(row,plan,seat,'before')
            self.assertEqual(ref,(256,276,20,0))
            self.assertEqual(old,(235,272,37,0))
            self.assertGreaterEqual(new[0],ref[0])
            self.assertEqual(new[3],0)

    def test_input_containers_not_mutated(self):
        args,_=self.one()
        args['config']['sellRivalTimingEnvelope']=True
        before=copy.deepcopy(args)
        self.new.optimize_lot(**args)
        self.assertEqual(args,before)

    def test_cli_writes_only_new_scratch_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'new.py'
            command=[sys.executable,str(audit.HERE/'compose_rival_timing.py'),
                     '--source',str(RUNTIME/'selected_sell_core.py'),'--output',str(output)]
            first=subprocess.run(command,capture_output=True,text=True)
            self.assertEqual(first.returncode,0,first.stderr)
            self.assertEqual(output.read_bytes(),composer.compose(self.data))
            second=subprocess.run(command,capture_output=True,text=True)
            self.assertNotEqual(second.returncode,0)
            self.assertEqual(output.read_bytes(),composer.compose(self.data))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime',type=Path,required=True)
    parser.add_argument('--mutant',choices=sorted(MUTATIONS))
    args,rest=parser.parse_known_args()
    RUNTIME=args.runtime.resolve();MUTANT=args.mutant
    unittest.main(argv=[sys.argv[0],*rest])
