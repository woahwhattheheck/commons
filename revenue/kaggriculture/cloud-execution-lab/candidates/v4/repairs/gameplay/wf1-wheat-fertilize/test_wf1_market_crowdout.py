# SPDX-License-Identifier: Apache-2.0
"""Official-market witnesses for WF1's observed endgame fertilizer crowd-out.

These are regression characterization tests, NOT tests of a policy repair.
Set TITAN_REPLAY_RUNTIME to the locked detached runtime fixture. No downloads.
"""
import copy
import os
from pathlib import Path
import unittest
import run_wf1_replay as r

HERE=Path(__file__).resolve().parent
RUNTIME=Path(os.environ.get('TITAN_REPLAY_RUNTIME',str(HERE/'runtime-fixture')))


class OfficialMarketCrowdout(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=r.read_json(HERE/'REGRESSION-MARKET-FIXTURE.json')
        r.require(cls.fixture['episode']==107952194 and cls.fixture['step']==696,'wrong witness')
        cls.engine,cls.Struct,_=r.load_engine(RUNTIME)

    def market(self,arm,wheat_change=0,money_change=0,capacity=None,limit=None):
        f=copy.deepcopy(self.fixture['arms'][arm]);seat=self.fixture['candidate_seat']
        cfg=self.Struct(f['configuration'])
        if capacity is not None:cfg['shedCapacity']=capacity
        if limit is not None:cfg['maxMarketOrdersPerTurn']=limit
        f['privates'][seat]['shed']['WHEAT']+=wheat_change
        f['farms'][seat]['money']+=money_change
        state=[self.Struct(observation=self.Struct(player=i,farms=f['farms'],market=f['market'],
                   private=f['privates'][i]),action=f['actions'][i]) for i in range(2)]
        env=self.Struct(configuration=cfg)
        before=f['privates'][seat]['shed']['FERTILIZER']
        old=copy.deepcopy(f['actions'])
        self.engine._process_market(state,env)
        self.assertEqual(f['actions'],old,'observer must not rewrite the action tape')
        return f['privates'][seat]['shed']['FERTILIZER']-before,sum(f['privates'][seat]['shed'].values())

    def test_same_ten_row_action_both_arms(self):
        a,b=[self.fixture['arms'][arm]['actions'][1] for arm in ('off','on')]
        self.assertEqual(a,b)
        self.assertEqual(a['market'],[['HIRE']]*9+[['BUY_PRODUCT','FERTILIZER',10]])
    def test_off_has_seven_free_slots(self):
        shed=self.fixture['arms']['off']['privates'][1]['shed']
        self.assertEqual(sum(shed.values()),93);self.assertEqual(self.market('off'),(7,100))
    def test_on_has_four_free_slots(self):
        shed=self.fixture['arms']['on']['privates'][1]['shed']
        self.assertEqual(sum(shed.values()),96);self.assertEqual(self.market('on'),(4,100))
    def test_only_shed_item_difference_is_three_wheat(self):
        a,b=[self.fixture['arms'][arm]['privates'][1]['shed'] for arm in ('off','on')]
        delta={k:b.get(k,0)-a.get(k,0) for k in set(a)|set(b) if b.get(k,0)!=a.get(k,0)}
        self.assertEqual(delta,{'WHEAT':3})
    def test_remove_three_wheat_restores_seven_fills(self):
        self.assertEqual(self.market('on',wheat_change=-3),(7,100))
    def test_add_three_wheat_reproduces_four_fills(self):
        self.assertEqual(self.market('off',wheat_change=3),(4,100))
    def test_more_cash_does_not_restore_lost_fills(self):
        self.assertEqual(self.market('on',money_change=100000),(4,100))
    def test_more_capacity_restores_lost_fills(self):
        self.assertEqual(self.market('on',capacity=103),(7,103))
    def test_fertilizer_row_is_tenth_executable_slot(self):
        self.assertEqual(self.market('off',limit=9)[0],0)
        self.assertEqual(self.market('on',limit=9)[0],0)


if __name__=='__main__':unittest.main()
