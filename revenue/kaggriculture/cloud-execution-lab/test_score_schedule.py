# SPDX-License-Identifier: Apache-2.0
"""Exact score/decision parity for the dated-consumption fast path.

The reference is the score body from selected_sell_core blob a743f3b2.
No game evaluator, private state or game seed is used.
"""
from contextlib import contextmanager
from copy import deepcopy
from itertools import product
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import selected_sell_core as core
sys.path.insert(0, str(HERE.parent / 'cloud-market-game-theory/adaptive'))
from recourse import compile_policy


def reference_score(self, plan, quantity, rival, alignment, terminal=False):
    inv=self.inventory;own_cash=other_cash=0;sold=0
    orders=dict(plan)
    for step in range(self.now,self.end+1):
        q=min(quantity-sold,max(0,orders.get(step,0)))
        r=(dict(rival).get(step,0) if isinstance(rival,tuple) else rival if step==self.now else 0)
        a,b,inv=self.joint(inv,q,r,alignment)
        own_cash+=a;other_cash+=b;sold+=q
        inv-=core.absorption(self.item,step,self.shops,self.config)
    remaining=quantity-sold
    carry=0.0
    if remaining and not terminal:
        carry=float(self.single(inv,remaining)[0])
    return own_cash+carry-other_cash, own_cash,other_cash,remaining


@contextmanager
def original_scores():
    with patch.object(core.MarketPath, 'score', reference_score):
        yield


def model_args(item='EGG', inventory=9998, now=241, end=249):
    return dict(item=item, inventory=inventory, params=None,
                shops=['BAKERY', 'BRUNCH_SPOT'], config={}, now=now, end=end)


