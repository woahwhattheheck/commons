# SPDX-License-Identifier: Apache-2.0
import copy
import unittest

from realized_hire_payback import certify_realized_hire_payback

PRODUCTS=["WHEAT","CARROT","TOMATO","STRAWBERRY","MELON","EGG","MILK","WOOL","FERTILIZER"]

def state(*,yield_units=0,shed=None,main_inventory=None,hands=0,crop="CARROT"):
    n=4
    tiles=[[None for _ in range(n)] for _ in range(n)]
    if yield_units:
        tiles[1][2]={"kind":"PLANT","crop":crop,"planted_day":0,"watered_today":True,
                     "consecutive_unwatered":0,"yield_units":yield_units,
                     "max_lifespan_step":999,"fertilized_until_day":-1}
    farm={"money":100,"tiles":tiles,"farmer":[1,1],"hands":[[2,1] for _ in range(hands)],
          "unlocked_quadrants":["NW"],"hires_today":4}
    p={"shed":{x:0 for x in PRODUCTS},"seeds":{},
       "inventories":[copy.deepcopy(main_inventory or {})]+[{} for _ in range(hands)]}
    for k,v in (shed or {}).items():p['shed'][k]=v
    return farm,p

def rows(now=50,end=71):
    base={"farmer":["PASS"],"hands":[],"market":[]}
    return [copy.deepcopy(base) for _ in range(end+1)]

def cfg(**patch):
    out={"boardSize":4,"turnsPerDay":24,"episodeSteps":720,
         "maxMarketOrdersPerTurn":10,"shedCapacity":100}
    out.update(patch);return out

def market(inventory=None):
    values={product:10000 for product in PRODUCTS}
    values["CARROT"]=12000
    values.update(inventory or {})
    return {"inventory":values,"prices":{product:1 for product in PRODUCTS}}

def run(farm,private,route,*,cost=5,now=50,baseline=None,candidate=None,config=None,
        market_state=None,shops=None,decisions=()):
    return certify_realized_hire_payback(
        farm=farm,private=private,market=market() if market_state is None else market_state,
        unlocked_shops=[] if shops is None else shops,route=route,
        baseline_market=[] if baseline is None else baseline,
        candidate_market=[["HIRE"]] if candidate is None else candidate,
        inserted_index=0,hire_cost=cost,current_step=now,
        configuration=cfg() if config is None else config,decision_steps=decisions)

