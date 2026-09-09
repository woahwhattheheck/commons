#!/usr/bin/env python3
"""Temporary branch materializer for W12; deleted by its guarded workflow."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

LAB = Path("revenue/kaggriculture/cloud-execution-lab")
SOURCE = LAB / "spatial_tempo.py"
TEST = LAB / "test_w12_stale_plan_state.py"
ANALYSIS = LAB / "analysis/w12-stale-plan-state"
RECEIPT = Path("p/sol-relay-titan-w12-stale-plan-state-20260909-01.md")

HELPER = '''    @staticmethod
    def _stock_total(stock):
        """Return a strict nonnegative observed stock total or ``None``."""
        if not isinstance(stock,dict):return None
        total=0
        for value in stock.values():
            if type(value) is not int or value<0:return None
            total+=value
        return total

    def _generic_extra_invalid_reason(self,obs,plan,worker,positions):
        """Recheck a retained optional HARVEST against the next public state.

        Generic tempo plans are authored from one observation but may survive
        intervening own actions. Only a still-pending optional harvest is
        guarded here; once it has executed, its delivery suffix remains owned by
        the existing recovery path.
        """
        if not isinstance(plan,dict):return 'malformed_extra_plan'
        extra=plan.get('extra')
        if extra is None or plan.get('kind') in ('idle_fertilizer','weed_continuation'):
            return None
        replacement=plan.get('replacement');step=plan.get('step')
        if not isinstance(replacement,list) or type(step) is not int:
            return 'malformed_extra_plan'
        offset=int(obs['step'])-step
        if offset<0:return 'malformed_extra_plan'
        remaining=replacement[offset:]
        if not any(isinstance(a,(list,tuple)) and a and a[0]=='HARVEST'
                   for a in remaining):
            return None
        if type(worker) is not int or worker<0 or worker>=len(positions):
            return 'extra_actor_changed'
        if not isinstance(extra,dict):return 'malformed_extra_prerequisite'
        tile_ref=extra.get('tile');item=extra.get('item');quantity=extra.get('quantity')
        if (not isinstance(tile_ref,(list,tuple)) or len(tile_ref)!=2
                or any(type(v) is not int for v in tile_ref)
                or not isinstance(item,str) or type(quantity) is not int or quantity<=0):
            return 'malformed_extra_prerequisite'
        x,y=tile_ref
        farms=obs.get('farms');player=obs.get('player')
        if (not isinstance(farms,list) or type(player) is not int
                or player<0 or player>=len(farms)):
            return 'malformed_extra_prerequisite'
        farm=farms[player];tiles=farm.get('tiles') if isinstance(farm,dict) else None
        if (not isinstance(tiles,list) or y<0 or y>=len(tiles)
                or not isinstance(tiles[y],list) or x<0 or x>=len(tiles[y])):
            return 'malformed_extra_prerequisite'
        tile=tiles[y][x]
        if not isinstance(tile,dict):return 'extra_harvest_changed'
        actual=None;animal=tile.get('animal');crop=tile.get('crop')
        if animal in self.m.ANIMALS:
            spec=self.m.ANIMALS[animal]
            if isinstance(spec,dict):actual=spec.get('product')
        elif crop in self.m.CROPS:
            spec=self.m.CROPS[crop]
            planted=tile.get('planted_day')
            first=spec.get('first_yield_day') if isinstance(spec,dict) else None
            if (not isinstance(spec,dict) or not spec.get('ongoing')
                    or type(planted) is not int or type(first) is not int):
                return 'extra_harvest_changed'
            try:day=int(obs['day'])
            except (KeyError,TypeError,ValueError):return 'malformed_extra_prerequisite'
            if day-planted<first:return 'extra_harvest_changed'
            actual=crop
        visible=tile.get('yield_units')
        if actual!=item or type(visible) is not int or visible!=quantity:
            return 'extra_harvest_changed'
        private=obs.get('private')
        if not isinstance(private,dict):return 'malformed_extra_prerequisite'
        shed=self._stock_total(private.get('shed'));inventories=private.get('inventories')
        if shed is None or not isinstance(inventories,list):
            return 'malformed_extra_prerequisite'
        carried=[]
        for inventory in inventories:
            value=self._stock_total(inventory)
            if value is None:return 'malformed_extra_prerequisite'
            carried.append(value)
        if shed+sum(carried)+quantity>100:return 'extra_capacity_changed'
        return None

    def _abandon_generic_extra(self,obs,plan,position,reason):
        """Remove optional work while preserving its endpoint and deadline."""
        now=int(obs['step']);end=plan.get('end')
        if type(end) is not int or end<=now:return None
        goal_ref=plan.get('goal')
        if (not isinstance(goal_ref,(list,tuple)) or len(goal_ref)!=2
                or any(type(v) is not int for v in goal_ref)):
            goal=position
        else:goal=tuple(goal_ref)
        left=end-now;trial=path(position,goal)
        if len(trial)>left:
            start=max(0,now-plan.get('step',now)) if type(plan.get('step')) is int else 0
            old=plan.get('replacement',[])
            old=old[start:start+left] if isinstance(old,list) else []
            trial=[list(a) if isinstance(a,(list,tuple)) and a and a[0] in MOVES
                   else ['PASS'] for a in old]
            trial=(trial+[['PASS']]*left)[:left]
        else:trial+=[['PASS']]*(left-len(trial))
        return dict(plan,step=now,origin=position,replacement=trial,extra=None,
                    invalidated_extra={'step':now,'reason':reason})

'''

BEGIN_GUARD = '''        farm=obs['farms'][obs['player']]
        positions=[tuple(farm['farmer']),*[tuple(p) for p in farm['hands']]]
        released=set()
        for i,plan in list(self.plans.items()):
            reason=self._generic_extra_invalid_reason(obs,plan,i,positions)
            if reason is None:continue
            extra=plan.get('extra') if isinstance(plan,dict) else None
            tile_ref=extra.get('tile') if isinstance(extra,dict) else None
            if (isinstance(tile_ref,(list,tuple)) and len(tile_ref)==2
                    and all(type(v) is int for v in tile_ref)):
                released.add(tuple(tile_ref))
            if type(i) is not int or i<0 or i>=len(positions):
                del self.plans[i]
            else:
                updated=self._abandon_generic_extra(obs,plan,positions[i],reason)
                if updated is None:del self.plans[i]
                else:self.plans[i]=updated
            self.events.append({'kind':'generic_extra_invalidated','step':now,
                'worker':i,'reason':reason,'tile':tuple(tile_ref) if tile_ref is not None
                and isinstance(tile_ref,(list,tuple)) else None})
        for i,plan in list(self.plans.items()):
'''

TEST_TEXT = '''import copy
import unittest

from spatial_tempo import SpatialTempo, unit


class Mechanics:
    CROPS={'CORN':{'ongoing':True,'first_yield_day':0}}
    ANIMALS={'COW':{'product':'MILK'}}

    @staticmethod
    def _farmer_position(farm,worker):
        return farm['farmer'] if worker==0 else farm['hands'][worker-1]


class Controller:
    def __init__(self,rows):
        self.cur='R';self.R={'R':rows}


def route_rows():
    return [{'farmer':['PASS'],'hands':[['NORTH']],
             'market':[['BUY_PRODUCT','WHEAT',1]]} for _ in range(24)]


def observation(*,step=11,yield_units=2,shed=None,tile=True):
    tiles=[[None for _ in range(10)] for _ in range(10)]
    if tile:
        tiles[0][1]={'kind':'PLANT','crop':'CORN','planted_day':0,
                     'yield_units':yield_units}
    return {'step':step,'day':0,'player':0,
            'farms':[{'farmer':(1,0),'hands':[(9,9)],'tiles':tiles}],
            'private':{'shed':{} if shed is None else dict(shed),
                       'inventories':[{},{}],'seeds':{}},
            'market':{'inventory':{},'params':{}}}


def committed(extra=None):
    if extra is None:
        extra={'tile':(1,0),'item':'CORN','quantity':2,'deposit_step':13}
    plan={'step':10,'worker':0,'end':15,'route':'R','origin':(0,0),
          'goal':(0,0),'saved_travel':0,'extra':extra,
          'original':[['PASS'] for _ in range(5)],
          'replacement':[['EAST'],['HARVEST'],['WEST'],['DROP'],['PASS']]}
    return {'step':10,'day':0,'plans':{0:plan},'events':[],
            'reserved':{(1,0)},'patches':{},'active':{0:15}}


def begin(obs,state=None):
    controller=Controller(route_rows());tempo=SpatialTempo(Mechanics())
    tempo._committed=copy.deepcopy(committed() if state is None else state)
    tempo._begin(controller,controller.R,copy.deepcopy(obs))
    return tempo,controller


class W12StalePlanStateTests(unittest.TestCase):
    def test_changed_tile_abandons_only_extra_and_preserves_row(self):
        tempo,controller=begin(observation(yield_units=1));row=controller.R['R'][11]
        self.assertEqual(['WEST'],unit(row,0))
        self.assertEqual([['NORTH']],row['hands'])
        self.assertEqual([['BUY_PRODUCT','WHEAT',1]],row['market'])
        self.assertIsNone(tempo.plans[0]['extra'])
        self.assertNotIn((1,0),tempo.reserved)
        event=[e for e in tempo.events if e.get('kind')=='generic_extra_invalidated'][-1]
        self.assertEqual('extra_harvest_changed',event['reason'])

    def test_same_state_preserves_exact_committed_action(self):
        tempo,controller=begin(observation())
        self.assertEqual(['HARVEST'],unit(controller.R['R'][11],0))
        self.assertEqual((1,0),tempo.plans[0]['extra']['tile'])
        self.assertIn((1,0),tempo.reserved)
        self.assertFalse(any(e.get('kind')=='generic_extra_invalidated' for e in tempo.events))

    def test_successful_stock_arrival_invalidates_before_harvest(self):
        tempo,controller=begin(observation(shed={'MILK':99}))
        self.assertEqual(['WEST'],unit(controller.R['R'][11],0))
        self.assertEqual('extra_capacity_changed',tempo.plans[0]['invalidated_extra']['reason'])

    def test_malformed_prerequisite_declines_without_exception(self):
        state=committed({'tile':(1,), 'item':'CORN','quantity':2,'deposit_step':13})
        tempo,controller=begin(observation(),state)
        self.assertEqual(['WEST'],unit(controller.R['R'][11],0))
        self.assertEqual('malformed_extra_prerequisite',
                         tempo.plans[0]['invalidated_extra']['reason'])

    def test_after_harvest_delivery_suffix_is_not_rewritten(self):
        obs=observation(step=12,tile=False);obs['private']['inventories'][0]={'CORN':2}
        tempo,controller=begin(obs)
        self.assertEqual(['WEST'],unit(controller.R['R'][12],0))
        self.assertIsNotNone(tempo.plans[0]['extra'])
        self.assertFalse(any(e.get('kind')=='generic_extra_invalidated' for e in tempo.events))


if __name__=='__main__':
    unittest.main()
'''


def patch() -> None:
    text = SOURCE.read_text(encoding="utf-8")
    helper_anchor = "    def _begin(self, controller, pristine, obs):\n"
    if text.count(helper_anchor) != 1:
        raise RuntimeError("unexpected _begin anchor")
    text = text.replace(helper_anchor, HELPER + helper_anchor)
    begin_anchor = "        farm=obs['farms'][obs['player']]\n        positions=[tuple(farm['farmer']),*[tuple(p) for p in farm['hands']]]\n        for i,plan in list(self.plans.items()):\n"
    if text.count(begin_anchor) != 1:
        raise RuntimeError("unexpected begin-state anchor")
    text = text.replace(begin_anchor, BEGIN_GUARD)
    state_anchor = "        if state:\n            state=dict(state,plans=dict(self.plans),events=list(self.events))\n"
    state_replacement = "        if state:\n            state=dict(state,plans=dict(self.plans),events=list(self.events),\n                       reserved=set(state.get('reserved',()))-released)\n"
    if text.count(state_anchor) != 1:
        raise RuntimeError("unexpected committed-state anchor")
    SOURCE.write_text(text.replace(state_anchor, state_replacement), encoding="utf-8")
    TEST.write_text(TEST_TEXT, encoding="utf-8")


def receipt() -> None:
    ANALYSIS.mkdir(parents=True, exist_ok=True);RECEIPT.parent.mkdir(parents=True, exist_ok=True)
    source_parent=os.environ["SOURCE_PARENT"];carrier=os.environ["GITHUB_SHA"]
    run=(os.environ["GITHUB_SERVER_URL"]+"/"+os.environ["GITHUB_REPOSITORY"]+
         "/actions/runs/"+os.environ["GITHUB_RUN_ID"])
    predecessor=int(Path("predecessor.status").read_text().strip())
    witness={
        "operation":"titan-frontier-W12-stale-plan-state-fingerprint-20260909-01",
        "source_parent":source_parent,"carrier_commit":carrier,
        "owner_path":str(SOURCE),
        "predecessor_witness":{"observation_step":11,"retained_action":"HARVEST",
            "target":[1,0],"authored_quantity":2,"observed_changed_quantity":1,
            "predecessor_result":"replayed stale HARVEST",
            "patched_result":"WEST toward certified endpoint; optional work released"},
        "invalidated_only_while_harvest_pending":True,
        "public_prerequisites":["actor exists","tile coordinates","derived product",
            "exact visible yield","observed physical storage headroom"],
        "excluded":["post-HARVEST delivery","idle_fertilizer","weed_continuation",
            "market rows","unrelated actors","runtime/config/default/archive activation"]}
    verification={"predecessor_unittest_exit":predecessor,
        "current_focused":"PASS (5 contracts)",
        "adjacent":"PASS: test_idle_fertilizer + test_weed_continuation",
        "disposable_canonical_build_check":"PASS",
        "official_matched_games":"NOT RUN: source-only correctness patch is not active canonical bytes",
        "workflow_run":run}
    (ANALYSIS/"witness.json").write_text(json.dumps(witness,indent=2,sort_keys=True)+"\n")
    (ANALYSIS/"verification.json").write_text(json.dumps(verification,indent=2,sort_keys=True)+"\n")
    RECEIPT.write_text(f'''# TITAN frontier W12 — retained optional-work state fingerprint

Operation: `titan-frontier-W12-stale-plan-state-fingerprint-20260909-01`

- Immutable parent: `{source_parent}`
- Materializer carrier: `{carrier}`
- Existing owner path: `{SOURCE}`
- New regression: `{TEST.name}`
- Earliest invalidation point: `_begin`, after the next own observation and before retained routes are republished.
- Scope: generic tempo `extra` segments only while their optional `HARVEST` remains pending.

## Proved behavior

The predecessor replays `HARVEST` after its authored target quantity changes from two units to one. Current code abandons only that optional work, routes the same actor from its actual position to the segment's already certified endpoint, pads to the original deadline, releases the tile reservation, and records the invalidation. An unchanged observation preserves the exact retained `HARVEST`. A newly observed stock arrival that removes immediate headroom invalidates before harvest. Malformed prerequisite data declines without throwing. Once harvest has executed, this guard does not rewrite the owned delivery suffix.

Unrelated actor actions and market rows are unchanged.

## Verification actually run

- Parent source + new regression: expected nonzero exit and `FAILED`.
- Patched source + five W12 contracts: PASS.
- `test_idle_fertilizer` and `test_weed_continuation`: PASS.
- Disposable canonical `build_integrated.py` rebuild followed by `--check`: PASS.
- Workflow: {run}

No official matched games were attributed: this source-only correctness PR does not activate rebuilt canonical bytes. No controller, runtime, configuration, default, archive, Kaggle, provider, credential, spend, or owner-PC action was changed.
''',encoding="utf-8")


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in {"patch", "receipt"}:
        raise SystemExit("usage: titan-w12-materialize.py patch|receipt")
    patch() if sys.argv[1] == "patch" else receipt()
