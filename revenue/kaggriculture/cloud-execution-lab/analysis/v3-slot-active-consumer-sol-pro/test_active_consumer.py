from __future__ import annotations

from pathlib import Path
import unittest

import active_witness
import materialize_active_consumer as materialize


class SourceMaterializerTests(unittest.TestCase):
    def fixture(self) -> str:
        return '''import copy

def materialize_sales(orders,current,shed,targets,max_orders):
    return list(orders)

def fund_same_turn_acquisition(*args):
    return args[0],None

class SellScheduler:
    pass


class FrozenSelected(SellScheduler):
    def transform(self, obs, config, base):
        receipt_feasible=lambda plan:True
        item='MILK';route=[];current={};now=0
        if True:
            def feasible(plan):
                for t,q in plan:
                    if q<=0:continue
                    orders=base['market'] if t==now else route[t].get('market',[]) if t<len(route) else []
                    if len(orders)>=int(config.get('maxMarketOrdersPerTurn',10)):
                        offered=sum(max(0,int(o[2])) for o in orders if o and o[0]=='SELL' and o[1]==item)
                        if q>offered:return False
                return receipt_feasible(plan)
        best=None;self.planned={};self.diagnostics={};shed={};targets={}
        farm={};private={};shops=[]
        if best:
            item,plan,info=best
            selected_plans=plan if item=='__joint__' else {item:plan}
            for selected_item,selected_plan in selected_plans.items():
                current[selected_item]=dict(selected_plan).get(now,0)
                self.planned[selected_item]=[(t,q) for t,q in selected_plan if t>now and q>0]
            self.diagnostics['chosen']=info
        out=copy.deepcopy(base)
        # Preserve every original order index, including withheld SELL positions.
        # Extra stock is offered only after inherited orders unless moving an
        # already-selected sale earlier is required to fund a fixed acquisition.
        out['market']=materialize_sales(out['market'],current,shed,targets,
                                        int(config.get('maxMarketOrdersPerTurn',10)))
        out['market'],funding=fund_same_turn_acquisition(
            out['market'],farm,private,obs['market'],shops,config,now,targets,
            lambda product:self.rival_supply(obs,product))
        if funding is not None:self.diagnostics['same_turn_funding']=funding
        return out
'''

    def test_patch_is_unique_parseable_and_closes_both_anchors(self):
        source=self.fixture()
        patched=materialize.patch_source(source,expected_blob=None)
        self.assertNotEqual(source,patched)
        compile(patched,"fixture.py","exec")
        self.assertEqual(patched.count("def _planned_slot_reservations("),1)
        self.assertEqual(patched.count("def _selected_emission_report("),1)
        self.assertIn("len(orders)+reserved",patched)
        self.assertIn("chosen-plan-not-emitted",patched)

    def test_materialized_helpers_reserve_shared_rows_and_bind_emission(self):
        namespace={}
        exec(compile(materialize.patch_source(self.fixture(),expected_blob=None),
                     'fixture.py','exec'),namespace)
        reserve=namespace['_planned_slot_reservations']
        self.assertEqual(reserve({'CARROT':[(100,1)]},{'CARROT':1},
                                 'MILK',100,100,[]),1)
        self.assertEqual(reserve({'MILK':[(100,1)]},{'MILK':1},
                                 'MILK',100,100,[]),0)
        self.assertEqual(reserve({'CARROT':[(101,1)]},{},
                                 'MILK',100,101,[]),1)
        self.assertIsNone(reserve({'CARROT':[(True,1)]},{},
                                  'MILK',100,101,[]))
        report=namespace['_selected_emission_report'](
            {'MILK':((100,1),)},[['SELL','CARROT',1]],100)
        self.assertEqual(report['missing'],{'MILK':1})
        self.assertFalse(report['valid'])

    def test_duplicate_ambiguous_and_wrong_blob_inputs_fail_closed(self):
        patched=materialize.patch_source(self.fixture(),expected_blob=None)
        with self.assertRaises(ValueError):
            materialize.patch_source(patched,expected_blob=None)
        with self.assertRaises(ValueError):
            materialize.patch_source(self.fixture()+materialize.OLD_FEASIBLE,
                                     expected_blob=None)
        with self.assertRaises(ValueError):
            materialize.patch_source(self.fixture(),expected_blob="0"*40)


class ExactActiveConsumerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lab=Path(__file__).resolve().parents[2]
        cls.witness=active_witness.build_witness(cls.lab)

    def test_exact_source_and_runtime_binding(self):
        self.assertEqual(self.witness['source_inputs'],materialize.EXPECTED_BLOBS)
        self.assertEqual(self.witness['runtime_binding'],
                         'Features.consumer=frozen -> root frozen_selected.FrozenSelected')
        self.assertEqual(len(self.witness['patched_git_blob']),40)

    def test_predecessor_reproduces_chosen_but_omitted_row(self):
        row=self.witness['predecessor']
        self.assertEqual(row['runtime_consumer'],'frozen')
        self.assertEqual(row['inherited_rows'],9)
        self.assertEqual(row['chosen_item'],'MILK')
        self.assertEqual(row['emitted_products'],['CARROT'])
        self.assertTrue(self.witness['verdicts']['predecessor_detached'])

    def test_successor_rejects_the_cross_product_collision(self):
        row=self.witness['successor']
        self.assertEqual(row['runtime_consumer'],'frozen')
        self.assertIsNone(row['chosen_item'])
        self.assertEqual(row['emitted_products'],['CARROT'])
        self.assertTrue(self.witness['verdicts']['successor_rejects_collision'])

    def test_emission_postcondition_restores_incumbent_state_and_action(self):
        row=self.witness['emission_guard']
        self.assertIsNone(row['chosen_item'])
        self.assertEqual(row['emitted_products'],['CARROT'])
        self.assertFalse(row['milk_planned_after'])
        self.assertEqual(row['selection_emission']['missing'],{'MILK':1})
        self.assertTrue(row['selection_emission']['fallback'])
        self.assertTrue(self.witness['verdicts']['emission_guard_restores_incumbent'])


if __name__=='__main__':
    unittest.main()
