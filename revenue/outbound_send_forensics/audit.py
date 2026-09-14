#!/usr/bin/env python3
"""Offline, fail-closed audit of outbound sends against connector-native lease evidence."""
from __future__ import annotations
import argparse,hashlib,json,re,sys
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path
from typing import Any,Mapping,Sequence
from revenue.outbound_connector_lease.key import BRANCH_PREFIX,LeaseKeyError,SUPPORTED_REPLY_PROVIDERS,compile_document as compile_lease_document
INPUT_SCHEMA='outbound-send-forensics/v1'; RECEIPT_SCHEMA='outbound-send-forensics-receipt/v1'; BATCH_SCHEMA='outbound-send-forensics-batch/v1'
_SHA256_RE=re.compile(r'^[0-9a-f]{64}$'); _SHA1_RE=re.compile(r'^[0-9a-f]{40}$'); _TOKEN_RE=re.compile(r'^[a-z0-9][a-z0-9._:/+\-]{0,190}$'); _BRANCH_RE=re.compile(r'^outbound-connector-lease/v1/[0-9a-f]{64}$'); _RFC3339_RE=re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$')
CLASS_PROTECTED='PROTECTED_PRE_SEND'; CLASS_POST_SEND='POST_SEND_LEASE_VIOLATION'; CLASS_MISSING='MISSING_LEASE'; CLASS_MISMATCH='SEAM_MISMATCH'; CLASS_UNTRUSTED='AMBIGUOUS_UNTRUSTED_EVIDENCE'; DUPLICATE_FLAG='DUPLICATE_SEND_SAME_SEAM'
CLASSIFICATIONS=(CLASS_PROTECTED,CLASS_POST_SEND,CLASS_MISSING,CLASS_MISMATCH,CLASS_UNTRUSTED)
class ForensicsError(ValueError): pass
def _strict_object(pairs):
    out={}
    for k,v in pairs:
        if k in out: raise ForensicsError(f'duplicate JSON key: {k}')
        out[k]=v
    return out
def strict_loads(raw):
    try: value=json.loads(raw,object_pairs_hook=_strict_object,parse_constant=lambda t:(_ for _ in ()).throw(ForensicsError(f'non-finite JSON number: {t}')))
    except json.JSONDecodeError as e: raise ForensicsError('invalid JSON') from e
    if type(value) is not dict: raise ForensicsError('input must be a JSON object')
    return value
def _exact(value,fields,name):
    if type(value) is not dict: raise ForensicsError(f'{name} must be an object')
    actual=set(value)
    if actual!=fields:
        missing=sorted(fields-actual); extra=sorted(actual-fields); bits=[]
        if missing: bits.append('missing='+','.join(missing))
        if extra: bits.append('extra='+','.join(extra))
        raise ForensicsError(f"{name} requires exact fields ({'; '.join(bits)})")
    return value
def _token(value,field):
    if type(value) is not str: raise ForensicsError(f'{field} must be a string')
    token=value.strip().casefold()
    if not token or len(token)>191 or _TOKEN_RE.fullmatch(token) is None: raise ForensicsError(f'{field} must use 1..191 lowercase-token chars [a-z0-9._:/+-]')
    return token
def _enum(value,allowed,field):
    if type(value) is not str: raise ForensicsError(f'{field} must be a string')
    n=value.strip().casefold()
    if n not in allowed: raise ForensicsError(f"{field} must be one of: {','.join(sorted(allowed))}")
    return n
def _sha256(value,field):
    if type(value) is not str or _SHA256_RE.fullmatch(value) is None: raise ForensicsError(f'{field} must be exactly 64 lowercase hex characters')
    return value
def _sha1(value,field):
    if type(value) is not str or _SHA1_RE.fullmatch(value) is None: raise ForensicsError(f'{field} must be exactly 40 lowercase hex characters')
    return value
def _branch(value,field):
    if type(value) is not str or _BRANCH_RE.fullmatch(value) is None: raise ForensicsError(f'{field} must be {BRANCH_PREFIX}<64-lowercase-hex>')
    return value
