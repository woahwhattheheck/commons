#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path
from validate import load, load_targets_dir, validate

def money(p):
    lo,hi=p['fixed_price_usd']['min'],p['fixed_price_usd']['max']
    fixed=f'${lo:,}' if lo==hi else f'${lo:,}–${hi:,}'
    m=p['optional_monthly_usd']
    return fixed + (f' + optional ${m:,}/month' if m else '')

def render(catalog,targets_doc):
    validate(catalog,targets_doc)
    products={p['id']:p for p in catalog['products']}
    grouped={b['id']:[] for b in catalog['bundles']}
    for t in targets_doc['targets']: grouped[t['bundle_id']].append(t)
    lines=['# Reconciliation Portfolio — vertical packaging and target queue','',
           f"Generated from verified source receipts and research checked **{catalog['generated_on']}**.",
           '', '> **Truth ceiling:** every commercial term below is `PROPOSED_NOT_ACCEPTED`. This catalog never grants outbound authority. '+catalog['global_outbound_rule'],'',
           '## Product truth registry','',
           '| Product | State | Provider receipt | Commercial hypothesis | Outreach gate |','|---|---|---|---|---|']
    for p in catalog['products']:
        receipt=f"[{p['repo']}#{p['pr']}]({p['pr_url']})"
        if p['merge_commit_sha']: receipt+=f" · `{p['merge_commit_sha'][:12]}…`"
        gate='eligible for packaging; fresh coordination still mandatory' if p['state']=='MERGED_DELIVERABLE' else 'HOLD — not merged / unresolved gates'
        lines.append(f"| {p['name']} | `{p['state']}` | {receipt} | {money(p)} | {gate} |")
    for b in catalog['bundles']:
        refs=[products[x] for x in b['flagship_product_ids']]
        rows=sorted(grouped[b['id']],key=lambda x:x['rank'])
        lines += ['',f"## {b['name']}",'',f"**Bundle state:** `{'OUTREACH_PACKAGING_READY' if b['outreach_ready'] else 'PRODUCT_GATE_HOLD'}` · **Target count:** {len(rows)}",'',f"**Buyer profile:** {b['buyer_profile']}",'',f"**Flagship:** {', '.join(p['name'] for p in refs)} · **Commercial hypothesis:** {', '.join(money(p) for p in refs)}",'',f"**Scope:** {' | '.join(p['scope'] for p in refs)}",'', '**Evidence intake**','']
        lines += [f"- {x}" for x in b['evidence_intake']]
        lines += ['','**Qualification**','']+[f"- {x}" for x in b['qualification_questions']]
        lines += ['','**Disqualify / stop**','']+[f"- {x}" for x in b['disqualifiers']]
        lines += ['','**Common objections**','']+[f"- {x}" for x in b['common_objections']]
        lines += ['',f"**Response frame:** {b['objection_response']}",'','**Authority exclusions**','']+[f"- {x}" for x in b['authority_exclusions']]
        lines += ['','### Research-only target queue','', '| # | Organization | Fit | Route state | Evidence | Next action |','|---:|---|---:|---|---|---|']
        for t in rows:
            ev=f"[source]({t['evidence_url']})"
            lines.append(f"| {t['rank']} | {t['organization']} | {t['fit_signal']}/3 | `{t['contact_route']['state']}` | {ev} — {t['evidence_signal']} | `{t['next_action']}` |")
    lines += ['','## Refresh contract','',
              '1. Re-verify product receipts against provider truth. A non-merged carrier is `OPEN_NEAR_SHIP`, never a sellable deliverable.',
              '2. Refresh first-party target evidence and route provenance. Weak or support-only routing stays `HOLD_ROUTE`.',
              '3. Preserve provider-SENT DNR until a genuine human/provider event; do not silently recycle a route.',
              '4. Run `python revenue/recon_portfolio/validate.py` and render a fresh human-readable view from source JSON.',
              '5. External outreach is a separate operation: fresh Slack/Gmail collision census → Muse single-writer election → immediate recensus → at most one selected send.','']
    return '\n'.join(lines)

def main(argv=None):
    ap=argparse.ArgumentParser(); here=Path(__file__).resolve().parent
    ap.add_argument('--catalog',type=Path,default=here/'catalog.json'); ap.add_argument('--targets-dir',type=Path,default=here/'targets')
    ap.add_argument('--output',type=Path); ns=ap.parse_args(argv)
    text=render(load(ns.catalog),load_targets_dir(ns.targets_dir))
    if ns.output:
        ns.output.write_text(text,encoding='utf-8'); print(ns.output)
    else:
        print(text)
    return 0
if __name__=='__main__': raise SystemExit(main())
