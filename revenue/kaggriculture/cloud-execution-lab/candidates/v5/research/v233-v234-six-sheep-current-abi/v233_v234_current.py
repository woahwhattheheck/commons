# SPDX-License-Identifier: Apache-2.0
"""Default-OFF current-ABI recovery of submitted V3.1 V233/V234 six-sheep investment."""
from __future__ import annotations
import copy, hashlib, json
from dataclasses import dataclass, field
from typing import Any

SUBMITTED_V31_SOURCE_COMMIT="a90d888f03987ef0b35cfd20ec3519c6144db08a"
SUBMITTED_V31_ARCHIVE_SHA256="5db3921f85efbc7596e5a1e7e198fc5f4644ceea43d8e8323c74ded7b4ba4361"
SUBMITTED_R03_GIT_BLOB="182e0b7b3f0cc1125967dc092b2c118601b19084"
FULL_ROUTE_SCHEMA="titan-v5-current-full-route-snapshot-v1"
ROUTE_SOURCE="committed_producer_route.R[route_id]"
TARGETS=tuple((x,y) for y in (5,6) for x in range(5,8)); ACCESS=((4,4),(5,4),(4,5),(5,5))
ANIMALS=("COW","SHEEP","GOOSE"); MAX_ORDERS=10; SHED_CAPACITY=100
BUY_PRICES={"SHEEP":500,"COW":400,"GOOSE":300}; SEED_PRICES={"WHEAT":10,"CARROT":20,"TOMATO":50,"STRAWBERRY":100,"MELON":80}
TELEMETRY=("commit_requests","committed","hire_requests","workers_confirmed","hire_shortfalls","purchase_shortfalls","budget_declines","capacity_declines","feed_buy_requests","wool_harvested","fertilizer_collected","extra_wool_sales","extra_fertilizer_sales","rescue_feed_requests","route_declines")

def _int(v): return type(v) is int
def _nn(v): return _int(v) and v>=0
def _identity(v): return copy.deepcopy(v)
def _canon(v):
    try:
        s=json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True,allow_nan=False)
        return s if json.loads(s)==v else None
    except (TypeError,ValueError,json.JSONDecodeError): return None

def _route(snapshot,step):
    if snapshot is None or getattr(snapshot,"schema",None)!=FULL_ROUTE_SCHEMA or getattr(snapshot,"route_source",None)!=ROUTE_SOURCE or getattr(snapshot,"current_step",None)!=step:return None
    raw=getattr(snapshot,"route_json",None); digest=getattr(snapshot,"route_sha256",None)
    if type(raw) is not str or type(digest) is not str or hashlib.sha256(raw.encode("ascii")).hexdigest()!=digest:return None
    try:r=json.loads(raw)
    except json.JSONDecodeError:return None
    return r if isinstance(r,list) and len(r)==getattr(snapshot,"route_length",None) and all(isinstance(a,dict) for a in r) else None

def _fingerprint(obs,selected,snapshot):
    raw=_canon({"o":obs,"s":selected,"r":None if snapshot is None else [getattr(snapshot,k,None) for k in ("schema","route_source","route_id","current_step","route_sha256","route_length")]})
    return None if raw is None else hashlib.sha256(raw.encode("ascii")).hexdigest()

def _shape(obs,selected):
    if not isinstance(obs,dict) or not isinstance(selected,dict) or not _nn(obs.get("step")) or obs.get("player") not in (0,1):return False
    farms=obs.get("farms"); private=obs.get("private"); market=obs.get("market"); town=obs.get("town")
    if not isinstance(farms,list) or obs["player"]>=len(farms) or not isinstance(private,dict) or not isinstance(market,dict) or not isinstance(town,dict):return False
    farm=farms[obs["player"]]; hands=farm.get("hands") if isinstance(farm,dict) else None; inv=private.get("inventories")
    if not isinstance(hands,list) or not isinstance(inv,list) or len(inv)!=len(hands)+1 or any(not isinstance(x,dict) for x in inv):return False
    if not isinstance(farm.get("tiles"),list) or len(farm["tiles"])!=10 or any(not isinstance(row,list) or len(row)!=10 for row in farm["tiles"]):return False
    if not isinstance(farm.get("unlocked_quadrants"),list) or not _nn(farm.get("money",0)) or not _nn(farm.get("hires_today",0)):return False
    if not isinstance(private.get("shed"),dict) or not isinstance(market.get("prices"),dict) or not isinstance(town.get("unlocked_shops"),list):return False
    if not isinstance(selected.get("farmer"),list) or not isinstance(selected.get("hands"),list) or len(selected["hands"])!=len(hands):return False
    orders=selected.get("market"); return isinstance(orders,list) and len(orders)<=MAX_ORDERS