def _timestamp(value,field):
    if type(value) is not str or not value.strip(): raise ForensicsError(f'{field} must be a non-empty RFC3339 timestamp')
    raw=value.strip()
    if _RFC3339_RE.fullmatch(raw) is None: raise ForensicsError(f'{field} must be strict RFC3339 with T, seconds, and timezone')
    candidate=raw[:-1]+'+00:00' if raw.endswith('Z') else raw
    try: parsed=datetime.fromisoformat(candidate)
    except ValueError as e: raise ForensicsError(f'{field} must be a valid RFC3339 timestamp') from e
    if parsed.tzinfo is None or parsed.utcoffset() is None: raise ForensicsError(f'{field} must include an explicit timezone offset')
    utc=parsed.astimezone(timezone.utc); canonical=utc.isoformat(timespec='microseconds').replace('+00:00','Z'); return utc,canonical
def _digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')).hexdigest()
def _normalize_send(raw):
    s=_exact(raw,{'provider','event_id','sent_at','authority','status','receipt_sha256'},'record.send')
    p=_enum(s['provider'],set(SUPPORTED_REPLY_PROVIDERS),'record.send.provider'); eid=_token(s['event_id'],'record.send.event_id'); dt,at=_timestamp(s['sent_at'],'record.send.sent_at')
    auth=_enum(s['authority'],{'provider-receipt','caller-assertion'},'record.send.authority'); status=_enum(s['status'],{'sent','ambiguous'},'record.send.status'); rh=_sha256(s['receipt_sha256'],'record.send.receipt_sha256')
    return {'provider':p,'event_id':eid,'sent_dt':dt,'sent_at':at,'authority':auth,'status':status,'receipt_sha256':rh}
def _normalize_lease(raw):
    if raw is None:return None
    l=_exact(raw,{'branch','created_at','authority','result','base_sha','receipt_sha256'},'record.lease_create'); branch=_branch(l['branch'],'record.lease_create.branch'); dt,at=_timestamp(l['created_at'],'record.lease_create.created_at')
    auth=_enum(l['authority'],{'github-create-result','caller-assertion'},'record.lease_create.authority'); result=_enum(l['result'],{'created','exists','ambiguous','failed'},'record.lease_create.result'); base=_sha1(l['base_sha'],'record.lease_create.base_sha'); rh=_sha256(l['receipt_sha256'],'record.lease_create.receipt_sha256')
    return {'branch':branch,'created_dt':dt,'created_at':at,'authority':auth,'result':result,'base_sha':base,'receipt_sha256':rh}
def _normalize_record(raw):
    r=_exact(raw,{'record_id','seam','send','lease_create'},'record'); rid=_token(r['record_id'],'record.record_id')
    try: compiled=compile_lease_document(r['seam'])
    except LeaseKeyError as e: raise ForensicsError(f'record.seam invalid: {e}') from e
    return {'record_id':rid,'compiled':compiled,'send':_normalize_send(r['send']),'lease':_normalize_lease(r['lease_create'])}
def _classify(r):
    s=r['send']; l=r['lease']; expected=r['compiled']['branch']
    if s['authority']!='provider-receipt' or s['status']!='sent': return CLASS_UNTRUSTED,['provider send is not backed by an authoritative SENT receipt']
    if l is None:return CLASS_MISSING,['provider SENT exists but no lease-create evidence was supplied']
    if l['authority']!='github-create-result' or l['result']!='created': return CLASS_UNTRUSTED,['lease evidence does not prove an exact successful GitHub create-branch result']
    if l['branch']!=expected:return CLASS_MISMATCH,['successful lease evidence is for a different canonical seam branch']
    if l['created_dt']>=s['sent_dt']:return CLASS_POST_SEND,['lease create was not strictly earlier than the provider SENT event']
    return CLASS_PROTECTED,['authoritative matching lease create is strictly earlier than provider SENT']
