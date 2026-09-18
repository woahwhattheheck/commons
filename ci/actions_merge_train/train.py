"""Train-level composition, receipts, verification, and Markdown rendering."""
from __future__ import annotations
import re
from collections import Counter
from typing import Any, Sequence
from contract import *  # noqa:F401,F403
from workflow import *  # noqa:F401,F403

def compile_capture(raw):
 c=normalize_capture(raw); workflows=[workflow_result(w,c['repository'],c['head_sha']) for w in c['workflows']]
 seen={}
 for w in workflows:
  for r in w['latest_attempts']+w['replaced_attempts']:
   key=(r['run_id'],r['run_attempt'])
   if key in seen: raise EvidenceError(f"run_id/run_attempt appears in multiple workflows: {seen[key]!r}, {w['name']!r}")
   seen[key]=w['name']
 reasons=[]
 if c['topology']['state']!='CURRENT': reasons.append('TOPOLOGY_NOT_CURRENT')
 rs=c['source_review']['state']
 if rs=='RED': reasons.append('SOURCE_REVIEW_RED')
 elif rs!='GREEN': reasons.append('SOURCE_REVIEW_NOT_GREEN')
 d={w['disposition'] for w in workflows}
 if 'HOLD_AMBIGUOUS' in d: reasons.append('EXECUTION_AMBIGUOUS')
 if 'SOURCE_EXECUTED_RED' in d: reasons.append('SOURCE_EXECUTED_RED')
 if 'EVIDENCE_ABSENT' in d: reasons.append('EXECUTION_EVIDENCE_ABSENT')
 if 'PROVIDER_QUEUED' in d: reasons.append('PROVIDER_QUEUED')
 if d&{'PROVIDER_NO_RUN','PROVIDER_CANCELLED_BEFORE_EXECUTION'}: reasons.append('PROVIDER_STARVATION')
 ordered=[r for r in HOLD_PRIORITY if r in set(reasons)]; overall='READY_FOR_GUARDED_REVIEW' if not ordered else OVERALL_BY_REASON[ordered[0]]
 if overall=='READY_FOR_GUARDED_REVIEW' and any(w['disposition']!='SOURCE_EXECUTED_GREEN' for w in workflows): raise EvidenceError('internal invariant: guarded-review readiness requires all workflows source-executed green')
 provider=bool(d&{'PROVIDER_NO_RUN','PROVIDER_QUEUED','PROVIDER_CANCELLED_BEFORE_EXECUTION'})
 return {'repository':c['repository'],'pr_number':c['pr_number'],'head_sha':c['head_sha'],'overall_disposition':overall,'hold_reasons':ordered,'source_review':c['source_review'],'topology':c['topology'],'workflows':workflows,'work_feed_projection':{'repository':c['repository'],'pr_number':c['pr_number'],'head_sha':c['head_sha'],'state':overall,'first_hold_reason':ordered[0] if ordered else None,'provider_hold':provider,'merge_authorized':False},'source_regression_proven':False,'merge_authorized':False,'workflow_mutation_authorized':False}

def compile_train(raws:Sequence[Any]):
 if not raws or len(raws)>MAX_CAPTURES: raise EvidenceError(f'expected 1..{MAX_CAPTURES} captures')
 prs=[compile_capture(r) for r in raws]; keys=[(r['repository'],r['pr_number']) for r in prs]
 if len(keys)!=len(set(keys)): raise EvidenceError('duplicate repository/pr_number capture')
 prs.sort(key=lambda r:(r['repository'],r['pr_number'],r['head_sha'])); counts=Counter(r['overall_disposition'] for r in prs); ready=counts.get('READY_FOR_GUARDED_REVIEW',0)
 receipt={'schema':RECEIPT_SCHEMA,'prs':prs,'aggregate':{'pr_count':len(prs),'ready_for_guarded_review_count':ready,'hold_count':len(prs)-ready,'provider_hold_pr_count':sum(r['work_feed_projection']['provider_hold'] for r in prs),'overall_disposition_counts':dict(sorted(counts.items())),'merge_authorized':False,'workflow_mutation_authorized':False}}
 receipt['receipt_sha256']=digest(receipt); return receipt

def verify_receipt(supplied,raws):
 recomputed=compile_train(raws); reasons=[]; supplied_sha=None
 if type(supplied) is not dict: reasons.append('SUPPLIED_RECEIPT_NOT_OBJECT')
 else:
  v=supplied.get('receipt_sha256'); supplied_sha=v if type(v) is str else None
  if supplied.get('schema')!=RECEIPT_SCHEMA: reasons.append('SUPPLIED_RECEIPT_SCHEMA_MISMATCH')
  if type(v) is not str or not re.fullmatch(r'[0-9a-f]{64}',v): reasons.append('SUPPLIED_RECEIPT_DIGEST_INVALID')
  else:
   p=dict(supplied); p.pop('receipt_sha256',None)
   if digest(p)!=v: reasons.append('SUPPLIED_RECEIPT_DIGEST_MISMATCH')
  if supplied!=recomputed: reasons.append('RECEIPT_RECOMPUTE_MISMATCH')
 return {'schema':VERIFY_SCHEMA,'valid':not reasons,'reason_codes':sorted(set(reasons)),'supplied_receipt_sha256':supplied_sha,'recomputed_receipt_sha256':recomputed['receipt_sha256']}

def render_markdown(receipt):
 if type(receipt) is not dict or receipt.get('schema')!=RECEIPT_SCHEMA: raise EvidenceError('markdown: expected compiled merge-train receipt')
 lines=['# Actions merge-train advisory report','',f"Receipt: `{receipt.get('receipt_sha256','UNKNOWN')}`",'','This report is advisory only. `READY_FOR_GUARDED_REVIEW` is not merge authorization.','','| Repository | PR | Head | Disposition | First hold | Provider hold |','| --- | ---: | --- | --- | --- | --- |']
 for r in receipt['prs']:
  p=r['work_feed_projection']; lines.append(f"| {r['repository']} | #{r['pr_number']} | `{r['head_sha'][:12]}` | {r['overall_disposition']} | {p['first_hold_reason'] or '-'} | {'yes' if p['provider_hold'] else 'no'} |")
 lines+=['','## Workflow evidence','']
 for r in receipt['prs']:
  lines += [f"### {r['repository']} PR #{r['pr_number']} @ `{r['head_sha']}`",'']
  for w in r['workflows']: lines.append(f"- `{w['name']}`: **{w['disposition']}**; rerun advice `{w['rerun_advice']}`; attempts {w['all_attempt_count']}")
  lines.append(f"- Hold reasons: {', '.join(r['hold_reasons'])}" if r['hold_reasons'] else '- Hold reasons: none; guarded human/current-head review is still required.'); lines.append('')
 return '\n'.join(lines).rstrip()+'\n'
