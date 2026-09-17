#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

CATALOG_SCHEMA='tjlabs.recon-portfolio.catalog/v1'
TARGETS_SCHEMA='tjlabs.recon-portfolio.target-bundle/v1'
PRODUCT_STATES={'MERGED_DELIVERABLE','OPEN_NEAR_SHIP','CONCEPT'}
ROUTE_STATES={'VERIFIED_CURRENT','HOLD_ROUTE','DNR_PROVIDER_SENT','PRODUCT_GATE_HOLD'}
ROUTE_KINDS={'EMAIL','FORM','SITE'}
SHA_RE=re.compile(r'^[0-9a-f]{40}$')
DOMAIN_RE=re.compile(r'^[a-z0-9][a-z0-9.-]+\.[a-z]{2,}$')

class PortfolioError(ValueError): pass

def _pairs(pairs):
    out={}
    for k,v in pairs:
        if k in out: raise PortfolioError(f'duplicate JSON key: {k}')
        out[k]=v
    return out

def load(path:Path)->Any:
    try:
        return json.loads(path.read_text(encoding='utf-8'),object_pairs_hook=_pairs,
                          parse_constant=lambda x: (_ for _ in ()).throw(PortfolioError(f'non-finite JSON: {x}')))
    except (json.JSONDecodeError,UnicodeError,OSError) as e:
        raise PortfolioError(f'{path}: {e}') from e

def load_targets_dir(path:Path)->dict[str,Any]:
    docs=[]
    for fp in sorted(path.glob('*.json')):
        doc=load(fp)
        _require(doc.get('schema')==TARGETS_SCHEMA,f'{fp}: target bundle schema')
        _require(doc.get('bundle_id')==fp.stem,f'{fp}: bundle_id/filename mismatch')
        docs.append(doc)
    _require(bool(docs),f'{path}: no target bundle files')
    dates={d.get('generated_on') for d in docs}
    _require(len(dates)==1,f'{path}: target generated_on mismatch')
    bundle_ids=[d['bundle_id'] for d in docs]
    _require(len(bundle_ids)==len(set(bundle_ids)),f'{path}: duplicate target bundle')
    return {'schema':'tjlabs.recon-portfolio.targets-aggregate/v1','generated_on':next(iter(dates)),'targets':[t for d in docs for t in d.get('targets',[])]}

def _require(cond:bool,msg:str):
    if not cond: raise PortfolioError(msg)

def _nonempty_strings(values:Any,where:str):
    _require(type(values) is list and values, f'{where}: expected non-empty list')
    for i,v in enumerate(values): _require(type(v) is str and v.strip(),f'{where}[{i}]: expected non-empty string')

