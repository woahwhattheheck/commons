#!/usr/bin/env python3
"""Execute the detached predecessor and active frozen-consumer successor."""
from __future__ import annotations

import argparse
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import types
from typing import Any

import materialize_active_consumer as materialize


def _load(name: str, path: Path):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    spec.loader.exec_module(module)
    return module


def _route() -> list[dict[str,Any]]:
    action={'farmer':['PASS'],'hands':[],'market':[]}
    return [copy.deepcopy(action) for _ in range(720)]


def _agent_with_module(runtime,module):
    route=_route()
    base_class=module.FrozenSelected

    class HarnessFrozen(base_class):
        def __init__(self):
            self.controller=types.SimpleNamespace(cur=0,R=[route])
            self.mode='candidate';self.pending={};self.planned={'CARROT':[(100,1)]}
            self.previous=None;self.observed_harvests={};self.diagnostics={}

    module.FrozenSelected=HarnessFrozen

    class FakeSeedBudget:
        def __init__(self,_routes):pass
        def remaining(self,*_args):return 0

    class FakeSpatial:
        def __init__(self,*_args,**_kwargs):
            self.transform=lambda obs,selected,controller:selected
        def install(self,_controller):pass

    fake_spatial=types.ModuleType('spatial_tempo')
    fake_spatial.SpatialTempo=FakeSpatial
    prior_frozen=sys.modules.get('frozen_selected')
    prior_spatial=sys.modules.get('spatial_tempo')
    old_load=runtime.load

    def fake_load(_name,path,*,cache=False):
        if str(path).endswith('seed_funding.py'):
            return types.SimpleNamespace(select_seed_queue=lambda *args:args[2])
        if str(path).endswith('seed_budget.py'):
            return types.SimpleNamespace(SeedBudget=FakeSeedBudget)
        return old_load(_name,path,cache=cache)

    try:
        sys.modules['frozen_selected']=module
        sys.modules['spatial_tempo']=fake_spatial
        runtime.load=fake_load
        agent=runtime.TitanAgent(runtime.Features(consumer='frozen',seed=False,funding=False))
        agent._initialize()
        if not isinstance(agent.consumer,HarnessFrozen):
            raise AssertionError('TitanAgent did not select the injected frozen consumer')
        return agent
    finally:
        runtime.load=old_load
        if prior_frozen is None:sys.modules.pop('frozen_selected',None)
        else:sys.modules['frozen_selected']=prior_frozen
        if prior_spatial is None:sys.modules.pop('spatial_tempo',None)
        else:sys.modules['spatial_tempo']=prior_spatial


def _configure(module,consumer,*,inherited_rows: int,drop_milk: bool=False):
    module.PRODUCTS=('CARROT','MILK')
    farm={'money':0,'hires_today':0,'unlocked_quadrants':['NW'],
          'tiles':[], 'hands':[]}
    private={'shed':{'CARROT':1,'MILK':1},'seeds':{},'inventories':[{}]}
    module.post_units=lambda obs,base,config:(copy.deepcopy(farm),copy.deepcopy(private))
    module.event_aware_horizon=lambda now,last,route,targets,shops,config:(
        101,{'baseline_end':101,'hard_end':101,'service_dates':{},
             'unit_event':None,'extended':False})
    module.represented_shed_event=lambda *args,**kwargs:None
    module.product_event_dates=lambda item,now,end,shops,config:[now,end]
    module.funded_minimum_now=lambda *args,**kwargs:(0,{'fixture':True})
    module.seller_public_observation=lambda obs:{'step':int(obs['step'])}
    module.fund_same_turn_acquisition=lambda orders,*args:(orders,None)

    def optimize_lot(**kwargs):
        item=kwargs['item'];reference=tuple(kwargs['reference'])
        if item=='MILK':
            candidate=((int(kwargs['now']),1),)
            allowed=bool(kwargs['capacity_ok'](candidate))
            plan=candidate if allowed else reference
            gain=10.0 if allowed else 0.0
        else:
            plan=reference;gain=0.0
        return plan,{'item':item,'quantity':kwargs['quantity'],
                     'worst_relative_gain':gain,'forced_feasibility':False,
                     'accepted':gain>0,'scenarios':{}}

    module.optimize_lot=optimize_lot
    module.seller_choice_rank=lambda info:(
        float(info.get('worst_relative_gain',0))>0,
        (False,float(info.get('worst_relative_gain',0))))
    consumer.observe=lambda obs:None
    consumer.cash_reserve=lambda obs,config,base,end:0
    consumer.receipt_profile=lambda *args:(lambda plan:True)
    consumer.rival_supply=lambda obs,item:0
    consumer.planned={'CARROT':[(100,1)]};consumer.pending={};consumer.diagnostics={}
    consumer.controller.R=[_route()];consumer.controller.cur=0
    orders=[['BUY_SEED','WHEAT',1] for _ in range(inherited_rows)]
    if drop_milk:
        real=module.materialize_sales
        def clipped(*args,**kwargs):
            return [row for row in real(*args,**kwargs)
                    if not (row and row[0]=='SELL' and row[1]=='MILK')]
        module.materialize_sales=clipped
    obs={'step':100,'player':0,
         'market':{'inventory':{'CARROT':10000,'MILK':10000},
                   'prices':{},'params':None},
         'town':{'unlocked_shops':[]},'farms':[{},{}],'private':{}}
    base={'farmer':['PASS'],'hands':[],'market':orders}
    return obs,{'episodeSteps':720,'maxMarketOrdersPerTurn':10},base


