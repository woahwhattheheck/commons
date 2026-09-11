import copy, json, os, sys
BASE='/tmp/v31base'
if BASE not in sys.path: sys.path.insert(0, BASE)
import r04_full_router as r04
_orig = r04.reserve_sales
TELEM=os.environ.get('L3_TELEMETRY','/tmp/l3_telemetry.jsonl')

def _debts(state):
    return copy.deepcopy(getattr(state,'sale_window_debts',{}) or {})

def _qty_market(market):
    q={}
    for row in market or []:
        if isinstance(row,list) and len(row)>=3 and row[0]=='SELL':
            try:n=max(0,int(row[2]))
            except Exception:continue
            q[row[1]]=q.get(row[1],0)+n
    return q

def _debt_total(debts):
    q={}
    for due,items in (debts or {}).items():
        for item,n in (items or {}).items(): q[item]=q.get(item,0)+int(n)
    return q

def reserve_l3(action, view, state, tape, step):
    if int(step) < 648:
        return _orig(action,view,state,tape,step)
    # Exact counterfactual on deep copies; never mutate real action/state.
    a=copy.deepcopy(action); s=copy.deepcopy(state)
    before_m=_qty_market(a.get('market',[])); before_d=_debt_total(_debts(s))
    _orig(a,view,s,tape,step)
    after_m=_qty_market(a.get('market',[])); after_d=_debt_total(_debts(s))
    added_m={k:after_m.get(k,0)-before_m.get(k,0) for k in set(before_m)|set(after_m) if after_m.get(k,0)-before_m.get(k,0)}
    added_d={k:after_d.get(k,0)-before_d.get(k,0) for k in set(before_d)|set(after_d) if after_d.get(k,0)-before_d.get(k,0)}
    rec={'pid':os.getpid(),'step':int(step),'player':int(getattr(view,'player',-1)) if hasattr(view,'player') else None,
         'avoided_sell_qty':added_m,'avoided_debt_qty':added_d,'causal':bool(added_m or added_d)}
    try:
        fd=os.open(TELEM,os.O_WRONLY|os.O_CREAT|os.O_APPEND,0o600)
        try: os.write(fd,(json.dumps(rec,separators=(',',':'))+'\n').encode())
        finally: os.close(fd)
    except Exception:
        pass
    return None
r04.reserve_sales=reserve_l3
import main as _base
agent=_base.agent