def _future_conflict(route):
    for a in route[12*24:min(len(route),30*24)]:
        orders=a.get("market") or []
        if any(o and (o[0]=="BUY_LAND" or o[:2]==["BUY_ANIMAL","SHEEP"]) for o in orders):return True
        cmds=[a.get("farmer") or ["PASS"],*(a.get("hands") or [])]
        if any(c and c[0] in ("PICKUP","PLACE") and len(c)>1 and c[1]=="SHEEP" for c in cmds):return True
    return False

def _day(route,day): return route[day*24:min((day+1)*24,len(route))]
def _max_hands(rows):
    try:return max(len(a["hands"]) for a in rows)
    except (KeyError,TypeError,ValueError):return None

def _fib(n):
    a=b=1
    for _ in range(n):a,b=b,a+b
    return a

def _beside(p):return p[0] in (4,5) and p[1] in (4,5)
def _walk(p,t):
    if p[0]!=t[0]:return ["EAST" if p[0]<t[0] else "WEST"]
    if p[1]!=t[1]:return ["SOUTH" if p[1]<t[1] else "NORTH"]
    return None

def _stock(obs,act):
    farm=obs["farms"][obs["player"]]; private=obs["private"]; stock={k:int(v) for k,v in private["shed"].items() if _nn(v)}; total=sum(stock.values())
    positions=[tuple(farm["farmer"]),*(tuple(p) for p in farm["hands"])]; cmds=[act["farmer"],*act["hands"]]
    for i,c in enumerate(cmds):
        if i>=len(positions) or not _beside(positions[i]) or not c:continue
        inv=private["inventories"][i]; op=c[0]
        if op=="PICKUP" and len(c)>1:
            q=c[2] if len(c)>2 and _nn(c[2]) else 1; take=min(stock.get(c[1],0),q); stock[c[1]]=stock.get(c[1],0)-take; total-=take
        elif op=="DROP":
            for item,held in inv.items():
                if not _nn(held):continue
                add=min(held,max(0,SHED_CAPACITY-total)); stock[item]=stock.get(item,0)+add; total+=add
    return stock

def _state():return {"last":-1,"day":-1,"committed":False,"pending":None,"workers":{},"work":{},"credit":{"WOOL":0,"FERTILIZER":0},"rescue":0,"route_id":None,"route_sha256":None,"route":None,"telemetry":{k:0 for k in TELEMETRY}}