def _run_arm(runtime,module,*,inherited_rows: int,drop_milk: bool=False) -> dict[str,Any]:
    agent=_agent_with_module(runtime,module)
    obs,cfg,base=_configure(module,agent.consumer,
                            inherited_rows=inherited_rows,drop_milk=drop_milk)
    out=agent.consumer.transform(obs,cfg,base)
    emitted=[row[1] for row in out['market'] if row and row[0]=='SELL']
    chosen=agent.consumer.diagnostics.get('chosen')
    return {
        'runtime_consumer':agent.features.consumer,
        'inherited_rows':inherited_rows,
        'emitted_products':emitted,
        'chosen_item':None if chosen is None else chosen.get('item'),
        'selection_emission':agent.consumer.diagnostics.get('selection_emission'),
        'milk_planned_after':bool(agent.consumer.planned.get('MILK')),
        'market_rows':len(out['market']),
    }


def build_witness(lab: Path) -> dict[str,Any]:
    lab=lab.resolve()
    with tempfile.TemporaryDirectory() as name:
        work=Path(name)
        patched_path=work/'frozen_selected.py'
        receipt_path=work/'RECEIPT.json'
        receipt=materialize.materialize(lab,patched_path,receipt_path)
        sys.path.insert(0,str(lab))
        try:
            original=_load('_slot_original_frozen',lab/'frozen_selected.py')
            patched=_load('_slot_patched_frozen',patched_path)
            runtime=_load('_slot_titan_runtime',lab/'titan_runtime.py')
            predecessor=_run_arm(runtime,original,inherited_rows=9)
            successor=_run_arm(runtime,patched,inherited_rows=9)
            # Reload the patched module so the deliberate emitter fault cannot
            # inherit state from the capacity-collision arm.
            guarded=_load('_slot_guarded_frozen',patched_path)
            emission_guard=_run_arm(runtime,guarded,inherited_rows=8,drop_milk=True)
        finally:
            try:sys.path.remove(str(lab))
            except ValueError:pass
    return {
        'schema':'titan-v3-cross-product-slot-active-consumer-witness-v1',
        'operation':materialize.OPERATION,
        'source_inputs':receipt['inputs'],
        'patched_git_blob':receipt['patched_git_blob'],
        'runtime_binding':receipt['runtime_binding'],
        'predecessor':predecessor,
        'successor':successor,
        'emission_guard':emission_guard,
        'verdicts':{
            'predecessor_detached':(
                predecessor['chosen_item']=='MILK'
                and predecessor['emitted_products']==['CARROT']),
            'successor_rejects_collision':(
                successor['chosen_item'] is None
                and successor['emitted_products']==['CARROT']),
            'emission_guard_restores_incumbent':(
                emission_guard['chosen_item'] is None
                and emission_guard['emitted_products']==['CARROT']
                and bool((emission_guard['selection_emission'] or {}).get('fallback'))
                and not emission_guard['milk_planned_after']),
        },
    }


def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument('--lab',type=Path,required=True)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    text=json.dumps(build_witness(args.lab),sort_keys=True,indent=2)+'\n'
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(text,encoding='utf-8')
    else:print(text,end='')
    return 0


if __name__=='__main__':
    raise SystemExit(main())