def validate(catalog:dict[str,Any],targets_doc:dict[str,Any])->dict[str,Any]:
    _require(catalog.get('schema')==CATALOG_SCHEMA,'catalog schema')
    _require(targets_doc.get('schema')=='tjlabs.recon-portfolio.targets-aggregate/v1','targets aggregate schema')
    _require(type(catalog.get('generated_on')) is str,'catalog generated_on')
    _require(targets_doc.get('generated_on')==catalog.get('generated_on'),'generated_on mismatch')
    _require(type(catalog.get('global_outbound_rule')) is str and 'Muse' in catalog['global_outbound_rule'],'global outbound mutex missing')

    products=catalog.get('products'); bundles=catalog.get('bundles'); targets=targets_doc.get('targets')
    _require(type(products) is list and products,'products missing')
    _require(type(bundles) is list and 5 <= len(bundles) <= 8,'bundle count must be 5..8')
    _require(type(targets) is list and targets,'targets missing')

    by_product={}
    for p in products:
        _require(type(p) is dict,'product must be object')
        pid=p.get('id'); _require(type(pid) is str and pid not in by_product,f'duplicate/invalid product id: {pid}')
        by_product[pid]=p
        state=p.get('state'); _require(state in PRODUCT_STATES,f'{pid}: bad state')
        _require(p.get('commercial_state')=='PROPOSED_NOT_ACCEPTED',f'{pid}: commercial truth must remain proposed')
        repo=p.get('repo'); pr=p.get('pr'); pr_url=p.get('pr_url')
        _require(type(repo) is str and '/' in repo,f'{pid}: repo')
        _require(type(pr) is int and pr>0,f'{pid}: pr')
        _require(pr_url==f'https://github.com/{repo}/pull/{pr}',f'{pid}: PR URL mismatch')
        sha=p.get('merge_commit_sha')
        if state=='MERGED_DELIVERABLE': _require(type(sha) is str and SHA_RE.fullmatch(sha),f'{pid}: merged product needs merge SHA')
        else: _require(sha is None,f'{pid}: non-merged state cannot carry merge SHA')
        price=p.get('fixed_price_usd'); _require(type(price) is dict,'price object')
        lo,hi=price.get('min'),price.get('max')
        _require(type(lo) is int and type(hi) is int and 0 < lo <= hi,f'{pid}: invalid fixed price')
        monthly=p.get('optional_monthly_usd'); _require(monthly is None or (type(monthly) is int and monthly>0),f'{pid}: invalid monthly')
        _require(type(p.get('scope')) is str and p['scope'],f'{pid}: scope')
        _require(type(p.get('authority_ceiling')) is str and p['authority_ceiling'],f'{pid}: authority ceiling')
        if state=='OPEN_NEAR_SHIP': _require(type(p.get('blocking_truth')) is str and p['blocking_truth'],f'{pid}: blocking truth required')

    by_bundle={}
    for b in bundles:
        bid=b.get('id'); _require(type(bid) is str and bid not in by_bundle,f'duplicate/invalid bundle: {bid}')
        by_bundle[bid]=b
        refs=b.get('flagship_product_ids'); _require(type(refs) is list and refs,f'{bid}: flagship refs')
        _require(all(r in by_product for r in refs),f'{bid}: unknown flagship ref')
        all_merged=all(by_product[r]['state']=='MERGED_DELIVERABLE' for r in refs)
        _require(type(b.get('outreach_ready')) is bool,f'{bid}: outreach_ready bool')
        _require(b['outreach_ready']==all_merged,f'{bid}: outreach_ready must exactly track merged flagships')
        for field in ('evidence_intake','qualification_questions','disqualifiers','common_objections','authority_exclusions'):
            _nonempty_strings(b.get(field),f'{bid}.{field}')
        for field in ('buyer_profile','objection_response'):
            _require(type(b.get(field)) is str and b[field].strip(),f'{bid}.{field}')

    grouped=defaultdict(list)
    for t in targets:
        _require(type(t) is dict,'target must be object')
        bid=t.get('bundle_id'); _require(bid in by_bundle,f'target unknown bundle: {bid}')
        grouped[bid].append(t)
        _require(type(t.get('rank')) is int and t['rank']>0,f'{bid}: rank')
        _require(type(t.get('organization')) is str and t['organization'].strip(),f'{bid}: organization')
        domain=t.get('domain'); _require(type(domain) is str and DOMAIN_RE.fullmatch(domain),f'{bid}/{t.get("organization")}: domain')
        _require(type(t.get('fit_signal')) is int and 1 <= t['fit_signal'] <= 3,f'{bid}/{t.get("organization")}: fit signal')
        ev=t.get('evidence_url'); _require(type(ev) is str and ev.startswith('https://'),f'{bid}/{t.get("organization")}: https evidence URL')
        _require(type(t.get('evidence_signal')) is str and t['evidence_signal'].strip(),f'{bid}/{t.get("organization")}: evidence signal')
        route=t.get('contact_route'); _require(type(route) is dict,f'{bid}: contact route')
        _require(route.get('kind') in ROUTE_KINDS,f'{bid}/{t.get("organization")}: route kind')
        state=route.get('state'); _require(state in ROUTE_STATES,f'{bid}/{t.get("organization")}: route state')
        value=route.get('value'); _require(type(value) is str and value.strip(),f'{bid}/{t.get("organization")}: route value')
        if route['kind'] in {'FORM','SITE'}: _require(value.startswith('https://'),f'{bid}/{t.get("organization")}: web route must be https')
        if route['kind']=='EMAIL': _require('@' in value and ' ' not in value,f'{bid}/{t.get("organization")}: email route')
        _require(t.get('research_only') is True,f'{bid}/{t.get("organization")}: must be research_only')
        _require(t.get('outbound_authority') is False,f'{bid}/{t.get("organization")}: outbound authority forbidden')
        _require(t.get('source_checked_on')==catalog['generated_on'],f'{bid}/{t.get("organization")}: stale checked date')
        expected_action={'VERIFIED_CURRENT':'FRESH_SLACK_GMAIL_CENSUS_THEN_MUSE','HOLD_ROUTE':'VERIFY_COMMERCIAL_ROUTE','DNR_PROVIDER_SENT':'WAIT_FOR_GENUINE_INBOUND','PRODUCT_GATE_HOLD':'WAIT_FOR_PRODUCT_MERGE_AND_REVERIFY'}[state]
        _require(t.get('next_action')==expected_action,f'{bid}/{t.get("organization")}: next action/state mismatch')
        if not by_bundle[bid]['outreach_ready']:
            _require(state=='PRODUCT_GATE_HOLD',f'{bid}/{t.get("organization")}: non-ready bundle must product-gate every target')

    for bid in by_bundle:
        rows=grouped.get(bid,[])
        _require(len(rows)>=15,f'{bid}: needs >=15 targets, got {len(rows)}')
        ranks=sorted(t['rank'] for t in rows)
        _require(ranks==list(range(1,len(rows)+1)),f'{bid}: ranks must be contiguous 1..N')
        names=[t['organization'].lower() for t in rows]
        _require(len(names)==len(set(names)),f'{bid}: duplicate organization')

    counts=Counter(t['contact_route']['state'] for t in targets)
    return {'products':len(products),'bundles':len(bundles),'targets':len(targets),'route_states':dict(sorted(counts.items()))}

def main(argv=None)->int:
    ap=argparse.ArgumentParser()
    here=Path(__file__).resolve().parent
    ap.add_argument('--catalog',type=Path,default=here/'catalog.json')
    ap.add_argument('--targets-dir',type=Path,default=here/'targets')
    ns=ap.parse_args(argv)
    try:
        summary=validate(load(ns.catalog),load_targets_dir(ns.targets_dir))
    except PortfolioError as e:
        print(f'INVALID: {e}')
        return 2
    print(json.dumps({'status':'VALID',**summary},sort_keys=True))
    return 0
if __name__=='__main__': raise SystemExit(main())
