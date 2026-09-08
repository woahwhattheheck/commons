# SPDX-License-Identifier: Apache-2.0
"""Actual frozen-SELL/official-engine ordered-transfer regression checks.

Uses an existing source checkout and engine cache. Constructs explicit states;
no seeded games or hosted policy strength are measured by these checks.
"""
from __future__ import annotations
import argparse, ast, copy, hashlib, importlib.util, json, random, sys, types, unittest
from pathlib import Path
F = S = E = ENGINE = None
COUNTS={'interpreter_transitions':0,'native_unit_transitions':0,'profile_plan_pairs':0}
RECEIPTS=[]


def load_file(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module
    exec(compile(path.read_bytes(),str(path),'exec'),module.__dict__)
    return module


def fixture(seat=0,reverse=False,operation='DROP',stock=90,capacity=100,terminal=False):
    farm={'farmer':[4,4],'hands':[[4,4]],'hires_today':1,'money':1000.0,
          'unlocked_quadrants':['NW'],'tiles':[[None]*10 for _ in range(10)]}
    private={'shed':{'WHEAT':stock,'CARROT':10},'seeds':{},
             'inventories':[{}, {'MILK':10}] if reverse else [{'MILK':10},{}]}
    market={'inventory':{p:10000 for p in ENGINE.PRODUCTS},'prices':{}}
    ENGINE._refresh_prices(market)
    obs={'step':8,'day':0,'hour':8,'player':seat,'farms':[copy.deepcopy(farm),copy.deepcopy(farm)],
         'private':private,'market':market,'town':{'unlocked_shops':['PET_CAFE']}}
    cfg={'boardSize':10,'turnsPerDay':24,'shedCapacity':capacity,'episodeSteps':11 if terminal else 720,
         'maxMarketOrdersPerTurn':10,'farmHandCostMult':1}
    drop=['DROP'] if operation=='DROP' else ['PLACE','MILK',10]
    actions=[['PICKUP','WHEAT',10],drop] if reverse else [drop,['PICKUP','WHEAT',10]]
    future={'farmer':actions[0],'hands':[actions[1]],'market':[]}
    selected={'farmer':['PASS'],'hands':[['PASS']],'market':[['SELL','CARROT',10]]}
    return obs,cfg,selected,future


def actor_for(future,legacy=False):
    actor=F.FrozenSelected()
    route=[{'farmer':['PASS'],'hands':[['PASS']],'market':[]} for _ in range(720)]
    route[9]=copy.deepcopy(future);actor.controller.R={actor.controller.cur:route}
    if legacy:
        actor.receipt_profile=types.MethodType(S.SellScheduler.receipt_profile,actor)
    return actor


def state_from(obs):
    # All shared public objects are shared exactly as in the interpreter.
    farms=copy.deepcopy(obs['farms']);market=copy.deepcopy(obs['market']);town=copy.deepcopy(obs['town'])
    state=[]
    for seat in (0,1):
        private=copy.deepcopy(obs['private']) if seat==obs['player'] else {'shed':{},'seeds':{},'inventories':[{},{}]}
        state.append(E.Struct(observation=E.Struct(step=8,day=0,hour=8,player=seat,
                        farms=farms,market=market,town=town,private=private),
                              action={},status='ACTIVE',reward=0.0))
    return state


def transition(state,cfg,step,seat,action):
    for player in (0,1):
        state[player].observation.step=step
        state[player].action=copy.deepcopy(action) if player==seat else {'farmer':['PASS'],'hands':[['PASS']],'market':[]}
    env=E.Struct(configuration=E.Struct(cfg),done=False,info={})
    ENGINE.interpreter(state,env);COUNTS['interpreter_transitions']+=1


def evaluate(case,legacy=False):
    obs,cfg,selected,future=copy.deepcopy(case);seat=obs['player'];actor=actor_for(future,legacy)
    out=actor.transform(obs,cfg,selected)
    diag=copy.deepcopy(actor.diagnostics)
    state=state_from(obs);transition(state,cfg,8,seat,out)
    at9=copy.deepcopy(dict(state[seat].observation));at9['step']=9
    final_action=actor.transform(at9,cfg,future) if cfg['episodeSteps']==11 else future
    transition(state,cfg,9,seat,final_action)
    private=state[seat].observation.private
    result={'seat':seat,'legacy':legacy,'first_action':out,'last_action':final_action,
            'private':copy.deepcopy(private),'own_cash':state[0].observation.farms[seat]['money'],
            'rival_cash':state[0].observation.farms[1-seat]['money'],
            'status':state[seat].status,'reward':state[seat].reward,'chosen':diag.get('chosen')}
    RECEIPTS.append(copy.deepcopy(result));return result


class FrozenOrderedCapacityTests(unittest.TestCase):
    def test_drop_then_pickup_keeps_full_deposit_both_seats(self):
        for seat in (0,1):
            with self.subTest(seat=seat):
                actual=evaluate(fixture(seat));self.assertEqual(actual['first_action']['market'],[['SELL','CARROT',10]])
                self.assertEqual(actual['private']['shed']['MILK'],10)

    def test_original_discriminator_is_retained(self):
        for seat in (0,1):
            actual=evaluate(fixture(seat),legacy=True)
            self.assertEqual(actual['first_action']['market'],[['SELL','CARROT',1]])
            self.assertEqual(actual['private']['shed']['MILK'],1)
            self.assertEqual(actual['chosen']['worst_relative_gain'],17)

    def test_reversed_order_remains_delay_eligible(self):
        for seat in (0,1):
            actual=evaluate(fixture(seat,reverse=True))
            self.assertEqual(actual['first_action']['market'],[['SELL','CARROT',1]])
            self.assertEqual(actual['private']['shed']['MILK'],10)

    def test_place_requires_its_own_earlier_space(self):
        for seat in (0,1):
            actual=evaluate(fixture(seat,operation='PLACE'))
            self.assertEqual(actual['first_action']['market'],[['SELL','CARROT',10]])
            self.assertEqual(actual['private']['shed']['MILK'],10)
            self.assertEqual(actual['private']['inventories'][0],{})

    def test_unsafe_plan_is_rejected_before_future_sale(self):
        case=fixture();obs,cfg,base,future=case;actor=actor_for(future)
        farm,private=S.post_units(obs,base,cfg)
        fn=actor.receipt_profile(obs,base,farm,private,9,'CARROT',cfg)
        self.assertFalse(fn([(8,1),(9,9)]))

    def test_reversed_order_capacity_certificate_accepts(self):
        obs,cfg,base,future=fixture(reverse=True);actor=actor_for(future)
        fn=actor.receipt_profile(obs,base,*S.post_units(obs,base,cfg),9,'CARROT',cfg)
        self.assertTrue(fn([(8,1),(9,9)]))

    def test_terminal_economic_effect_uses_actual_rewards(self):
        for seat in (0,1):
            case=fixture(seat,terminal=True)
            original=evaluate(case,legacy=True);fixed=evaluate(case)
            self.assertEqual(original['status'],'DONE');self.assertEqual(fixed['status'],'DONE')
            self.assertEqual(original['rival_cash'],fixed['rival_cash'])
            self.assertGreater(fixed['reward'],original['reward'])
            self.assertEqual(fixed['reward'],fixed['own_cash'])
            # Each result was produced by both actual interpreter steps.

    def test_no_pressure_is_unchanged(self):
        for reverse in (False,True):
            case=fixture(reverse=reverse,stock=50)
            actual=evaluate(case);original=evaluate(case,legacy=True)
            for key in ('first_action','last_action','private','own_cash','rival_cash'):
                self.assertEqual(actual[key],original[key])

    def test_existing_one_unit_headroom_is_preserved(self):
        obs,cfg,base,future=fixture(reverse=True);actor=actor_for(future)
        fn=actor.receipt_profile(obs,base,*S.post_units(obs,base,cfg),9,'CARROT',cfg)
        self.assertFalse(fn([(8,0)]));self.assertTrue(fn([(8,1)]))

    def test_current_post_units_are_not_applied_again(self):
        obs,cfg,base,future=fixture();base['farmer']=['DROP']
        actor=actor_for(future)
        pair=S.post_units(obs,base,cfg)
        self.assertEqual(pair[1]['inventories'][0],{})
        before=copy.deepcopy(pair)
        actor.receipt_profile(obs,base,*pair,9,'CARROT',cfg)
        self.assertEqual(pair,before)

    def test_inputs_and_route_are_not_mutated(self):
        obs,cfg,base,future=fixture();actor=actor_for(future)
        pair=S.post_units(obs,base,cfg)
        before=copy.deepcopy((obs,cfg,base,pair,actor.controller.R))
        fn=actor.receipt_profile(obs,base,*pair,16,'CARROT',cfg)
        for a in range(11):fn([(8,a),(16,10-a)])
        self.assertEqual((obs,cfg,base,pair,actor.controller.R),before)

    def test_generated_new_certificates_never_weaken_old(self):
        rng=random.Random(41036)
        for _ in range(100):
            obs,cfg,base,future=fixture(reverse=bool(rng.randrange(2)),stock=rng.randrange(40,101))
            actor=actor_for(future);pair=S.post_units(obs,base,cfg)
            new=actor.receipt_profile(obs,base,*pair,9,'CARROT',cfg)
            old=S.SellScheduler.receipt_profile(actor,obs,base,*pair,9,'CARROT',cfg)
            for a in range(11):
                plan=[(8,a),(9,10-a)];x=new(plan);y=old(plan)
                self.assertFalse(x and not y);COUNTS['profile_plan_pairs']+=1

    def test_monotonic_transfers_keep_original_results(self):
        for action in (['PASS'],['DROP'],['PLACE','MILK',4],['PICKUP','WHEAT',3],['NORTH']):
            obs,cfg,base,future=fixture(stock=70);future['farmer']=action;future['hands']=[['PASS']]
            actor=actor_for(future);pair=S.post_units(obs,base,cfg)
            a=actor.receipt_profile(obs,base,*pair,16,'CARROT',cfg)
            b=S.SellScheduler.receipt_profile(actor,obs,base,*pair,16,'CARROT',cfg)
            for q in range(11):
                plan=[(8,q),(16,10-q)];self.assertEqual(a(plan),b(plan));COUNTS['profile_plan_pairs']+=1

    def test_nonnumeric_or_duplicate_date_semantics_unchanged_without_pressure(self):
        obs,cfg,base,future=fixture(stock=40);actor=actor_for(future);pair=S.post_units(obs,base,cfg)
        a=actor.receipt_profile(obs,base,*pair,16,'CARROT',cfg)
        b=S.SellScheduler.receipt_profile(actor,obs,base,*pair,16,'CARROT',cfg)
        for plan in ([('unrelated','ignored')],[(8,1),(8,3)],[(8,-2),(9,10)],[],[(8,2.5)]):
            self.assertEqual(a(plan),b(plan))

    def test_unit_primitive_is_the_pinned_engine_body(self):
        left=ast.parse(Path(S.m.__file__).read_text());right=ast.parse(Path(ENGINE.__file__).read_text())
        def body(tree):return ast.dump(next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_apply_unit_action'))
        self.assertEqual(body(left),body(right))


def main():
    global F,S,E,ENGINE
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime',type=Path,required=True)
    parser.add_argument('--evaluator',type=Path,required=True)
    parser.add_argument('--engine-cache',type=Path,required=True)
    parser.add_argument('--report',type=Path)
    parser.add_argument('--original-control',action='store_true')
    args=parser.parse_args();sys.path.insert(0,str(args.runtime.resolve()))
    S=load_file('scheduler',args.runtime/'scheduler.py');F=load_file('frozen_selected',args.runtime/'frozen_selected.py')
    E=load_file('capacity_existing_evaluator',args.evaluator)
    ENGINE,hashes=E.get_engine(args.engine_cache,prepare=False)
    if args.original_control:F.FrozenSelected.receipt_profile=S.SellScheduler.receipt_profile
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(FrozenOrderedCapacityTests)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    report={'schema':'titan.frozen-ordered-capacity.v1','tests':result.testsRun,'success':result.wasSuccessful(),
            'failures':[{'test':t.id(),'traceback':s} for t,s in result.failures],
            'errors':[{'test':t.id(),'traceback':s} for t,s in result.errors],
            'counts':COUNTS,'receipts':RECEIPTS,'source_sha256':{n:hashlib.sha256((args.runtime/n).read_bytes()).hexdigest() for n in ('scheduler.py','frozen_selected.py','mechanics.py')},
            'engine_sha256':hashes,'engine_ref':E.ENGINE_REF,'new_games':0,'seeds_consumed':[]}
    if args.report:args.report.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('tests','success','counts','new_games')}))
    return int(not result.wasSuccessful())
if __name__=='__main__':raise SystemExit(main())
