# SPDX-License-Identifier: Apache-2.0
"""Executed engine/capacity/source-custody gates; missing inputs FAIL, not skip."""
from __future__ import annotations
import copy
import hashlib
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import run_census as c
import storage_witness as w

RUNTIME=Path(os.environ['TITAN_RUNTIME']).resolve()
MANIFEST=Path(os.environ['TITAN_MANIFEST']).resolve()


class StorageContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs={rev:w.setup(RUNTIME,MANIFEST,rev) for rev in ('canonical_manifest','pr_head')}

    def cases(self,stock,harvest):
        for rev,loaded in self.inputs.items():
            for seat in (0,1):
                yield rev,w.compare_case(loaded,seat,stock,harvest)

    def test_losing_hire_is_blocked_after_full_eod(self):
        for rev,case in self.cases(85,15):
            with self.subTest(revision=rev,seat=case['seat']):
                self.assertEqual(case['donor_admission']['reason'],'admitted')
                self.assertEqual(case['donor_cash_delta'],-2)
                self.assertEqual(case['donor_fertilizer_delta'],0)
                self.assertTrue(case['donor_physical_equal'])
                self.assertTrue(case['donor_market_equal'])
                self.assertTrue(case['donor_town_equal'])
                self.assertTrue(case['bounded_baseline_equal'])
                self.assertEqual(case['arms']['donor']['steps'][-2]['private']['inventories'][-1],{'FERTILIZER':3})
                self.assertEqual(case['arms']['bounded']['final_cash'],5000)

    def test_55_dollar_hire_is_also_pure_loss_and_blocked(self):
        for rev,loaded in self.inputs.items():
            for seat in (0,1):
                case=w.compare_case(loaded,seat,85,15,hires_today=9)
                with self.subTest(revision=rev,seat=seat):
                    self.assertEqual(case['donor_admission']['reason'],'admitted')
                    self.assertEqual(case['donor_cash_delta'],-55)
                    self.assertEqual(case['donor_fertilizer_delta'],0)
                    self.assertTrue(case['donor_physical_equal'])
                    self.assertTrue(case['bounded_baseline_equal'])

    def test_roomy_hire_remains_byte_equivalent_to_donor(self):
        for rev,case in self.cases(60,15):
            with self.subTest(revision=rev,seat=case['seat']):
                self.assertEqual(case['donor_admission']['reason'],'admitted')
                self.assertEqual(case['donor_fertilizer_delta'],3)
                for key in ('final_cash','final_private','final_farms','final_market','final_town','actions','steps'):
                    self.assertEqual(case['arms']['bounded'][key],case['arms']['donor'][key],key)

    def test_no_harvest_boundary_preserves_donor_without_double_count(self):
        for rev,case in self.cases(85,0):
            with self.subTest(revision=rev,seat=case['seat']):
                self.assertEqual(case['arms']['bounded']['initial_stock_bound'],88)
                self.assertEqual(case['donor_fertilizer_delta'],3)
                self.assertEqual(case['arms']['bounded']['actions'],case['arms']['donor']['actions'])
                self.assertEqual(case['arms']['bounded']['final_private'],case['arms']['donor']['final_private'])

    def sample(self,rev='canonical_manifest',stock=85,harvest=15):
        loaded=self.inputs[rev]
        lane,ev,engine,spatial,mechanics,*_=loaded
        states,env,cfg,tape,start=w.fixture(ev,engine,0,stock,harvest)
        obs=copy.deepcopy(states[0].observation)
        bound=lambda o,r,e: spatial.SpatialTempo._idle_stock_bound(SimpleNamespace(m=mechanics),o,r,e)
        return lane,obs,cfg,tape,start,bound

    def test_twelve_unit_headroom_is_preserved(self):
        for rev in self.inputs:
            lane,obs,cfg,tape,start,bound=self.sample(rev,stock=85,harvest=1)
            self.assertEqual(bound(obs,tape,312)[0],89)
            self.assertFalse(w.capacity.certify(lane,obs,tape,cfg,bound)['allowed'])

    def test_veto_has_no_parent_or_pending_state_mutation(self):
        for rev in self.inputs:
            lane,obs,cfg,tape,start,bound=self.sample(rev)
            action=copy.deepcopy(tape[start]);state=lane._Day(12)
            before=copy.deepcopy((obs,action,tape,state.__dict__,lane.REPORT))
            result=w.capacity.consider(lane,lane._consider_hire,obs,action,state,tape,cfg,bound)
            self.assertIs(result,action)
            self.assertEqual((obs,action,tape,state.__dict__,lane.REPORT),before)

    def test_missing_day_evidence_fails_closed(self):
        lane,obs,cfg,tape,start,bound=self.sample()
        for length in (0,start,start+1,311):
            self.assertFalse(w.capacity.certify(lane,obs,tape[:length],cfg,bound)['allowed'])

    def test_unknown_or_unsafe_bound_fails_closed(self):
        lane,obs,cfg,tape,start,_=self.sample()
        for value in (None,[],(),(1,),(-1,set(),set()),(True,set(),set()),
                      (85.,set(),set()),(0,set(),set())):
            with self.subTest(value=str(value)):
                self.assertFalse(w.capacity.certify(lane,obs,tape,cfg,lambda *args:value)['allowed'])
        def broken(*args):raise ValueError('unsupported native certificate')
        self.assertFalse(w.capacity.certify(lane,obs,tape,cfg,broken)['allowed'])

    def test_configuration_malformed_and_out_of_window_decline(self):
        lane,obs,cfg,tape,start,bound=self.sample()
        for name,value in (('shedCapacity',200),('maxMarketOrdersPerTurn',11),('turnsPerDay',25),('marketParams',{'x':1})):
            variant=copy.deepcopy(cfg);variant[name]=value
            self.assertFalse(w.capacity.certify(lane,obs,tape,variant,bound)['allowed'])
        for step in (0,12*24+13,12*24+23,24*24+14):
            variant=copy.deepcopy(obs);variant['step']=step
            self.assertFalse(w.capacity.certify(lane,variant,tape,cfg,bound)['allowed'])
        self.assertFalse(w.capacity.certify(lane,None,tape,cfg,bound)['allowed'])

    def test_existing_native_bound_counts_carried_and_standing_inputs(self):
        lane,obs,cfg,tape,start,bound=self.sample(stock=60,harvest=15)
        self.assertEqual(bound(obs,tape,312)[0],78)
        obs['private']['inventories'][2]={'MILK':12}
        certificate=w.capacity.certify(lane,obs,tape,cfg,bound)
        self.assertEqual(certificate['stock_upper'],90)
        self.assertFalse(certificate['allowed'])

    def test_native_bound_does_not_credit_later_sales(self):
        lane,obs,cfg,tape,start,bound=self.sample()
        tape[305]['market']=[['SELL','CARROT',85]]
        self.assertEqual(bound(obs,tape,312)[0],103)
        self.assertFalse(w.capacity.certify(lane,obs,tape,cfg,bound)['allowed'])

    def test_future_hire_and_branch_crossing_have_no_stock_certificate(self):
        lane,obs,cfg,tape,start,bound=self.sample()
        tape[305]['market']=[['HIRE']]
        self.assertIsNone(bound(obs,tape,312))
        self.assertFalse(w.capacity.certify(lane,obs,tape,cfg,bound)['allowed'])
        obs['step']=218;tape=[{'farmer':['PASS'],'hands':[['PASS'],['PASS']],'market':[]} for _ in range(240)]
        self.assertIsNone(bound(obs,tape,240))

    def test_bounded_144_cell_engine_matrix(self):
        for loaded in self.inputs.values():
            for seat in (0,1):
                for stock in (0,60,82,85,87,100):
                    for harvest in (0,3,6,9,12,15):
                        case=w.compare_case(loaded,seat,stock,harvest)
                        with self.subTest(seat=seat,stock=stock,harvest=harvest):
                            base,trial,guard=(case['arms'][a] for a in ('baseline','donor','bounded'))
                            if guard['actions']==base['actions']:
                                for key in ('final_cash','final_private','final_farms','final_market','final_town'):
                                    self.assertEqual(guard[key],base[key])
                            else:
                                for key in ('final_cash','final_private','final_farms','final_market','final_town','actions'):
                                    self.assertEqual(guard[key],trial[key])
                                self.assertLessEqual(guard['initial_stock_bound'],88)
                                self.assertEqual(guard['final_private']['shed'].get('FERTILIZER',0),3)