def table_case(quantity=2, item='EGG', inventory=9998, now=241):
    end=now+8
    plans=[{'id':str(t), 'sales':[[t,quantity]]} for t in range(now+1,end+1)]
    if quantity>1:
        plans.append({'id':'split','sales':[[now+1,quantity//2],[end,quantity-quantity//2]]})
    streams=[('quiet', (), 'paired')]
    for amount, date, alignment in product(sorted({quantity,min(100,2*quantity)}),
                                          (now,now+1,end),('before','paired','after')):
        streams.append((str(len(streams)),((date,amount),),alignment))
    for date,alignment in product((now+1,end),('paired','after')):
        streams.append((str(len(streams)),((now,min(quantity,50)),(date,min(quantity,50))),alignment))
    while len(streams)<32:
        streams.append((str(len(streams)),((now+2,len(streams)),),'paired'))
    return model_args(item,inventory,now,end),plans,streams


class ScoreScheduleTests(unittest.TestCase):
    def test_complete_receipt_parity(self):
        cases=0
        for item, inv, quantity, now, alignment, terminal in product(
                core.m.PRODUCTS,(-20,9998,10300,100000),(0,2,17),(0,23,710),
                ('before','paired','after'),(False,True)):
            args=model_args(item,inv,now,now+8)
            args['shops']=['BAKERY','BRUNCH_SPOT','DAIRY','UNKNOWN']
            args['config']={'townShopSellInterval':3,'townCenterSellInterval':5}
            fast=core.MarketPath(**args);slow=core.MarketPath(**deepcopy(args))
            for rival in (quantity,((now,2),(now,3),(now+5,quantity))):
                plan=((now,quantity//2),(now+8,quantity-quantity//2))
                self.assertEqual(fast.score(plan,quantity,rival,alignment,terminal),
                                 reference_score(slow,plan,quantity,rival,alignment,terminal))
                cases+=1
        self.assertEqual(cases,3888)

    def test_repeated_calls_cache_only_consumption(self):
        model=core.MarketPath(**model_args())
        with patch.object(core,'absorption',wraps=core.absorption) as observed:
            for i in range(12):
                model.score(((242,1),(249,1)),2,((242,i),),'paired',True)
            self.assertEqual(observed.call_count,9)
        self.assertEqual(model._score_consumed,tuple(core.absorption('EGG',t,model.shops,{}) for t in range(241,250)))

    def test_mutated_context_invalidates(self):
        fast=core.MarketPath(**model_args());slow=core.MarketPath(**model_args())
        mutations=[lambda m:None,lambda m:m.config.update(townShopSellInterval=1),
                   lambda m:m.config.update(townCenterSellInterval=2),
                   lambda m:m.shops.append('BRUNCH_SPOT'),lambda m:setattr(m,'now',240),
                   lambda m:setattr(m,'end',251),lambda m:setattr(m,'item','FERTILIZER')]
        for change in mutations:
            change(fast);change(slow)
            self.assertEqual(fast.score(((242,1),(249,1)),2,3,'after'),
                             reference_score(slow,((242,1),(249,1)),2,3,'after'))

    def test_empty_horizon_does_not_inspect_unused_inputs(self):
        model=core.MarketPath(**model_args(now=9,end=8));model.shops=None;model.config=None
        self.assertEqual(model.score((),0,('malformed',),'paired',True),(0.0,0,0,0))

    def test_last_write_wins_and_carry(self):
        model=core.MarketPath(**model_args())
        for plan in ((),((241,10),(241,1),(249,1)),((240,10),(250,10)),((241,-2),)):
            for terminal in (False,True):
                self.assertEqual(model.score(plan,8,((241,10),(241,2)),'before',terminal),
                                 reference_score(model,plan,8,((241,10),(241,2)),'before',terminal))

    def test_inputs_unchanged(self):
        args=model_args();plan=[[242,1],[249,1]];rival=((242,3),)
        before=deepcopy((args,plan,rival));model=core.MarketPath(**args)
        for _ in range(3):model.score(plan,2,rival,'after')
        self.assertEqual((args,plan,rival),before)

    def test_optimizer_and_capacity_call_order(self):
        for item,quantity,inv in product(('EGG','WOOL','FERTILIZER'),(1,4,12),(9900,10000,11000)):
            args=dict(item=item,quantity=quantity,inventory=inv,params=None,
                shops=['BAKERY','BRUNCH_SPOT'],config={},now=241,dates=[241,242,245,249],
                reference=((241,quantity),),rival_quantity=quantity,minimum_now=0)
            old_calls=[];new_calls=[]
            def feasible(plan, target):
                target.append(tuple(plan));return dict(plan).get(241,0)>=min(1,quantity)
            with original_scores():
                expected=core.optimize_lot(**args,capacity_ok=lambda p:feasible(p,old_calls))
            actual=core.optimize_lot(**args,capacity_ok=lambda p:feasible(p,new_calls))
            self.assertEqual(actual,expected);self.assertEqual(new_calls,old_calls)

    def test_full_adaptive_trees(self):
        for item,quantity,inv,now in product(('EGG','WOOL','MILK'),(2,5,20),(9998,10300),(241,655)):
            args,plans,streams=table_case(quantity,item,inv,now)
            before=deepcopy((args,plans,streams))
            with original_scores():
                expected=compile_policy(core.MarketPath(**args),plans,quantity,streams,now+1,core.absorption)
            actual=compile_policy(core.MarketPath(**args),plans,quantity,streams,now+1,core.absorption)
            self.assertEqual(actual,expected);self.assertEqual((args,plans,streams),before)

    def test_fertilizer_does_not_consume_center_interval(self):
        args=model_args('FERTILIZER');args['config']['townCenterSellInterval']=0
        model=core.MarketPath(**args)
        self.assertEqual(model.score(((249,2),),2,2,'paired'),reference_score(model,((249,2),),2,2,'paired'))

    def test_invalid_shop_interval_still_raises(self):
        args=model_args();args['config']['townShopSellInterval']=0
        with self.assertRaises(ZeroDivisionError):core.MarketPath(**args).score((),2,0,'paired')


if __name__=='__main__':unittest.main()
