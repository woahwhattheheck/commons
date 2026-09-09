#!/usr/bin/env python3
"""Temporary E08 composer: current-market replay fix plus landed E18 acceptance."""
from __future__ import annotations

import sys
from pathlib import Path


def patch_source(path: Path) -> None:
    s = path.read_text()
    start = s.index('def represented_shed_event(')
    end = s.index('\n\ndef product_event_dates', start)
    market_replay = '''def _project_represented_market(farm, private, orders, item, size):
    """Replay market effects needed by the existing receipt projection.

    Candidate SELL quantity for ``item`` is deliberately left unresolved, just
    like SellScheduler.receipt_profile. Other sales, product/animal receipts,
    and hires are exact represented state needed by future unit actions.
    """
    for order in orders:
        if not order:
            continue
        op=order[0]
        if op=='SELL' and len(order)>2 and order[1]!=item:
            q=max(0,int(order[2]))
            private['shed'][order[1]]=max(0,private['shed'].get(order[1],0)-q)
        elif op in ('BUY_PRODUCT','BUY_ANIMAL') and len(order)>2:
            q=max(0,int(order[2]))
            private['shed'][order[1]]=private['shed'].get(order[1],0)+q
        elif op=='HIRE':
            farm['hands'].append(m._spawn_hand(farm,size))
            private['inventories'].append({})


def represented_shed_event(now, baseline_end, hard_end, route, farm, private,
                            base, item, config):
    """Return this candidate item's first represented post-baseline shed deposit.

    Start from ``post_units(obs, base)`` and then replay *current* market before
    looking at future unit stages. That is the same phase ordering used by
    ``receipt_profile``: current HIRE/BUY state exists next turn, while the
    candidate item's current SELL remains unresolved because E08 may change it.
    HARVEST alone only creates carried inventory and therefore is not a trigger.
    """
    if hard_end<=baseline_end:
        return None
    f,p=copy.deepcopy(farm),copy.deepcopy(private)
    size=len(f['tiles'])
    turns_per_day=int(config.get('turnsPerDay',24))
    _project_represented_market(f,p,base.get('market',[]),item,size)
    for t in range(now+1,hard_end+1):
        action=route[t] if t<len(route) else parent.PASS
        before=sum(p['shed'].values())
        acts=[action.get('farmer',['PASS']),*action.get('hands',[])]
        for i,a in enumerate(acts):
            m._apply_unit_action(
                f,p,i,a,size,t//turns_per_day,turns_per_day,10**6)
        after=sum(p['shed'].values())
        if t>baseline_end and after>before:
            return t
        _project_represented_market(f,p,action.get('market',[]),item,size)
    return None
'''
    s = s[:start] + market_replay + s[end:]

    old = '''        end,horizon=event_aware_horizon(now,last,route,targets,shops,config)
        unit_event=(represented_shed_event(
            now,horizon['baseline_end'],horizon['hard_end'],route,farm,private,config)
                    if targets else None)
        if unit_event is not None:
            end=max(end,unit_event)
        horizon['unit_event']=unit_event
        horizon['extended']=end>horizon['baseline_end']
        self.diagnostics['horizon']=horizon
        budget=self.cash_reserve(obs,config,base,end)
'''
    new = '''        end,horizon=event_aware_horizon(now,last,route,targets,shops,config)
        unit_events={item:represented_shed_event(
            now,horizon['baseline_end'],horizon['hard_end'],route,farm,private,
            base,item,config) for item in targets}
        reached=[event for event in unit_events.values() if event is not None]
        if reached:
            end=max(end,max(reached))
        horizon['unit_events']=unit_events
        horizon['unit_event']=max(reached) if reached else None
        horizon['extended']=end>horizon['baseline_end']
        self.diagnostics['horizon']=horizon
        budget=self.cash_reserve(obs,config,base,end)
'''
    assert s.count(old) == 1
    s = s.replace(old, new, 1)
    old = '''            item_end=max(horizon['baseline_end'],
                         horizon['service_dates'].get(item,horizon['baseline_end']),
                         horizon['unit_event'] or horizon['baseline_end'])
'''
    new = '''            item_end=max(horizon['baseline_end'],
                         horizon['service_dates'].get(item,horizon['baseline_end']),
                         horizon['unit_events'].get(item) or horizon['baseline_end'])
'''
    assert s.count(old) == 1
    s = s.replace(old, new, 1)

    needle = "    return shared_slot_ledger(all_plans,orders_at,max_orders)\n\n\ndef event_aware_horizon"
    insert = '''    return shared_slot_ledger(all_plans,orders_at,max_orders)


def seller_choice_rank(info):
    """Return active admission plus deterministic rank for one optimizer report."""
    forced=bool(info.get('forced_feasibility',False))
    accepted=bool(info.get('accepted',float(info.get('worst_relative_gain',0.0))>0))
    score=float(info.get('acceptance_score',info.get('worst_relative_gain',0.0)))
    return forced or accepted,(forced,score)


def event_aware_horizon'''
    assert s.count(needle) == 1
    s = s.replace(needle, insert, 1)
    old = "            eligible=info['worst_relative_gain']>0 or info.get('forced_feasibility',False)\n            rank=(info.get('forced_feasibility',False),info['worst_relative_gain'])\n"
    assert s.count(old) == 1
    s = s.replace(old, "            eligible,rank=seller_choice_rank(info)\n", 1)
    old = "                if best is None or rank>(best[2].get('forced_feasibility',False),best[2]['worst_relative_gain']):best=(item,plan,info)"
    assert s.count(old) == 1
    s = s.replace(old, "                if best is None or rank>seller_choice_rank(best[2])[1]:best=(item,plan,info)", 1)
    old = "            ranked=sorted(options,key=lambda x:(x[2].get('forced_feasibility',False),x[2]['worst_relative_gain']),reverse=True)[:4]"
    assert s.count(old) == 1
    s = s.replace(old, "            ranked=sorted(options,key=lambda x:seller_choice_rank(x[2])[1],reverse=True)[:4]", 1)
    old = "                           'named_worst_relative_gain':metrics['worst_relative_gain'],\n                           'worst_relative_gain':independent}"
    assert s.count(old) == 1
    s = s.replace(old, "                           'named_worst_relative_gain':metrics['worst_relative_gain'],\n                           'worst_relative_gain':independent,\n                           'accepted':True,'acceptance_score':independent,\n                           'acceptance_rule':'joint_strict'}", 1)
    old = "                    if best is None or rank>(best[2].get('forced_feasibility',False),best[2]['worst_relative_gain']):"
    assert s.count(old) == 1
    s = s.replace(old, "                    if best is None or rank>seller_choice_rank(best[2])[1]:", 1)
    compile(s, str(path), 'exec')
    path.write_text(s)


