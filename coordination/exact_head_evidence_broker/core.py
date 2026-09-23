from __future__ import annotations

import hashlib, json, re
from datetime import datetime, timedelta, timezone
from typing import Any

INPUT_SCHEMA = 'commons-exact-head-evidence/v1'
RECEIPT_SCHEMA = 'commons-exact-head-evidence-receipt/v2'
COMPILER_ID = 'commons.exact-head-evidence-broker/v2'
MAX_INPUT_BYTES = 2 * 1024 * 1024
MAX_TEXT = 4096
MAX_ITEMS = 2048
MAX_DEPTH = 32
MAX_NODES = 10000
MAX_SAFE_INT = 10**15
MAX_SNAPSHOT_AGE = timedelta(hours=24)
_SHA = re.compile(r'^[0-9a-f]{40}$')
_BLOB = re.compile(r'^[0-9a-f]{40}$')
_ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._:/@+\-]{0,255}$')
_TS = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$')
RUN_STATUSES = frozenset({'queued','pending','waiting','requested','in_progress','completed'})
RUN_CONCLUSIONS = frozenset({'success','failure','cancelled','skipped','timed_out','action_required','neutral','stale','startup_failure'})
VERDICTS = frozenset({'GREEN','STOP'})
MERGEABILITY = frozenset({'true','false','unknown'})
STATES = frozenset({
    'READY_FOR_HUMAN_FINALIZATION_REVIEW','HOLD_HEAD_MISMATCH','HOLD_MAIN_PATH_OVERLAP',
    'HOLD_CI_UNKNOWN','HOLD_CI_FAILED','HOLD_REVIEW_MISSING','HOLD_REVIEW_STOP',
    'HOLD_REVIEW_CONFLICT','HOLD_MERGEABILITY_UNKNOWN','HOLD_NOT_MERGEABLE',
    'HOLD_CRITICAL_BLOB_MISMATCH','HOLD_STALE_SNAPSHOT','HOLD_MALFORMED_EVIDENCE',
})

class BrokerError(ValueError):
    pass

def _bad_float(_s: str, _err=BrokerError): raise _err('float JSON forbidden')
def _bad_constant(_s: str, _err=BrokerError): raise _err('nonfinite JSON forbidden')
def _parse_int(s: str, _int=int, _len=len, _abs=abs, _max=MAX_SAFE_INT, _err=BrokerError):
    if _len(s.lstrip('-')) > 16: raise _err('integer outside safe domain')
    v = _int(s)
    if _abs(v) > _max: raise _err('integer outside safe domain')
    return v

def _pairs(rows, _err=BrokerError):
    out = {}
    for k,v in rows:
        if k in out: raise _err('duplicate JSON key')
        out[k]=v
    return out

def _freeze(value: Any, _type=type, _bool_type=bool, _int_type=int, _str_type=str, _list_type=list, _dict_type=dict, _len=len, _abs=abs, _unicode_error=UnicodeError, _recursion_error=RecursionError, _err=BrokerError,
            _max_text=MAX_TEXT, _max_items=MAX_ITEMS, _max_depth=MAX_DEPTH,
            _max_nodes=MAX_NODES, _max_int=MAX_SAFE_INT):
    nodes=[0]
    def walk(v, depth):
        if depth > _max_depth: raise _err('JSON depth limit')
        nodes[0]+=1
        if nodes[0] > _max_nodes: raise _err('JSON node limit')
        t=_type(v)
        if v is None or t is _bool_type: return v
        if t is _int_type:
            if _abs(v)>_max_int: raise _err('integer outside safe domain')
            return v
        if t is _str_type:
            if _len(v)>_max_text: raise _err('text limit')
            try: v.encode('utf-8','strict')
            except _unicode_error as e: raise _err('invalid UTF-8') from e
            return v
        if t is _list_type:
            if _len(v)>_max_items: raise _err('collection limit')
            return [walk(x,depth+1) for x in v]
        if t is _dict_type:
            if _len(v)>_max_items: raise _err('mapping limit')
            out={}
            for k,x in v.items():
                if _type(k) is not _str_type: raise _err('object key type')
                if _len(k)>_max_text: raise _err('key limit')
                try: k.encode('utf-8','strict')
                except _unicode_error as e: raise _err('invalid UTF-8') from e
                out[k]=walk(x,depth+1)
            return out
        raise _err('non-JSON type')
    try: return walk(value,0)
    except _recursion_error as e: raise _err('JSON recursion limit') from e