def _payload(r):
    c,reasons=_classify(r); s=r['send']; l=r['lease']
    return {'schema':RECEIPT_SCHEMA,'record_id':r['record_id'],'classification':c,'reasons':reasons,'dnr':True,'expected_branch':r['compiled']['branch'],'seam_sha256':r['compiled']['seam_sha256'],'send_provider':s['provider'],'send_event_id':s['event_id'],'send_at_utc':s['sent_at'],'send_receipt_sha256':s['receipt_sha256'],'lease_branch':None if l is None else l['branch'],'lease_created_at_utc':None if l is None else l['created_at'],'lease_receipt_sha256':None if l is None else l['receipt_sha256'],'batch_flags':[],'same_seam_send_count':1}
def _seal(p):
    bare=dict(p); bare.pop('receipt_sha256',None); return {**bare,'receipt_sha256':_digest(bare)}
def audit_document(document):
    top=_exact(document,{'schema','records'},'input')
    if top['schema']!=INPUT_SCHEMA:raise ForensicsError(f'input.schema must be {INPUT_SCHEMA}')
    if type(top['records']) is not list or not top['records']:raise ForensicsError('input.records must be a non-empty array')
    records=[_normalize_record(x) for x in top['records']]; ids=[r['record_id'] for r in records]; dup=sorted(k for k,c in Counter(ids).items() if c>1)
    if dup:raise ForensicsError('duplicate record_id: '+','.join(dup))
    seen={}
    for r in records:
        key=(r['send']['provider'],r['send']['event_id'])
        if key in seen:
            p=seen[key]
            if p['send']['sent_at']!=r['send']['sent_at'] or p['send']['receipt_sha256']!=r['send']['receipt_sha256'] or p['compiled']['branch']!=r['compiled']['branch']:raise ForensicsError('contradictory duplicate provider event: '+':'.join(key))
            raise ForensicsError('duplicate provider event: '+':'.join(key))
        seen[key]=r
    receipts=[_payload(r) for r in records]; by=defaultdict(list)
    for r,x in zip(records,receipts):
        s=r['send']
        if s['authority']=='provider-receipt' and s['status']=='sent':by[x['expected_branch']].append(x)
    incidents=[]
    for branch,group in sorted(by.items()):
        if len(group)<=1:continue
        for x in group:x['batch_flags']=[DUPLICATE_FLAG];x['same_seam_send_count']=len(group)
        incidents.append({'expected_branch':branch,'send_count':len(group),'record_ids':sorted(x['record_id'] for x in group),'provider_events':sorted(f"{x['send_provider']}:{x['send_event_id']}" for x in group)})
    sealed=sorted((_seal(x) for x in receipts),key=lambda x:x['record_id']); counts=Counter(x['classification'] for x in sealed)
    summary={'records':len(sealed),'dnr_records':sum(1 for x in sealed if x['dnr']),'duplicate_seams':len(incidents),'duplicate_send_records':sum(1 for x in sealed if DUPLICATE_FLAG in x['batch_flags']),**{name:counts.get(name,0) for name in CLASSIFICATIONS}}
    payload={'schema':BATCH_SCHEMA,'summary':summary,'incident_seams':incidents,'receipts':sealed};return {**payload,'batch_sha256':_digest(payload)}
def audit_json(raw):return audit_document(strict_loads(raw))
def main(argv:Sequence[str]|None=None):
    parser=argparse.ArgumentParser(description='Audit provider sends against canonical pre-send lease evidence');parser.add_argument('input',nargs='?',default='-',help="input JSON path, or '-' for stdin");parser.add_argument('--pretty',action='store_true');args=parser.parse_args(argv)
    try: raw=sys.stdin.read() if args.input=='-' else Path(args.input).read_text(encoding='utf-8');result=audit_json(raw)
    except (ForensicsError,OSError) as e:print(f'HOLD: {e}',file=sys.stderr);return 2
    print(json.dumps(result,sort_keys=True,indent=2 if args.pretty else None,separators=None if args.pretty else (',',':'),ensure_ascii=True));return 0
if __name__=='__main__':raise SystemExit(main())
