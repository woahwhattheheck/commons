from __future__ import annotations
import hashlib, json, re, stat
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

SOURCE_SCHEMA='revenue-collection-desk/source/v1'
REPORT_SCHEMA='revenue-collection-desk/report/v1'
RECEIPT_SCHEMA='revenue-collection-desk/receipt/v1'
MAX_BYTES=5*1024*1024
TOKEN=re.compile(r'^[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,127}$')
MONEY=re.compile(r'^(?:0|[1-9][0-9]*)(?:\.[0-9]{1,9})?$')
TS=re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$')
FIN={'WORK_SUBMITTED','ACCEPTED_AWAITING_PAYMENT','PAYMENT_ASSERTED_HOLD','PAYMENT_AVAILABLE','SETTLED_CASH','DISPUTED','CLOSED_NO_PAY'}
AUX={'COLLECTION_RELEASED','COLLECTION_CONTACT','COUNTERPARTY_REPLY','ROUTE_REPAIRED'}
NEXT={
 'WORK_SUBMITTED':{'ACCEPTED_AWAITING_PAYMENT','DISPUTED','CLOSED_NO_PAY'},
 'ACCEPTED_AWAITING_PAYMENT':{'PAYMENT_ASSERTED_HOLD','PAYMENT_AVAILABLE','DISPUTED','CLOSED_NO_PAY'},
 'PAYMENT_ASSERTED_HOLD':{'PAYMENT_AVAILABLE','DISPUTED','CLOSED_NO_PAY'},
 'PAYMENT_AVAILABLE':{'SETTLED_CASH','DISPUTED','CLOSED_NO_PAY'},
 'DISPUTED':{'ACCEPTED_AWAITING_PAYMENT','CLOSED_NO_PAY'},
 'SETTLED_CASH':set(),'CLOSED_NO_PAY':set(),
}

class CollectionError(ValueError): pass

def _pairs(pairs):
 out={}
 for k,v in pairs:
  if k in out: raise CollectionError(f'duplicate JSON key: {k}')
  out[k]=v
 return out

def _no_int(v): raise CollectionError(f'JSON integers forbidden; use strings: {v}')
def _no_float(v): raise CollectionError(f'JSON numeric fractions forbidden: {v}')
def _no_const(v): raise CollectionError(f'JSON non-finite value forbidden: {v}')

def _reject_bool(value,path='json'):
 if type(value) is bool: raise CollectionError(f'{path}: JSON booleans forbidden')
 if type(value) is list:
  for i,item in enumerate(value): _reject_bool(item,f'{path}[{i}]')
 elif type(value) is dict:
  for k,item in value.items(): _reject_bool(item,f'{path}.{k}')

def load_json_bytes(raw:bytes,label='source'):
 if type(raw) is not bytes or len(raw)>MAX_BYTES: raise CollectionError(f'{label}: bounded bytes required')
 try:
  value=json.loads(raw.decode('utf-8'),object_pairs_hook=_pairs,parse_int=_no_int,parse_float=_no_float,parse_constant=_no_const)
  _reject_bool(value,label)
  return value
 except CollectionError: raise
 except Exception as e: raise CollectionError(f'{label}: invalid JSON: {e}') from e

def canonical(value): return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False)+'\n').encode()
def digest(raw:bytes): return hashlib.sha256(raw).hexdigest()

def exact(v,label,fields):
 if type(v) is not dict: raise CollectionError(f'{label}: object required')
 if set(v)!=set(fields): raise CollectionError(f'{label}: exact fields required')
 return v

def token(v,label):
 if type(v) is not str or TOKEN.fullmatch(v) is None: raise CollectionError(f'{label}: opaque token required')
 return v