@dataclass
class V233V234SixSheepCurrentABI:
    enabled:bool=False
    _states:dict[int,dict[str,Any]]=field(default_factory=dict)
    _retry:dict[int,dict[str,Any]]=field(default_factory=dict)
    def __post_init__(self):
        if type(self.enabled) is not bool:raise TypeError("enabled must be exact bool")
    def telemetry(self,seat=0):return copy.deepcopy(self._states.get(seat,{}).get("telemetry",{}))
    def transform(self,obs,selected,*,route_snapshot=None):
        if not self.enabled or not _shape(obs,selected):return _identity(selected)
        route=_route(route_snapshot,obs["step"]); fp=_fingerprint(obs,selected,route_snapshot)
        if route is None or fp is None:return _identity(selected)
        seat=obs["player"]; step=obs["step"]; tx=self._retry.get(seat)
        if tx and step==tx["step"]:
            if fp==tx["fp"]:return copy.deepcopy(tx["out"])
            self._states[seat]=copy.deepcopy(tx["pre"])
        elif tx and step<tx["step"]:self._states.pop(seat,None); self._retry.pop(seat,None)
        st=self._states.setdefault(seat,_state())
        if step<st["last"]:st=self._states[seat]=_state()
        pre=copy.deepcopy(st); out=self._apply(obs,selected,route_snapshot,route,st)
        self._retry[seat]={"step":step,"fp":fp,"pre":pre,"out":copy.deepcopy(out)}; return out
    def _apply(self,obs,selected,snapshot,live,st):
        step=obs["step"]; day=step//24; hour=step%24; st["last"]=step
        if not 12<=day<=29:return _identity(selected)
        if st["route"] is None:
            if day!=12 or _future_conflict(live):st["telemetry"]["route_declines"]+=1; return _identity(selected)
            st["route"]=copy.deepcopy(live); st["route_id"]=snapshot.route_id; st["route_sha256"]=snapshot.route_sha256
        elif snapshot.route_id!=st["route_id"] or snapshot.route_sha256!=st["route_sha256"]:
            st["telemetry"]["route_declines"]+=1; return _identity(selected)
        route=st["route"]; farm=obs["farms"][obs["player"]]; private=obs["private"]
        if st["day"]!=day:st["day"]=day; st["workers"]={}; st["work"]={}; st["rescue"]=0
        for actor,prev in list(st["work"].items()):
            if prev["step"]!=step-1 or actor>=len(private["inventories"]):continue
            item={"HARVEST":"WOOL","COLLECT_FERTILIZER":"FERTILIZER"}.get(prev["cmd"][0])
            if item:
                gain=max(0,private["inventories"][actor].get(item,0)-prev["inv"].get(item,0)); st["credit"][item]+=gain; st["telemetry"]["wool_harvested" if item=="WOOL" else "fertilizer_collected"]+=gain
        pending=st.pop("pending",None)
        if pending:
            funded="SE" in farm["unlocked_quadrants"] and (not pending["initial"] or private["shed"].get("SHEEP",0)>=6)
            if not funded:st["telemetry"]["purchase_shortfalls"]+=1
            elif len(farm["hands"])<pending["first"]+1:st["telemetry"]["hire_shortfalls"]+=1
            else:
                for i in range(2):st["workers"][pending["first"]+i]=[(x,5+i) for x in range(5,8)]
                st["telemetry"]["workers_confirmed"]+=2
                if pending["initial"]:st["committed"]=True; st["telemetry"]["committed"]+=1
        action=self._request(obs,selected,st,route,day,hour)
        if not st["committed"]:return action
        result=copy.deepcopy(action); cmds=[result["farmer"],*result["hands"]]; st["work"]={}
        for actor,targets in st["workers"].items():
            if actor>=len(cmds) or actor>=len(private["inventories"]):continue
            cmd=self._worker(obs,actor,targets); cmds[actor]=cmd; st["work"][actor]={"step":step,"cmd":copy.deepcopy(cmd),"inv":dict(private["inventories"][actor])}
        result["farmer"],result["hands"]=cmds[0],cmds[1:]; result=self._rescue(obs,result,st); stock=_stock(obs,result)
        for item in ("WOOL","FERTILIZER"):
            sold=sum(o[2] for o in result["market"] if len(o)>2 and o[:2]==["SELL",item] and _nn(o[2])); q=min(st["credit"][item],max(0,stock.get(item,0)-sold))
            if q and len(result["market"])<MAX_ORDERS:result["market"].append(["SELL",item,q]); st["credit"][item]-=q; st["telemetry"]["extra_wool_sales" if item=="WOOL" else "extra_fertilizer_sales"]+=q
        return result
    def _eligible(self,obs,route):
        farm=obs["farms"][obs["player"]]; p=obs["market"]["prices"]; private=obs["private"]
        return set(farm["unlocked_quadrants"])=={"NW","NE","SW"} and obs["town"]["unlocked_shops"].count("YARN_STORE")>=2 and p["WOOL"]>=220 and p["WHEAT"]<=45 and all(farm["tiles"][y][x]=="LOCKED" for x,y in TARGETS) and not private["shed"].get("SHEEP",0) and not any(i.get("SHEEP",0) for i in private["inventories"]) and not _future_conflict(route)
    def _request(self,obs,selected,st,route,day,hour):
        if hour>(2 if st["committed"] else 1) or st.get("requested_day")==day:return _identity(selected)
        if not st["committed"] and (day!=12 or not self._eligible(obs,route)):return _identity(selected)
        planned=_day(route,day); expected=_max_hands(planned); farm=obs["farms"][obs["player"]]
        if expected is None or any(o and o[0]=="HIRE" for a in planned[hour+1:] for o in (a.get("market") or [])):return _identity(selected)
        market=selected["market"]; parent_hires=sum(bool(o) and o[0]=="HIRE" for o in market)
        if len(farm["hands"])+parent_hires!=expected:return _identity(selected)
        initial=not st["committed"]; extra=([['BUY_LAND'],['BUY_ANIMAL','SHEEP',6]] if initial else [])+[['BUY_PRODUCT','WHEAT',6],['HIRE'],['HIRE']]
        if len(market)+len(extra)>MAX_ORDERS:return _identity(selected)
        stock=_stock(obs,selected); incoming=6+(6 if initial else 0); quote=obs["market"]["prices"]["WHEAT"]; budget=7000*int(initial)+6*(quote+10); start=farm["hires_today"]+parent_hires; budget+=_fib(start)+_fib(start+1)
        for o in market:
            if o[0]=="BUY_LAND":return _identity(selected)
            if len(o)<3 or not _nn(o[2]):continue
            q=o[2]
            if o[0]=="BUY_PRODUCT":
                price=obs["market"]["prices"].get(o[1]);
                if not _nn(price):return _identity(selected)
                incoming+=q; budget+=q*(price+10)
            elif o[0]=="BUY_ANIMAL" and o[1] in BUY_PRICES:incoming+=q; budget+=q*BUY_PRICES[o[1]]
            elif o[0]=="BUY_SEED" and o[1] in SEED_PRICES:budget+=q*SEED_PRICES[o[1]]
        if sum(stock.values())+incoming>SHED_CAPACITY:st["telemetry"]["capacity_declines"]+=1; return _identity(selected)
        if farm["money"]<budget+(3000 if initial else 1000):st["telemetry"]["budget_declines"]+=1; return _identity(selected)
        st["requested_day"]=day; st["pending"]={"first":expected+1,"initial":initial}; st["telemetry"]["hire_requests"]+=2; st["telemetry"]["feed_buy_requests"]+=6; st["telemetry"]["commit_requests"]+=int(initial)
        out=copy.deepcopy(selected); out["market"]+=extra; return out
    def _worker(self,obs,actor,targets):
        farm=obs["farms"][obs["player"]]; private=obs["private"]; pos=tuple(farm["hands"][actor-1]); inv=private["inventories"][actor]; home=min(ACCESS,key=lambda p:(abs(pos[0]-p[0])+abs(pos[1]-p[1]),p)); dist=abs(pos[0]-home[0])+abs(pos[1]-home[1]); cargo=[i for i in ("WOOL","FERTILIZER") if inv.get(i,0)]
        if cargo and obs["step"]%24>=(22 if obs["step"]//24==29 else 23)-dist:return _walk(pos,home) or ["PLACE",cargo[0],inv[cargo[0]]]
        missing=sum(not(isinstance(farm["tiles"][y][x],dict) and farm["tiles"][y][x].get("animal")=="SHEEP") for x,y in targets)
        if missing and not inv.get("SHEEP",0) and private["shed"].get("SHEEP",0):return _walk(pos,home) or ["PICKUP","SHEEP",min(missing,private["shed"]["SHEEP"])]
        hungry=sum(not(isinstance(farm["tiles"][y][x],dict) and farm["tiles"][y][x].get("fed_today")) for x,y in targets)
        if hungry and not inv.get("WHEAT",0) and private["shed"].get("WHEAT",0):return _walk(pos,home) or ["PICKUP","WHEAT",min(hungry,private["shed"]["WHEAT"])]
        jobs=[]
        for n,(x,y) in enumerate(targets):
            tile=farm["tiles"][y][x]; cmd=None
            if tile is None:cmd=["BUILD_PASTURE"]
            elif isinstance(tile,dict) and tile.get("kind")=="WEED":cmd=["DIG"]
            elif isinstance(tile,dict) and tile.get("kind")=="PASTURE" and not tile.get("animal") and inv.get("SHEEP",0):cmd=["PLACE","SHEEP"]
            elif isinstance(tile,dict) and tile.get("animal")=="SHEEP":
                if not tile.get("fed_today") and inv.get("WHEAT",0):cmd=["FEED"]
                elif not tile.get("cared_today"):cmd=["CARE"]
                elif tile.get("yield_units",0):cmd=["HARVEST"]
                elif tile.get("fertilizer_available"):cmd=["COLLECT_FERTILIZER"]
            if cmd:jobs.append((abs(pos[0]-x)+abs(pos[1]-y),n,(x,y),cmd))
        if jobs:
            _,_,target,cmd=min(jobs); return _walk(pos,target) or cmd
        return (_walk(pos,home) or ["PLACE",cargo[0],inv[cargo[0]]]) if cargo else ["PASS"]
    def _rescue(self,obs,action,st):
        if not st["workers"] or obs["step"]%24>14 or len(action["market"])>=MAX_ORDERS:return action
        orders=action["market"]
        if any(o and (o[0] in ("HIRE","BUY_LAND","BUY_ANIMAL","BUY_PRODUCT","BUY_SEED") or (len(o)>1 and o[1]=="WHEAT")) for o in orders):return action
        farm=obs["farms"][obs["player"]]; private=obs["private"]; cmds=[action["farmer"],*action["hands"]]; hungry=carried=0
        for actor,targets in st["workers"].items():
            if actor>=len(cmds) or actor>=len(private["inventories"]):return action
            if cmds[actor]==["FEED"] or cmds[actor][:2]==["PICKUP","WHEAT"]:return action
            carried+=private["inventories"][actor].get("WHEAT",0); hungry+=sum(isinstance(farm["tiles"][y][x],dict) and farm["tiles"][y][x].get("animal")=="SHEEP" and not farm["tiles"][y][x].get("fed_today") for x,y in targets)
        stock=_stock(obs,action); shortage=hungry-carried-stock.get("WHEAT",0); quote=obs["market"]["prices"]["WHEAT"]
        if not 0<shortage<=6 or st["rescue"]+shortage>6 or quote<1 or farm["money"]<1000+shortage*(quote+10) or sum(stock.values())+shortage>SHED_CAPACITY:return action
        out=copy.deepcopy(action); out["market"].append(["BUY_PRODUCT","WHEAT",shortage]); st["rescue"]+=shortage; st["telemetry"]["rescue_feed_requests"]+=shortage; return out