class PaybackTests(unittest.TestCase):
    def productive_route(self,units=6):
        f,p=state(yield_units=units);r=rows()
        r[51]['hands']=[["HARVEST"]]
        r[52]['hands']=[["DROP"]]
        r[52]['market']=[["SELL","CARROT",units]]
        return f,p,r

    def test_exact_floor_coverage_admits(self):
        f,p,r=self.productive_route(5)
        got=run(f,p,r,cost=5)
        self.assertTrue(got['admit'])
        self.assertEqual(got['reason'],'realized_payback_covers_hire')
        self.assertEqual(got['realized_cash_floor'],5)
        self.assertEqual(got['coverage_margin'],0)

    def test_six_units_cover_five_with_margin(self):
        f,p,r=self.productive_route(6)
        got=run(f,p,r,cost=5)
        self.assertTrue(got['admit'])
        self.assertEqual(got['incremental_sale_units'],{'CARROT':6})
        self.assertEqual(got['coverage_margin'],1)

    def test_published_flat_tax_shape_is_blocked_without_realized_sale(self):
        f,p,r=self.productive_route(6)
        r[52]['market']=[]
        got=run(f,p,r,cost=5)
        self.assertFalse(got['admit'])
        self.assertEqual(got['reason'],'insufficient_realized_payback')
        self.assertEqual(got['realized_cash_floor'],0)

    def test_four_units_do_not_cover_five_dollar_hire(self):
        f,p,r=self.productive_route(4)
        got=run(f,p,r,cost=5)
        self.assertFalse(got['admit'])
        self.assertEqual(got['realized_cash_floor'],4)

    def test_newly_unlocked_noop_is_rejected_before_incumbent_laundering(self):
        f,p=state();r=rows()
        f['tiles'][1][1]={"kind":"PLANT","crop":"WHEAT","planted_day":0,
                          "watered_today":True,"consecutive_unwatered":0,
                          "yield_units":6,"max_lifespan_step":999,
                          "fertilized_until_day":-1}
        # Main farmer realizes six units in both arms; the newly unlocked hand
        # tries to HARVEST an empty spawn tile and must not borrow that output.
        r[51]['farmer']=["HARVEST"];r[51]['hands']=[["HARVEST"]]
        r[52]['farmer']=["DROP"];r[52]['market']=[["SELL","WHEAT",6]]
        got=run(f,p,r)
        self.assertFalse(got['admit'])
        self.assertEqual(got['reason'],'new_hand_first_action_noop')

    def test_unrelated_incumbent_sales_do_not_count(self):
        f,p=state();r=rows()
        f['tiles'][1][1]={"kind":"PLANT","crop":"WHEAT","planted_day":0,
                          "watered_today":True,"consecutive_unwatered":0,
                          "yield_units":6,"max_lifespan_step":999,
                          "fertilized_until_day":-1}
        r[51]['farmer']=["HARVEST"];r[51]['hands']=[["EAST"]]
        r[52]['farmer']=["DROP"];r[52]['hands']=[["WEST"]]
        r[52]['market']=[["SELL","WHEAT",6]]
        got=run(f,p,r)
        self.assertFalse(got['admit'])
        self.assertEqual(got['reason'],'insufficient_realized_payback')
        self.assertEqual(got['control_sales']['WHEAT'],6)
        self.assertEqual(got['candidate_sales']['WHEAT'],6)

    def test_per_product_displacement_is_hard_veto(self):
        f,p=state(yield_units=6,main_inventory={'MELON':1});r=rows()
        r[51]['hands']=[["HARVEST"]]
        r[52]['hands']=[["DROP"]]
        r[53]['farmer']=["DROP"];r[53]['hands']=[["PASS"]]
        r[54]['hands']=[["PASS"]]
        r[54]['market']=[["SELL","MELON",1],["SELL","WHEAT",6]]
        got=run(f,p,r,config=cfg(shedCapacity=6))
        self.assertFalse(got['admit'])
        self.assertEqual(got['reason'],'step_sale_displacement')
        self.assertEqual(got['sale_regressions'],{'MELON':-1})

    def test_incremental_wheat_sale_rejects_hidden_rival_buy_price_path(self):
        f,p=state(yield_units=5,crop="WHEAT");r=rows()
        r[51]['hands']=[["HARVEST"]]
        r[52]['hands']=[["DROP"]]
        r[52]['market']=[["SELL","WHEAT",5]]
        got=run(f,p,r,market_state=market({"WHEAT":999999}))
        self.assertFalse(got['admit'])
        self.assertEqual(got['reason'],'incremental_sale_not_public_state_neutral')
        self.assertEqual(got['rejected_sale_proof']['reason'],
                         'rival_buy_can_raise_price')

    def test_nonfloor_incremental_sale_rejects_public_price_externality(self):
        f,p,r=self.productive_route(5)
        got=run(f,p,r,market_state=market({"CARROT":10000}))
        self.assertFalse(got['admit'])
        self.assertEqual(got['reason'],'incremental_sale_not_public_state_neutral')
        self.assertEqual(got['rejected_sale_proof']['reason'],
                         'sale_not_guaranteed_at_price_floor')

    def test_town_absorption_is_charged_before_future_sale_quote(self):
        f,p,r=self.productive_route(5)
        # PET_CAFE consumes two CARROT at every shop interval. Force intervals
        # each turn so the lower inventory bound rises off the floor by step 52.
        got=run(f,p,r,market_state=market({"CARROT":10845}),
                shops=["PET_CAFE"],
                config=cfg(townShopSellInterval=1,townCenterSellInterval=999))
        self.assertFalse(got['admit'])
        self.assertEqual(got['reason'],'incremental_sale_not_public_state_neutral')
        proof=got['rejected_sale_proof']
        self.assertEqual(proof['minimum_inventory_before_sale'],10841)
        self.assertGreater(proof['maximum_possible_price'],1)

    def test_route_checkpoint_inside_hired_lifetime_fails_closed(self):
        f,p,r=self.productive_route(5)
        got=run(f,p,r,decisions=(52,))
        self.assertFalse(got['admit'])
        self.assertEqual(got['reason'],'route_decision_checkpoint_in_horizon')

    def test_current_buy_dependency_fails_closed(self):
        f,p,r=self.productive_route(6)
        got=run(f,p,r,baseline=[[],["BUY_PRODUCT","WHEAT",1]],
                candidate=[["HIRE"],["BUY_PRODUCT","WHEAT",1]])
        self.assertFalse(got['admit'])
        self.assertEqual(got['reason'],'unsupported_market_dependency')

    def test_future_buy_dependency_fails_closed(self):
        f,p,r=self.productive_route(6)
        r[52]['market']=[["BUY_PRODUCT","WHEAT",1]]
        got=run(f,p,r)
        self.assertFalse(got['admit'])
        self.assertEqual(got['reason'],'unsupported_market_dependency')

    def test_resource_consuming_new_hand_action_fails_closed(self):
        f,p=state();r=rows();r[51]['hands']=[["FEED"]]
        got=run(f,p,r)
        self.assertFalse(got['admit'])
        self.assertEqual(got['reason'],'unsupported_new_hand_action')

    def test_current_step_decay_precedes_first_hired_action(self):
        f,p,r=self.productive_route(5)
        plant=f['tiles'][1][2]
        plant['max_lifespan_step']=50
        # Official current-step decay reduces 5 -> 4 before step 51 HARVEST,
        # so the represented sale cannot cover the exact $5 HIRE.
        got=run(f,p,r,cost=5,now=50)
        self.assertFalse(got['admit'])
        self.assertEqual(got['reason'],'insufficient_realized_payback')
        self.assertEqual(got['realized_cash_floor'],4)

    def test_hire_at_day_close_expires_before_action(self):
        f,p=state();r=rows(now=71,end=72);r[72]['hands']=[["EAST"]]
        got=run(f,p,r,now=71)
        self.assertFalse(got['admit'])
        self.assertEqual(got['reason'],'hire_expires_before_first_action')

    def test_candidate_must_be_exact_single_hire_delta(self):
        f,p,r=self.productive_route(6)
        got=run(f,p,r,baseline=[],candidate=[["HIRE"],["SELL","WHEAT",1]])
        self.assertFalse(got['admit'])
        self.assertEqual(got['reason'],'market_delta_not_single_append')

    def test_inputs_are_not_mutated_and_receipt_is_deterministic(self):
        f,p,r=self.productive_route(6);before=copy.deepcopy((f,p,r))
        a=run(f,p,r);b=run(f,p,r)
        self.assertEqual((f,p,r),before)
        self.assertEqual(a,b)
        self.assertTrue(a['admit'])


    def test_hire_cost_must_match_official_fibonacci_cost(self):
        f,p,r=self.productive_route(6)
        got=run(f,p,r,cost=4)
        self.assertFalse(got['admit'])
        self.assertEqual(got['reason'],'hire_cost_mismatch')

    def test_bool_hire_cost_is_rejected(self):
        f,p,r=self.productive_route(6)
        got=run(f,p,r,cost=True)
        self.assertFalse(got['admit'])
        self.assertEqual(got['reason'],'invalid_integer')

if __name__=='__main__':unittest.main(verbosity=2)