def timestamp(v,label):
 if type(v) is not str or TS.fullmatch(v) is None: raise CollectionError(f'{label}: UTC timestamp required')
 try: dt=datetime.strptime(v,'%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
 except ValueError as e: raise CollectionError(f'{label}: invalid UTC timestamp') from e
 return v,dt

def money(v,label,positive=True):
 if type(v) is not str or MONEY.fullmatch(v) is None: raise CollectionError(f'{label}: unsigned decimal string required')
 try: d=Decimal(v)
 except InvalidOperation as e: raise CollectionError(f'{label}: invalid decimal') from e
 if not d.is_finite() or (positive and d<=0): raise CollectionError(f'{label}: positive finite amount required')
 return v,d

def mtext(d):
 s=format(d,'f')
 if '.' in s: s=s.rstrip('0').rstrip('.')
 return s or '0'

def event_data(kind,raw,label,amount,instrument):
 if kind in FIN:
  fields={'amount','instrument'}
  if kind=='PAYMENT_ASSERTED_HOLD': fields.add('hold_until')
  if kind=='SETTLED_CASH': fields.add('settlement_ref')
  d=exact(raw,label+'.data',fields)
  if d['amount']!=amount or d['instrument']!=instrument: raise CollectionError(f'{label}: conflicting economics')
  money(d['amount'],label+'.amount'); token(d['instrument'],label+'.instrument')
  out={'amount':amount,'instrument':instrument}
  if kind=='PAYMENT_ASSERTED_HOLD': out['hold_until']=timestamp(d['hold_until'],label+'.hold_until')[0]
  if kind=='SETTLED_CASH': out['settlement_ref']=token(d['settlement_ref'],label+'.settlement_ref')
  return out
 if kind=='COLLECTION_RELEASED':
  d=exact(raw,label+'.data',{'not_before','expires_at'}); nb,nbd=timestamp(d['not_before'],label+'.not_before'); ex,exd=timestamp(d['expires_at'],label+'.expires_at')
  if exd<=nbd: raise CollectionError(f'{label}: invalid release window')
  return {'not_before':nb,'expires_at':ex}
 if kind=='COLLECTION_CONTACT':
  d=exact(raw,label+'.data',{'delivery','dnr_until'})
  if d['delivery'] not in {'DELIVERED','BOUNCED','DEAD'}: raise CollectionError(f'{label}: bad delivery')
  until=None if d['dnr_until'] is None else timestamp(d['dnr_until'],label+'.dnr_until')[0]
  return {'delivery':d['delivery'],'dnr_until':until}
 exact(raw,label+'.data',set()); return {}

def normalize_claim(raw,index,asof_dt):
 label=f'claims[{index}]'; c=exact(raw,label,{'claim_id','counterparty_id','work_ref','instrument','amount','reference_value_usd','events'})
 cid=token(c['claim_id'],label+'.claim_id'); cp=token(c['counterparty_id'],label+'.counterparty_id'); work=token(c['work_ref'],label+'.work_ref'); inst=token(c['instrument'],label+'.instrument'); amt,amt_d=money(c['amount'],label+'.amount')
 ref=c['reference_value_usd']
 if ref is not None: ref,_=money(ref,label+'.reference_value_usd',positive=False)
 if type(c['events']) is not list or not c['events'] or len(c['events'])>1000: raise CollectionError(label+'.events: bounded non-empty array required')
 seen=set(); times=set(); packed=[]
 for i,r in enumerate(c['events']):
  el=f'{label}.events[{i}]'; e=exact(r,el,{'event_id','at','kind','source_ref','data'}); eid=token(e['event_id'],el+'.event_id')
  if eid in seen: raise CollectionError(f'{label}: duplicate event_id {eid}')
  seen.add(eid); at,dt=timestamp(e['at'],el+'.at')
  if dt>asof_dt or at in times: raise CollectionError(f'{el}: future or duplicate timestamp')
  times.add(at); kind=e['kind']
  if kind not in FIN|AUX: raise CollectionError(f'{el}: unsupported kind')
  item={'event_id':eid,'at':at,'kind':kind,'source_ref':token(e['source_ref'],el+'.source_ref'),'data':event_data(kind,e['data'],el,amt,inst)}
  packed.append((dt,item))
 packed.sort(key=lambda x:(x[0],x[1]['event_id'])); events=[x[1] for x in packed]
 financial=[e for e in events if e['kind'] in FIN]
 if not financial or financial[0]['kind']!='WORK_SUBMITTED' or sum(e['kind']=='WORK_SUBMITTED' for e in financial)!=1: raise CollectionError(f'{label}: exactly one first WORK_SUBMITTED required')
 state='WORK_SUBMITTED'
 for e in financial[1:]:
  if e['kind'] not in NEXT[state]: raise CollectionError(f'{label}: illegal transition {state}->{e["kind"]}')
  state=e['kind']
 hold=None; delivered=None; reply=None; route_broken=False; dnr=None; releases=[]
 for dt,e in packed:
  d=e['data']; k=e['kind']
  if k=='PAYMENT_ASSERTED_HOLD':
   hold,hd=timestamp(d['hold_until'],'hold_until')
   if hd<dt: raise CollectionError(f'{label}: hold predates assertion')
  elif k=='COLLECTION_CONTACT':
   if d['delivery']=='DELIVERED':
    delivered=dt; route_broken=False
    if d['dnr_until'] is not None:
     _,dnr=timestamp(d['dnr_until'],'dnr_until')
     if dnr<dt: raise CollectionError(f'{label}: DNR predates contact')
   else: route_broken=True
  elif k=='ROUTE_REPAIRED': route_broken=False
  elif k=='COUNTERPARTY_REPLY': reply=dt
  elif k=='COLLECTION_RELEASED':
   _,nb=timestamp(d['not_before'],'not_before'); _,ex=timestamp(d['expires_at'],'expires_at'); releases.append((dt,nb,ex))
 if state in {'SETTLED_CASH','CLOSED_NO_PAY'}: action='DONE'
 elif state=='DISPUTED': action='HOLD_CONFLICT'
 elif state=='PAYMENT_AVAILABLE': action='VERIFY_SETTLEMENT'
 elif state=='PAYMENT_ASSERTED_HOLD':
  if hold is None: raise CollectionError(f'{label}: missing hold')
  _,hd=timestamp(hold,'hold_until'); action='WAIT_HOLD' if asof_dt<hd else 'VERIFY_AVAILABLE'
 elif state=='WORK_SUBMITTED': action='WAIT_REPLY'
 elif route_broken: action='ROUTE_REPAIR_REQUIRED'
 elif delivered is not None and (reply is None or reply<delivered):
  newer=any(rd>delivered and nb<=asof_dt<ex for rd,nb,ex in releases)
  action='WAIT_REPLY' if (dnr is not None and asof_dt<dnr) or not newer else 'COLLECTION_ELIGIBLE'
 else: action='COLLECTION_ELIGIBLE' if any(nb<=asof_dt<ex for _,nb,ex in releases) else 'WAIT_REPLY'
 return {'claim_id':cid,'counterparty_id':cp,'work_ref':work,'instrument':inst,'amount':amt,'reference_value_usd':ref,'state':state,'next_action':action,'hold_until':hold,'events':events,'_amount':amt_d}

def compile_ledger(source:Any):
 root=exact(source,'source',{'schema','as_of','claims'})
 if root['schema']!=SOURCE_SCHEMA: raise CollectionError('source.schema mismatch')
 asof,asof_dt=timestamp(root['as_of'],'source.as_of')
 if type(root['claims']) is not list or len(root['claims'])>10000: raise CollectionError('source.claims: bounded array required')
 claims=[]; ids=set(); identities=set()
 for i,raw in enumerate(root['claims']):
  c=normalize_claim(raw,i,asof_dt)
  if c['claim_id'] in ids: raise CollectionError('duplicate claim_id')
  ident=(c['counterparty_id'],c['work_ref'])
  if ident in identities: raise CollectionError('duplicate counterparty/work_ref')
  ids.add(c['claim_id']); identities.add(ident); claims.append(c)
 claims.sort(key=lambda c:c['claim_id']); totals={}
 for c in claims:
  b=totals.setdefault(c['instrument'],{k:Decimal(0) for k in ('accepted_outstanding','asserted_hold','available_not_settled','settled_cash')}); a=c['_amount']; s=c['state']
  if s in {'ACCEPTED_AWAITING_PAYMENT','PAYMENT_ASSERTED_HOLD','PAYMENT_AVAILABLE'}: b['accepted_outstanding']+=a
  if s=='PAYMENT_ASSERTED_HOLD': b['asserted_hold']+=a
  if s=='PAYMENT_AVAILABLE': b['available_not_settled']+=a
  if s=='SETTLED_CASH': b['settled_cash']+=a
 clean=[{k:v for k,v in c.items() if not k.startswith('_')} for c in claims]
 payload={'schema':REPORT_SCHEMA,'as_of':asof,'claims':clean,'totals_by_instrument':{i:{k:mtext(v) for k,v in b.items()} for i,b in sorted(totals.items())},'recognition':{'accepted_is_not_paid':True,'provider_assertion_is_not_settlement':True,'reference_valuation_is_never_cash':True,'mixed_instrument_sum':None,'settled_cash_requires_exact_event':True},'authority':{'external_contact':False,'invoice_creation':False,'claim_submission':False,'provider_mutation':False,'wallet_or_bank_mutation':False,'payment_movement':False,'revenue_recognition_authority':False}}
 return {'payload':payload,'semantic_sha256':digest(canonical(payload))}

def verify_ledger(source,report):
 if canonical(compile_ledger(source))!=canonical(report): raise CollectionError('report verification failed')
 return True

def markdown_queue(report):
 lines=['# Revenue collection queue','',f"As of `{report['payload']['as_of']}`. Internal evidence compiler only; **no message is authorized by this file**.",'','| Claim | Counterparty | Instrument | Amount | State | Next action |','|---|---|---|---:|---|---|']
 for r in report['payload']['claims']:
  vals=[str(r[k]).replace('|','\\|') for k in ('claim_id','counterparty_id','instrument','amount','state','next_action')]; lines.append('| '+' | '.join(vals)+' |')
 lines+=['','Reference valuations are retained metadata only and never enter settled-cash totals.','']; return '\n'.join(lines).encode()

def artifact_bundle(source_bytes):
 source=load_json_bytes(source_bytes); report=compile_ledger(source); rb=canonical(report); mb=markdown_queue(report); receipt={'schema':RECEIPT_SCHEMA,'normalized_source_sha256':digest(canonical(source)),'report_semantic_sha256':report['semantic_sha256'],'artifacts':{'report.json':digest(rb),'queue.md':digest(mb)},'authority':'INTERNAL_OFFLINE_CONTROL_ONLY'}
 return {'report.json':rb,'queue.md':mb,'receipt.json':canonical(receipt)}

def read_regular(path:Path,maximum=MAX_BYTES):
 st=path.lstat()
 if stat.S_ISLNK(st.st_mode) or not stat.S_ISREG(st.st_mode) or st.st_size>maximum: raise CollectionError(f'ordinary bounded file required: {path}')
 return path.read_bytes()

def publish_bundle(source_bytes,output:Path):
 artifacts=artifact_bundle(source_bytes); output.mkdir(mode=0o700,parents=False,exist_ok=False)
 for name,data in artifacts.items():
  with (output/name).open('xb') as f: f.write(data)
 return artifacts

def verify_bundle(source_bytes,output:Path):
 for name,data in artifact_bundle(source_bytes).items():
  if read_regular(output/name)!=data: raise CollectionError(f'artifact mismatch: {name}')
 return True
