import copy, importlib.util, pathlib

spec=importlib.util.spec_from_file_location('rh', pathlib.Path(__file__).parent/'reference'/'titan-current'/'redundant_hire.py')
rh=importlib.util.module_from_spec(spec);spec.loader.exec_module(rh)

class M:
    PRODUCTS=['WHEAT','EGG']
    CROPS={'WHEAT':{'first_yield_day':1}}
    ANIMALS={'GOOSE':{'product':'EGG'}}
    @staticmethod
    def _apply_unit_action(farm,private,i,a,board,day,day_len,cap):
        return None
    @staticmethod
    def _hire_cost(n,mult): return 5*mult
    @staticmethod
    def _do_hire(farm,private,board,mult):
        farm['money']-=5*mult;farm['hires_today']+=1;farm['hands'].append([4,4]);private['inventories'].append({})
    @staticmethod
    def market_price(item,inv,params=None): return (params or {}).get('price',10)


def obs(tile=None, *, price=10, main=(0,0)):
    tiles=[[None for _ in range(10)] for _ in range(10)]
    if tile is not None: tiles[4][6]=copy.deepcopy(tile)
    return {'step':58,'day':2,'hour':10,'player':0,
            'farms':[{'farmer':list(main),'hands':[],'tiles':tiles,'money':100,'hires_today':0},
                     {'farmer':[0,0],'hands':[],'tiles':copy.deepcopy(tiles),'money':100,'hires_today':0}],
            'private':{'shed':{},'inventories':[{}],'seeds':{}},
            'market':{'inventory':{'WHEAT':100,'EGG':100},'params':{'price':price}}}

def route(main_actions=None):
    rows=[]
    for t in range(72):
        row={'farmer':['PASS'],'hands':[],'market':[]}
        if main_actions and t in main_actions: row['farmer']=main_actions[t]
        rows.append(row)
    return rows

CFG={'boardSize':10,'turnsPerDay':24,'episodeSteps':720,'shedCapacity':100,
     'maxMarketOrdersPerTurn':10,'farmHandCostMult':1}
ACTION={'farmer':['PASS'],'hands':[],'market':[['HIRE']]}

def call(o,r):
    return rh.propose_redundant_hires(M,o,CFG,ACTION,route=r,route_id='x',route_switch_steps=[])

def test_truly_unused_hire_is_removed():
    r=route();out,rep=call(obs(),r)
    assert out['market']==[['SELL','WHEAT',0]]
    assert rep['immediate_wage_saving']==5 and rep['completed_jobs']==0
    assert not rep['route_changed']

def test_profitable_complete_harvest_deposit_rejoin_protects_hire():
    r=route();o=obs({'kind':'PLANT','crop':'WHEAT','planted_day':0,'yield_units':1},price=10)
    out,rep=call(o,r)
    assert out['market']==[['HIRE']]
    assert rep['reason']=='productive_detour_protected_hire'
    assert rep['completed_jobs']==1 and rep['wage_payback']==5
    w=rep['productive_detours'][0]
    assert w['target']==[6,4] and w['deposit_step']<72 and w['rejoin']==[4,4]
    program=[r[t]['hands'][0] for t in range(59,72)]
    assert ['HARVEST'] in program and ['DROP'] in program
    p=[4,4]
    for a in program:
        d=rh.MOVES.get(a[0])
        if d:p=[p[0]+d[0],p[1]+d[1]]
    assert p==[4,4]

def test_nominal_value_not_above_wage_does_not_protect():
    r=route();o=obs({'kind':'PLANT','crop':'WHEAT','planted_day':0,'yield_units':1},price=5)
    out,rep=call(o,r)
    assert out['market'][0]==['SELL','WHEAT',0]
    assert rep['completed_jobs']==0

def test_shared_target_reservation_declines_detour():
    r=route({59:['WATER']});o=obs({'kind':'PLANT','crop':'WHEAT','planted_day':0,'yield_units':1},price=10,main=(6,4))
    out,rep=call(o,r)
    assert out['market'][0]==['SELL','WHEAT',0]
    assert rep['completed_jobs']==0

def test_cannot_finish_before_reset_declines_detour():
    o=obs({'kind':'PLANT','crop':'WHEAT','planted_day':0,'yield_units':1},price=50)
    o['step']=69;o['hour']=21
    r=route()
    out,rep=rh.propose_redundant_hires(M,o,CFG,ACTION,route=r,route_id='x',route_switch_steps=[])
    assert out['market'][0]==['SELL','WHEAT',0]
    assert rep['completed_jobs']==0

def test_nonredundant_existing_job_is_never_rewritten():
    r=route();r[59]['hands']=[['HARVEST']]
    out,rep=call(obs(),r)
    assert out['market']==[['HIRE']]
    assert rep['reason']=='no_redundant_trailing_worker'
    assert r[59]['hands']==[['HARVEST']]

def test_one_productive_hire_preserves_contiguous_order_and_removes_later_tail():
    r=route();o=obs({'kind':'PLANT','crop':'WHEAT','planted_day':0,'yield_units':1},price=10)
    action={'farmer':['PASS'],'hands':[],'market':[['HIRE'],['HIRE']]}
    out,rep=rh.propose_redundant_hires(M,o,CFG,action,route=r,route_id='x',route_switch_steps=[])
    assert out['market']==[['HIRE'],['SELL','WHEAT',0]]
    assert rep['protected_workers']==1 and rep['removed_workers']==1
    assert rep['productive_detours'][0]['worker']==1