class PreflightCustody(unittest.TestCase):
    def test_native_source_manifest_verifies_all_members(self):
        self.assertEqual(len(c.verify_inputs(RUNTIME,MANIFEST)),109)

    def test_missing_runtime_member_fails_not_skips(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(FileNotFoundError):c.verify_inputs(Path(d),MANIFEST)

    def test_manifest_drift_is_rejected_before_runtime_access(self):
        with tempfile.TemporaryDirectory() as d:
            bad=Path(d)/'manifest.json';bad.write_bytes(MANIFEST.read_bytes()+b'\n')
            with self.assertRaisesRegex(ValueError,'manifest differs'):c.verify_inputs(Path(d),bad)

    def test_changed_runtime_member_is_rejected(self):
        actual=Path.read_bytes
        def read(path):
            raw=actual(path)
            return raw+b'\n' if path==RUNTIME/'main.py' else raw
        with patch.object(Path,'read_bytes',read):
            with self.assertRaisesRegex(ValueError,'member mismatch'):c.verify_inputs(RUNTIME,MANIFEST)

    def test_both_donor_versions_are_authentic(self):
        self.assertEqual(c.blob((c.HERE/'donor/s1_canonical_manifest.py').read_bytes()),c.CANONICAL_DONOR_BLOB)
        self.assertEqual(c.blob((c.HERE/'donor/r04_s1_fert_sweep.py').read_bytes()),c.DONOR_BLOB)

    def test_donor_drift_is_rejected(self):
        actual=Path.read_bytes
        for name in ('s1_canonical_manifest.py','r04_s1_fert_sweep.py'):
            def read(path):
                raw=actual(path)
                return raw+b'\n' if path==c.HERE/'donor'/name else raw
            with patch.object(Path,'read_bytes',read):
                with self.assertRaisesRegex(ValueError,'donor'):c.verify_inputs(RUNTIME,MANIFEST)

    def test_packaged_manifest_is_bound(self):
        actual=Path.read_bytes
        def read(path):
            raw=actual(path)
            return raw+b'\n' if path==RUNTIME/'SOURCE.json' else raw
        with patch.object(Path,'read_bytes',read):
            with self.assertRaisesRegex(ValueError,'SOURCE.json'):c.verify_inputs(RUNTIME,MANIFEST)

if __name__=='__main__':unittest.main(verbosity=2)