def loads_strict_json(raw: bytes|str, _loads=json.loads, _freeze_fn=_freeze, _pairs_hook=_pairs,
                      _parse_int_fn=_parse_int, _bad_float_fn=_bad_float, _bad_const_fn=_bad_constant,
                      _type=type, _len=len, _bytes=bytes, _str=str, _max=MAX_INPUT_BYTES, _json_error=json.JSONDecodeError, _value_error=ValueError, _type_error=TypeError, _recursion_error=RecursionError, _err=BrokerError):
    if _type(raw) is _bytes:
        if _len(raw)>_max: raise _err('JSON input byte limit')
        try: text=raw.decode('utf-8','strict')
        except UnicodeError as e: raise _err('invalid UTF-8') from e
    elif _type(raw) is _str:
        if _len(raw)>_max: raise _err('JSON input byte limit')
        try: enc=raw.encode('utf-8','strict')
        except UnicodeError as e: raise _err('invalid UTF-8') from e
        if _len(enc)>_max: raise _err('JSON input byte limit')
        text=raw
    else: raise _err('JSON input type')
    try:
        obj=_loads(text,object_pairs_hook=_pairs_hook,parse_int=_parse_int_fn,parse_float=_bad_float_fn,parse_constant=_bad_const_fn)
    except _err: raise
    except (_json_error,_value_error,_type_error,_recursion_error) as e: raise _err('invalid JSON') from e
    return _freeze_fn(obj)

