# SPDX-License-Identifier: MIT OR CC-BY-4.0
"""Focused primitive comparisons against pinned engine, no games or replay reruns."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import sys
import unittest
import forecast as f
from test_forecast import obs,plant
from forecast_market_mechanics import PRODUCTS, MARKET_PARAMS

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('forecast_existing_eval',HERE.parent/'cloud-eval/evaluate.py')
eval=importlib.util.module_from_spec(spec);spec.loader.exec_module(eval)
engine,_=eval.get_engine(Path(sys.argv[1]))


class EngineCases(unittest.TestCase):
    def test_actual_engine_pricing_defaults_and_override(self):
        params=deepcopy(MARKET_PARAMS);params['TOMATO'].update(base=75,T=80)
        for p in PRODUCTS:
            for n in [-100,9000,9999,10000,10001,11500]:
                for config in [None,params]:
                    self.assertEqual(f.market_price(p,n,config),engine.market_price(p,n,config))

    def test_exact_town_copy_counts_configured_intervals_and_negative_inventory(self):
        for start,end in [(0,1),(216,217),(224,257),(430,601)]:
            for config in [{},{'townShopSellInterval':5,'townCenterSellInterval':7}]:
                o=obs(start,copies=['PIZZA_SHOP','PIZZA_SHOP','FARMERS_MARKET','YARN_STORE'])
                o['market']['inventory']={p:0 for p in PRODUCTS}
                d=f.public_demand(o,config,end)
                state=[eval.Struct(observation=eval.structify(deepcopy(o)))]
                env=eval.Struct(configuration=eval.Struct(config))
                for step in range(start,end):engine._town_consume(env,state,step)
                self.assertEqual(state[0].observation.market.inventory,{p:-n for p,n in d['units'].items()})

    def test_no_future_work_crop_transitions_match_engine(self):
        for tile in [plant(held=0,until=9),plant('TOMATO',0,4,True,11),plant('WHEAT',8,3,False)]:
            o=obs(239,tile);original=deepcopy(o['farms'][0]);cfg=f._config({})
            snapshots,_,_=f._tile_scenario(tile,1,1,original,239,289,cfg,f.SCENARIOS['no_future_work'],0)
            farm=deepcopy(original)
            for step in range(239,290):
                t=farm['tiles'][1][1]
                held=t.get('yield_units',0) if t.get('kind')=='PLANT' else 0
                self.assertEqual(snapshots[step]['held_units'],held)
                engine._decay_plants(farm,step)
                if (step+1)%24==0:engine._daily_refresh_plants(farm,step//24,24)


if __name__=='__main__':
    unittest.main(argv=[sys.argv[0],*sys.argv[2:]])
