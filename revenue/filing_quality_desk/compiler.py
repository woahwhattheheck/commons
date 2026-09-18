from decimal import Decimal
from .core import *
from .policy import parse_policy
from .select import select

def compile_packet(source_raw:bytes,policy_raw:bytes):
    src=load(source_raw);pol=load(policy_raw,512_000)
    if not isinstance(src,dict) or not isinstance(pol,dict):raise FilingQualityError('roots must be objects')
    cik,cutoff,sels,checks=parse_policy(pol);actual=text(src.get('cik'),'source.cik')
    if actual.lstrip('0')!=cik.lstrip('0'):raise FilingQualityError('CIK mismatch')
    facts=src.get('facts')
    if not isinstance(facts,dict):raise FilingQualityError('facts must be object')
    obs={};findings=[]
    for q in sels:
        try:obs[q['id']]=select(facts,q)
        except FilingQualityError as e:findings.append({'id':f"selection:{q['id']}",'severity':'ERROR','code':'SELECTION_HOLD','detail':str(e)})
    for o in obs.values():
        if o['prior_values']:findings.append({'id':f"history:{o['selector_id']}",'severity':'INFO','code':'VALUE_CHANGED_PRIOR_FILING','detail':f"selected {o['value']}; prior={','.join(o['prior_values'])}"})
    if not any(f['severity']=='ERROR' for f in findings):
        for c in checks:
            ids=list(c['lhs'])+[c['rhs']]
            if any(x not in obs for x in ids):findings.append({'id':c['id'],'severity':'ERROR','code':'CHECK_MISSING_SELECTOR','detail':'missing selector'});continue
            xs=[obs[x] for x in ids]
            if len({x['unit'] for x in xs})>1 or len({x['period'] for x in xs})>1:findings.append({'id':c['id'],'severity':'ERROR','code':'CHECK_INCOMPATIBLE','detail':'unit or period mismatch'});continue
            lhs=sum((Decimal(obs[x]['value']) for x in c['lhs']),Decimal(0));rhs=Decimal(obs[c['rhs']]['value']);tol=dec(c.get('tolerance','0'),'tolerance');delta=lhs-rhs;ok=abs(delta)<=tol
            findings.append({'id':c['id'],'severity':'INFO' if ok else 'ERROR','code':'CHECK_PASS' if ok else 'CHECK_FAIL','detail':f'lhs={dec_text(lhs)} rhs={dec_text(rhs)} delta={dec_text(delta)} tolerance={dec_text(tol)}'})
    findings.sort(key=lambda x:(x['severity'],x['code'],x['id'],x['detail']))
    p={'schema':'tjlabs.filing-quality-desk/v1','source_sha256':sha(source_raw),'policy_sha256':sha(policy_raw),'cik':cik,'filed_on_or_before':cutoff,'status':'HOLD' if any(f['severity']=='ERROR' for f in findings) else 'READY_FOR_ANALYST_QA','observations':[obs[k] for k in sorted(obs)],'findings':findings,'limitations':['Retained bytes are not authenticated SEC custody.','A filing-date cutoff over a later snapshot is not a historical-vintage guarantee.','Value changes are findings, not automatic restatement claims.','No investment, filing, trading, GL, payment, or customer-account action is authorized.']}
    p['semantic_sha256']=sha(canon(p));return p