def _canonical(obj, _freeze_fn=_freeze, _dumps=json.dumps, _value_error=ValueError, _type_error=TypeError, _unicode_error=UnicodeError, _recursion_error=RecursionError, _err=BrokerError):
    try: return _dumps(_freeze_fn(obj),sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8','strict')
    except (_value_error,_type_error,_unicode_error,_recursion_error) as e: raise _err('canonical JSON') from e

def _digest(obj, _canonical_fn=_canonical, _sha256=hashlib.sha256): return _sha256(_canonical_fn(obj)).hexdigest()

def _exact(obj, keys, label, _type=type, _dict_type=dict, _set=set, _err=BrokerError):
    if _type(obj) is not _dict_type or _set(obj)!=keys: raise _err(f'{label} keys')
    return obj

def _text(v,label,_type=type,_str=str,_len=len,_max=MAX_TEXT,_err=BrokerError):
    if _type(v) is not _str or not v or _len(v)>_max: raise _err(label)
    try: v.encode('utf-8','strict')
    except UnicodeError as e: raise _err(label) from e
    return v

def _ident(v,label,_text_fn=_text,_re=_ID,_err=BrokerError):
    v=_text_fn(v,label)
    if not _re.fullmatch(v): raise _err(label)
    return v

def _sha40(v,label,_text_fn=_text,_re=_SHA,_err=BrokerError):
    v=_text_fn(v,label)
    if not _re.fullmatch(v): raise _err(label)
    return v

def _path(v,label='path',_type=type,_str=str,_len=len,_any=any,_err=BrokerError):
    if _type(v) is not _str or not v or _len(v)>1024 or v.startswith('/') or '\\' in v or '\x00' in v or _any(part in ('','.','..') for part in v.split('/')): raise _err(label)
    return v

def _ts(v,label,_text_fn=_text,_re=_TS,_strptime=datetime.strptime,_utc=timezone.utc,_value_error=ValueError,_err=BrokerError):
    v=_text_fn(v,label)
    if not _re.fullmatch(v): raise _err(label)
    try: dt=_strptime(v,'%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=_utc)
    except _value_error as e: raise _err(label) from e
    if dt.strftime('%Y-%m-%dT%H:%M:%SZ')!=v: raise _err(label)
    return dt

def _fmt(dt,_utc=timezone.utc): return dt.astimezone(_utc).replace(microsecond=0).strftime('%Y-%m-%dT%H:%M:%SZ')

def _validate(packet, _freeze_fn=_freeze, _exact_fn=_exact, _ident_fn=_ident, _sha_fn=_sha40, _path_fn=_path, _ts_fn=_ts, _input_schema=INPUT_SCHEMA, _mergeability=MERGEABILITY, _run_statuses=RUN_STATUSES, _run_conclusions=RUN_CONCLUSIONS, _verdicts=VERDICTS, _max_items=MAX_ITEMS, _type=type, _int_type=int, _list_type=list, _len=len, _err=BrokerError):
    p=_freeze_fn(packet)
    _exact_fn(p,{'schema','repo','pr_number','source_owner_ref','candidate_head_sha','provider_pr_head_sha','base_sha','current_main_sha','observed_at_utc','valid_until_utc','mergeability','pr_changed_paths','main_changed_paths','required_workflows','workflow_runs','reviews','critical_blobs'},'packet')
    if p['schema']!=_input_schema: raise _err('schema')
    _ident_fn(p['repo'],'repo'); _ident_fn(p['source_owner_ref'],'source_owner_ref')
    if _type(p['pr_number']) is not _int_type or p['pr_number']<=0: raise _err('pr_number')
    for f in ('candidate_head_sha','provider_pr_head_sha','base_sha','current_main_sha'): _sha_fn(p[f],f)
    _ts_fn(p['observed_at_utc'],'observed_at_utc'); _ts_fn(p['valid_until_utc'],'valid_until_utc')
    if p['mergeability'] not in _mergeability: raise _err('mergeability')
    for f in ('pr_changed_paths','main_changed_paths','required_workflows','workflow_runs','reviews','critical_blobs'):
        if _type(p[f]) is not _list_type or _len(p[f])>_max_items: raise _err(f)
    for x in p['pr_changed_paths']+p['main_changed_paths']: _path_fn(x)
    for x in p['required_workflows']: _ident_fn(x,'workflow name')
    for r in p['workflow_runs']:
        _exact_fn(r,{'run_id','name','head_sha','status','conclusion'},'workflow')
        if _type(r['run_id']) is not _int_type or r['run_id']<=0: raise _err('run_id')
        _ident_fn(r['name'],'workflow name'); _sha_fn(r['head_sha'],'workflow head')
        if r['status'] not in _run_statuses: raise _err('workflow status')
        if r['status']=='completed':
            if r['conclusion'] not in _run_conclusions: raise _err('workflow conclusion')
        elif r['conclusion'] is not None: raise _err('nonterminal conclusion')
    for r in p['reviews']:
        _exact_fn(r,{'provider_id','head_sha','reviewer_ref','verdict'},'review')
        _ident_fn(r['provider_id'],'provider_id'); _sha_fn(r['head_sha'],'review head'); _ident_fn(r['reviewer_ref'],'reviewer_ref')
        if r['verdict'] not in _verdicts: raise _err('verdict')
    for b in p['critical_blobs']:
        _exact_fn(b,{'path','expected_blob_sha','observed_blob_sha'},'blob')
        _path_fn(b['path']); _sha_fn(b['expected_blob_sha'],'expected_blob_sha'); _sha_fn(b['observed_blob_sha'],'observed_blob_sha')
    return p

def _authority():
    return {
        'merge_authorized':False,'ref_or_source_mutation_authorized':False,'provider_mutation_authorized':False,
        'workflow_cancel_or_rerun_authorized':False,'review_submission_authorized':False,'outbound_or_muse_authorized':False,
        'terms_or_contract_authorized':False,'invoice_or_receivable_authorized':False,'payment_or_funds_movement_authorized':False,
        'cash_receipt_proven':False,'revenue_recognized':False,'tax_or_accounting_conclusion':False,
    }

def _provenance():
    return {
        'provider_snapshot_complete':False,
        'owner_identity_authenticated_here':False,
        'reviewer_identity_authenticated_here':False,
        'review_verdict_authenticated_here':False,
    }

def _compile_at(packet, now, _validate_fn=_validate, _ts_fn=_ts, _fmt_fn=_fmt, _digest_fn=_digest,
                _authority_fn=_authority, _provenance_fn=_provenance, _receipt_schema=RECEIPT_SCHEMA, _compiler_id=COMPILER_ID, _utc=timezone.utc, _max_age=MAX_SNAPSHOT_AGE, _len=len, _set=set, _sorted=sorted, _sum=sum, _any=any):
    p=_validate_fn(packet); now=now.astimezone(_utc).replace(microsecond=0)
    observed=_ts_fn(p['observed_at_utc'],'observed_at_utc'); valid=_ts_fn(p['valid_until_utc'],'valid_until_utc')
    reasons=[]; diagnostics={}
    anomalies=[]
    for field in ('pr_changed_paths','main_changed_paths','required_workflows'):
        if _len(p[field])!=_len(_set(p[field])): anomalies.append('DUPLICATE_'+field.upper())
    ids=[r['run_id'] for r in p['workflow_runs']]
    if _len(ids)!=_len(_set(ids)): anomalies.append('DUPLICATE_RUN_ID')
    review_ids=[r['provider_id'] for r in p['reviews']]
    if _len(review_ids)!=_len(_set(review_ids)): anomalies.append('DUPLICATE_REVIEW_ID')
    blob_paths=[b['path'] for b in p['critical_blobs']]
    if _len(blob_paths)!=_len(_set(blob_paths)): anomalies.append('DUPLICATE_CRITICAL_PATH')
    exact_runs=[r for r in p['workflow_runs'] if r['head_sha']==p['provider_pr_head_sha']]
    by_name={}
    for r in exact_runs: by_name.setdefault(r['name'],[]).append(r)
    for name,rows in by_name.items():
        if _len(rows)>1: anomalies.append('WORKFLOW_NAME_COLLISION:'+name)
    exact_reviews=[r for r in p['reviews'] if r['head_sha']==p['provider_pr_head_sha']]
    claimed_distinct_reviews=[r for r in exact_reviews if r['reviewer_ref']!=p['source_owner_ref']]
    stale_review_count=_sum(r['head_sha']!=p['provider_pr_head_sha'] for r in p['reviews'])
    diagnostics['stale_review_count']=stale_review_count
    diagnostics['main_path_overlap']=_sorted(_set(p['pr_changed_paths']) & _set(p['main_changed_paths']))
    diagnostics['exact_head_workflow_run_ids']=_sorted(r['run_id'] for r in exact_runs)
    diagnostics['exact_head_review_ids']=_sorted(r['provider_id'] for r in exact_reviews)
    diagnostics['claimed_distinct_exact_head_review_ids']=_sorted(r['provider_id'] for r in claimed_distinct_reviews)
    diagnostics['malformed_anomalies']=_sorted(anomalies)
    if anomalies:
        state='HOLD_MALFORMED_EVIDENCE'; reasons.extend(_sorted(anomalies))
    elif p['candidate_head_sha']!=p['provider_pr_head_sha']:
        state='HOLD_HEAD_MISMATCH'; reasons.append('PROVIDER_HEAD_MOVED')
    elif observed>now or valid<=observed or now>=valid or now-observed>_max_age:
        state='HOLD_STALE_SNAPSHOT'; reasons.append('SNAPSHOT_NOT_CURRENT')
    elif _any(b['expected_blob_sha']!=b['observed_blob_sha'] for b in p['critical_blobs']):
        state='HOLD_CRITICAL_BLOB_MISMATCH'; reasons.append('CRITICAL_BLOB_REMINT')
    elif diagnostics['main_path_overlap']:
        state='HOLD_MAIN_PATH_OVERLAP'; reasons.append('CURRENT_MAIN_PATH_OVERLAP')
    else:
        required=_set(p['required_workflows']); missing=[]; unknown=[]; failed=[]
        for name in _sorted(required):
            rows=by_name.get(name,[])
            if not rows: missing.append(name); continue
            row=rows[0]
            if row['status']!='completed': unknown.append(name)
            elif row['conclusion']!='success': failed.append(name)
        diagnostics['missing_workflows']=missing; diagnostics['unknown_workflows']=unknown; diagnostics['failed_workflows']=failed
        claimed_greens=[r for r in claimed_distinct_reviews if r['verdict']=='GREEN']; stops=[r for r in exact_reviews if r['verdict']=='STOP']
        diagnostics['claimed_green_review_ids']=_sorted(r['provider_id'] for r in claimed_greens); diagnostics['stop_review_ids']=_sorted(r['provider_id'] for r in stops)
        if missing or unknown:
            state='HOLD_CI_UNKNOWN'; reasons.append('REQUIRED_CI_NOT_TERMINAL_SUCCESS')
        elif failed:
            state='HOLD_CI_FAILED'; reasons.append('REQUIRED_CI_NON_SUCCESS')
        elif claimed_greens and stops:
            state='HOLD_REVIEW_CONFLICT'; reasons.append('CLAIMED_EXACT_HEAD_GREEN_STOP_CONFLICT')
        elif stops:
            state='HOLD_REVIEW_STOP'; reasons.append('EXACT_HEAD_STOP')
        elif not claimed_greens:
            state='HOLD_REVIEW_MISSING'; reasons.append('NO_CLAIMED_DISTINCT_EXACT_HEAD_GREEN')
        elif p['mergeability']=='unknown':
            state='HOLD_MERGEABILITY_UNKNOWN'; reasons.append('MERGEABILITY_UNKNOWN')
        elif p['mergeability']=='false':
            state='HOLD_NOT_MERGEABLE'; reasons.append('PROVIDER_NOT_MERGEABLE')
        else:
            state='READY_FOR_HUMAN_FINALIZATION_REVIEW'; reasons.append('RETAINED_PACKET_CLAIMS_COMPLETE_NEEDS_HUMAN_AUTHENTICATION')
    receipt={
        'schema':_receipt_schema,'compiler_id':_compiler_id,'repo':p['repo'],'pr_number':p['pr_number'],
        'candidate_head_sha':p['candidate_head_sha'],'provider_pr_head_sha':p['provider_pr_head_sha'],
        'base_sha':p['base_sha'],'current_main_sha':p['current_main_sha'],'evaluated_at_utc':_fmt_fn(now),
        'state':state,'reasons':reasons,'diagnostics':diagnostics,'input_digest_sha256':_digest_fn(p),
        'critical_blob_set_sha256':_digest_fn(_sorted(p['critical_blobs'],key=lambda x:x['path'])),
        'provenance':_provenance_fn(),'authority':_authority_fn(),
    }
    receipt['receipt_digest_sha256']=_digest_fn(receipt)
    return receipt

def _validate_receipt(r, _freeze_fn=_freeze, _exact_fn=_exact, _sha40_fn=_sha40, _ts_fn=_ts, _digest_fn=_digest, _authority_fn=_authority, _provenance_fn=_provenance, _receipt_schema=RECEIPT_SCHEMA, _compiler_id=COMPILER_ID, _states=STATES, _type=type, _list_type=list, _str_type=str, _dict_type=dict, _bool_type=bool, _set=set, _all=all, _any=any, _dict_ctor=dict, _fullmatch=re.fullmatch, _err=BrokerError):
    r=_freeze_fn(r)
    _exact_fn(r,{'schema','compiler_id','repo','pr_number','candidate_head_sha','provider_pr_head_sha','base_sha','current_main_sha','evaluated_at_utc','state','reasons','diagnostics','input_digest_sha256','critical_blob_set_sha256','provenance','authority','receipt_digest_sha256'},'receipt')
    if r['schema']!=_receipt_schema or r['compiler_id']!=_compiler_id or r['state'] not in _states: raise _err('receipt metadata')
    for f in ('candidate_head_sha','provider_pr_head_sha','base_sha','current_main_sha'): _sha40_fn(r[f],f)
    _ts_fn(r['evaluated_at_utc'],'evaluated_at_utc')
    if _type(r['reasons']) is not _list_type or not r['reasons'] or not _all(_type(x) is _str_type and x for x in r['reasons']): raise _err('reasons')
    if _type(r['diagnostics']) is not _dict_type: raise _err('diagnostics')
    for f in ('input_digest_sha256','critical_blob_set_sha256','receipt_digest_sha256'):
        if _type(r[f]) is not _str_type or not _fullmatch(r'^[0-9a-f]{64}$',r[f]): raise _err(f)
    expected_provenance=_provenance_fn()
    if _type(r['provenance']) is not _dict_type or r['provenance']!=expected_provenance or _any(_type(v) is not _bool_type or v is not False for v in r['provenance'].values()): raise _err('provenance')
    expected_keys=_set(_authority_fn())
    if _type(r['authority']) is not _dict_type or _set(r['authority'])!=expected_keys or _any(_type(v) is not _bool_type or v is not False for v in r['authority'].values()): raise _err('authority')
    unsigned=_dict_ctor(r); got=unsigned.pop('receipt_digest_sha256')
    if _digest_fn(unsigned)!=got: raise _err('receipt digest')
    return r

def verify_integrity(packet, receipt, _freeze_fn=_freeze, _valid_receipt=_validate_receipt, _ts_fn=_ts, _compile=_compile_at, _canonical_fn=_canonical):
    p=_freeze_fn(packet); r=_valid_receipt(receipt); at=_ts_fn(r['evaluated_at_utc'],'evaluated_at_utc')
    return _canonical_fn(_compile(p,at))==_canonical_fn(r)

def _projection(r):
    return {k:v for k,v in r.items() if k not in ('evaluated_at_utc','receipt_digest_sha256')}

def _verify_current_at(packet, receipt, now, _freeze_fn=_freeze, _valid_receipt=_validate_receipt, _ts_fn=_ts, _compile=_compile_at, _canonical_fn=_canonical, _projection_fn=_projection, _verify_integrity_fn=verify_integrity):
    p=_freeze_fn(packet); r=_valid_receipt(receipt); at=_ts_fn(r['evaluated_at_utc'],'evaluated_at_utc')
    if not _verify_integrity_fn(p,r): return False
    current=_compile(p,now)
    return _canonical_fn(_projection_fn(current))==_canonical_fn(_projection_fn(r))

def _make_current(compile_fn, freeze_fn, now_fn, utc):
    def compile_current(packet): return compile_fn(freeze_fn(packet),now_fn(utc))
    return compile_current

def _make_verify_current(fn, freeze_fn, now_fn, utc):
    def verify_current(packet,receipt): return fn(freeze_fn(packet),freeze_fn(receipt),now_fn(utc))
    return verify_current

compile_current=_make_current(_compile_at,_freeze,datetime.now,timezone.utc)
verify_current=_make_verify_current(_verify_current_at,_freeze,datetime.now,timezone.utc)
del _make_current, _make_verify_current