def patch_tests(path: Path) -> None:
    s = path.read_text()
    s = s.replace("            10,18,23,tape,farm,private,\n            {'turnsPerDay':24,'shedCapacity':100})", "            10,18,23,tape,farm,private,{'market':[]},'MILK',\n            {'turnsPerDay':24,'shedCapacity':100})", 2)
    s = s.replace("            private_state(shed={'MILK':4},inventory={'CARROT':2}),\n            {'turnsPerDay':24,'shedCapacity':100})", "            private_state(shed={'MILK':4},inventory={'CARROT':2}),\n            {'market':[]},'MILK',{'turnsPerDay':24,'shedCapacity':100})", 1)
    s = s.replace("            private_state(shed={'MILK':4},inventory={'COW':1}),\n            {'turnsPerDay':24,'shedCapacity':100})", "            private_state(shed={'MILK':4},inventory={'COW':1}),\n            {'market':[]},'MILK',{'turnsPerDay':24,'shedCapacity':100})", 1)
    marker = "    def test_checkpoint_before_event_prevents_extension(self):\n"
    insert = '''    def test_current_hire_enables_future_hand_pickup_and_deposit(self):
        tape=route()
        tape[19]['hands']=[['PICKUP','CARROT',1]]
        tape[20]['hands']=[['DROP']]
        event=fs.represented_shed_event(
            10,18,23,tape,farm_at((4,4)),
            private_state(shed={'MILK':4,'CARROT':1}),
            {'market':[['HIRE']]},'MILK',
            {'turnsPerDay':24,'shedCapacity':100})
        self.assertEqual(event,20)

    def test_current_buy_product_feeds_future_represented_deposit(self):
        tape=route()
        tape[19]['hands']=[['PICKUP','CARROT',1]]
        tape[20]['hands']=[['DROP']]
        farm=farm_at((4,4));farm['hands']=[[5,4]]
        private=private_state(shed={'MILK':4});private['inventories'].append({})
        event=fs.represented_shed_event(
            10,18,23,tape,farm,private,
            {'market':[['BUY_PRODUCT','CARROT',1]]},'MILK',
            {'turnsPerDay':24,'shedCapacity':100})
        self.assertEqual(event,20)

    def test_current_non_target_sell_removes_future_pickup_stock(self):
        tape=route()
        tape[19]['hands']=[['PICKUP','CARROT',1]]
        tape[20]['hands']=[['DROP']]
        farm=farm_at((4,4));farm['hands']=[[5,4]]
        private=private_state(shed={'MILK':4,'CARROT':1});private['inventories'].append({})
        event=fs.represented_shed_event(
            10,18,23,tape,farm,private,
            {'market':[['SELL','CARROT',1]]},'MILK',
            {'turnsPerDay':24,'shedCapacity':100})
        self.assertIsNone(event)

    def test_current_target_sell_stays_unresolved_for_candidate_replay(self):
        tape=route()
        tape[19]['hands']=[['PICKUP','CARROT',1]]
        tape[20]['hands']=[['DROP']]
        farm=farm_at((4,4));farm['hands']=[[5,4]]
        private=private_state(shed={'CARROT':1});private['inventories'].append({})
        event=fs.represented_shed_event(
            10,18,23,tape,farm,private,
            {'market':[['SELL','CARROT',1]]},'CARROT',
            {'turnsPerDay':24,'shedCapacity':100})
        self.assertEqual(event,20)

'''
    assert s.count(marker) == 1
    s = s.replace(marker, insert + marker, 1)
    compile(s, str(path), 'exec')
    path.write_text(s)


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit('usage: e08_compose_patch.py SOURCE TEST')
    patch_source(Path(sys.argv[1]))
    patch_tests(Path(sys.argv[2]))


if __name__ == '__main__':
    main()
