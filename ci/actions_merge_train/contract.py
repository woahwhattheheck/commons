"""Strict input contract and bridge to the retained execution-truth classifier."""
from __future__ import annotations
import re, sys
from pathlib import Path
from typing import Any
HERE=Path(__file__).resolve().parent
PRED=HERE.parent/'actions_execution_truth'
if str(PRED) not in sys.path: sys.path.insert(0,str(PRED))
from schema import EvidenceError, canonical_bytes, digest, loads_strict  # type: ignore  # noqa:E402
from truth import classify_case  # type: ignore  # noqa:E402

CAPTURE_SCHEMA='commons-actions-merge-train-capture/v1'
REVIEW_SCHEMA='commons-source-review-capture/v1'
TOPOLOGY_SCHEMA='commons-pr-topology-capture/v1'
RECEIPT_SCHEMA='commons-actions-merge-train-receipt/v1'
VERIFY_SCHEMA='commons-actions-merge-train-verification/v1'
MAX_CAPTURES=64; MAX_WORKFLOWS=64; MAX_CASES_PER_WORKFLOW=32; MAX_WORKFLOW_NAME=160
SHA_RE=re.compile(r'^[0-9a-f]{40}$'); REPO_RE=re.compile(r'^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$')
REVIEW_STATES={'GREEN','RED','ABSENT','AMBIGUOUS'}; TOPOLOGY_STATES={'CURRENT','STALE','ABSENT','AMBIGUOUS'}

def exact(v,keys,where):
 if type(v) is not dict: raise EvidenceError(f'{where}: expected object')
 a=set(v)
 if a!=keys: raise EvidenceError(f'{where}: schema mismatch missing={sorted(keys-a)} extra={sorted(a-keys)}')
 return v
def text(v,where,n=512):
 if type(v) is not str or not v or len(v)>n: raise EvidenceError(f'{where}: expected non-empty string <= {n} characters')
 return v
def pos(v,where):
 if type(v) is not int or v<=0: raise EvidenceError(f'{where}: expected positive integer (bool is not int)')
 return v
def nonneg(v,where):
 if type(v) is not int or v<0: raise EvidenceError(f'{where}: expected non-negative integer (bool is not int)')
 return v
def sha(v,where):
 v=text(v,where,40)
 if not SHA_RE.fullmatch(v): raise EvidenceError(f'{where}: expected lowercase 40-hex commit SHA')
 return v
def repo(v,where):
 v=text(v,where)
 if not REPO_RE.fullmatch(v): raise EvidenceError(f'{where}: expected owner/name')
 return v
def opt_pos(v,where): return None if v is None else pos(v,where)
def opt_sha(v,where): return None if v is None else sha(v,where)

def normalize_review(raw):
 x=exact(raw,{'schema','repository','pr_number','head_sha','state','review_id'},'source_review')
 if x['schema']!=REVIEW_SCHEMA: raise EvidenceError('source_review: wrong schema')
 state=text(x['state'],'source_review.state',16)
 if state not in REVIEW_STATES: raise EvidenceError(f'source_review.state: unexpected value {state!r}')
 rid=opt_pos(x['review_id'],'source_review.review_id')
 if state in {'GREEN','RED'} and rid is None: raise EvidenceError('source_review: GREEN/RED requires review_id')
 if state=='ABSENT' and rid is not None: raise EvidenceError('source_review: ABSENT requires null review_id')
 return {'schema':REVIEW_SCHEMA,'repository':repo(x['repository'],'source_review.repository'),'pr_number':pos(x['pr_number'],'source_review.pr_number'),'head_sha':sha(x['head_sha'],'source_review.head_sha'),'state':state,'review_id':rid}

def normalize_topology(raw):
 x=exact(raw,{'schema','repository','pr_number','head_sha','base_sha','behind_by','state','required_workflows'},'topology')
 if x['schema']!=TOPOLOGY_SCHEMA: raise EvidenceError('topology: wrong schema')
 state=text(x['state'],'topology.state',16)
 if state not in TOPOLOGY_STATES: raise EvidenceError(f'topology.state: unexpected value {state!r}')
 base=opt_sha(x['base_sha'],'topology.base_sha'); behind=None if x['behind_by'] is None else nonneg(x['behind_by'],'topology.behind_by')
 if state=='CURRENT' and (base is None or behind!=0): raise EvidenceError('topology: CURRENT requires base_sha and behind_by=0')
 if state=='ABSENT' and (base is not None or behind is not None): raise EvidenceError('topology: ABSENT requires null base_sha/behind_by')
 raw_names=x['required_workflows']
 if type(raw_names) is not list or not raw_names or len(raw_names)>MAX_WORKFLOWS: raise EvidenceError(f'topology.required_workflows: expected 1..{MAX_WORKFLOWS} names')
 names=[text(n,'topology.required_workflows[]',MAX_WORKFLOW_NAME) for n in raw_names]
 if len(names)!=len(set(names)): raise EvidenceError('topology.required_workflows: duplicate workflow name')
 return {'schema':TOPOLOGY_SCHEMA,'repository':repo(x['repository'],'topology.repository'),'pr_number':pos(x['pr_number'],'topology.pr_number'),'head_sha':sha(x['head_sha'],'topology.head_sha'),'base_sha':base,'behind_by':behind,'state':state,'required_workflows':sorted(names)}

def normalize_capture(raw):
 x=exact(raw,{'schema','repository','pr_number','head_sha','workflows','source_review','topology'},'capture')
 if x['schema']!=CAPTURE_SCHEMA: raise EvidenceError('capture: wrong schema')
 repository=repo(x['repository'],'capture.repository'); pr=pos(x['pr_number'],'capture.pr_number'); head=sha(x['head_sha'],'capture.head_sha')
 review=normalize_review(x['source_review']); topology=normalize_topology(x['topology'])
 for label,e in (('source_review',review),('topology',topology)):
  if (e['repository'],e['pr_number'],e['head_sha'])!=(repository,pr,head): raise EvidenceError(f'capture/{label} repository/pr/head binding mismatch')
 raw_w=x['workflows']
 if type(raw_w) is not list or not raw_w or len(raw_w)>MAX_WORKFLOWS: raise EvidenceError(f'capture.workflows: expected 1..{MAX_WORKFLOWS} workflow groups')
 out=[]; names=[]
 for i,wraw in enumerate(raw_w,1):
  w=exact(wraw,{'name','cases'},f'workflow {i}'); name=text(w['name'],f'workflow {i}.name',MAX_WORKFLOW_NAME); cases=w['cases']
  if type(cases) is not list or len(cases)>MAX_CASES_PER_WORKFLOW: raise EvidenceError(f'workflow {name}.cases: expected list <= {MAX_CASES_PER_WORKFLOW}')
  pairs=[]
  for j,craw in enumerate(cases,1):
   c=exact(craw,{'run','jobs'},f'workflow {name} case {j}'); pairs.append({'run':c['run'],'jobs':c['jobs']})
  out.append({'name':name,'cases':pairs}); names.append(name)
 if len(names)!=len(set(names)): raise EvidenceError('capture.workflows: duplicate workflow name')
 if sorted(names)!=topology['required_workflows']: raise EvidenceError('capture.workflows do not exactly match topology.required_workflows')
 out.sort(key=lambda r:r['name'])
 return {'schema':CAPTURE_SCHEMA,'repository':repository,'pr_number':pr,'head_sha':head,'workflows':out,'source_review':review,'topology':topology}
