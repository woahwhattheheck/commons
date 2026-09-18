"""Conservative merge-train composition over retained Actions execution truth."""
from __future__ import annotations
import re
from collections import Counter, defaultdict
from typing import Any, Sequence
from contract import *  # noqa:F401,F403

HOLD_PRIORITY=('TOPOLOGY_NOT_CURRENT','SOURCE_REVIEW_RED','SOURCE_REVIEW_NOT_GREEN','EXECUTION_AMBIGUOUS','SOURCE_EXECUTED_RED','EXECUTION_EVIDENCE_ABSENT','PROVIDER_QUEUED','PROVIDER_STARVATION')
OVERALL_BY_REASON={'TOPOLOGY_NOT_CURRENT':'HOLD_TOPOLOGY','SOURCE_REVIEW_RED':'HOLD_SOURCE_REVIEW_RED','SOURCE_REVIEW_NOT_GREEN':'HOLD_SOURCE_REVIEW','EXECUTION_AMBIGUOUS':'HOLD_AMBIGUOUS','SOURCE_EXECUTED_RED':'HOLD_SOURCE_EXECUTED_RED','EXECUTION_EVIDENCE_ABSENT':'HOLD_EVIDENCE_ABSENT','PROVIDER_QUEUED':'HOLD_PROVIDER_QUEUED','PROVIDER_STARVATION':'HOLD_PROVIDER_STARVATION'}

def row_disposition(row):
 s=row['classification']
 if s=='EXECUTED_GREEN': return 'SOURCE_EXECUTED_GREEN'
 if s=='EXECUTED_NON_GREEN': return 'SOURCE_EXECUTED_RED'
 if s=='NOT_EXECUTED_RUNNER_UNASSIGNED': return 'PROVIDER_CANCELLED_BEFORE_EXECUTION' if row['run_conclusion']=='cancelled' else 'PROVIDER_NO_RUN'
 if s=='PENDING_EXECUTION' and row['run_status'] in {'queued','waiting','requested','pending'}: return 'PROVIDER_QUEUED'
 return 'HOLD_AMBIGUOUS'

def workflow_result(w,repository,head):
 rows=[]; seen=set(); by_run=defaultdict(list)
 for c in w['cases']:
  r=classify_case(c['run'],c['jobs'])
  if r['repository']!=repository or r['head_sha']!=head: raise EvidenceError(f"workflow {w['name']}: run evidence does not bind capture repository/head")
  key=(r['run_id'],r['run_attempt'])
  if key in seen: raise EvidenceError(f"workflow {w['name']}: duplicate run_id/run_attempt")
  seen.add(key); rows.append(r); by_run[r['run_id']].append(r)
 rows.sort(key=lambda r:(r['run_id'],r['run_attempt']))
 if not rows: return {'name':w['name'],'disposition':'EVIDENCE_ABSENT','latest_attempts':[],'replaced_attempts':[],'all_attempt_count':0,'provider_hold_attempt_count':0,'rerun_advice':'CAPTURE_EVIDENCE_FIRST','source_regression_proven':False,'merge_authorized':False}
 latest=[]; replaced=[]
 for run_id in sorted(by_run):
  ordered=sorted(by_run[run_id],key=lambda r:r['run_attempt']); latest.append(ordered[-1]); replaced.extend(ordered[:-1])
 kinds={row_disposition(r) for r in latest}
 if 'HOLD_AMBIGUOUS' in kinds or {'SOURCE_EXECUTED_GREEN','SOURCE_EXECUTED_RED'}<=kinds: disp='HOLD_AMBIGUOUS'
 elif 'SOURCE_EXECUTED_RED' in kinds: disp='SOURCE_EXECUTED_RED'
 elif 'SOURCE_EXECUTED_GREEN' in kinds: disp='SOURCE_EXECUTED_GREEN'
 elif 'PROVIDER_QUEUED' in kinds: disp='PROVIDER_QUEUED'
 elif 'PROVIDER_NO_RUN' in kinds: disp='PROVIDER_NO_RUN'
 elif kinds=={'PROVIDER_CANCELLED_BEFORE_EXECUTION'}: disp='PROVIDER_CANCELLED_BEFORE_EXECUTION'
 else: disp='HOLD_AMBIGUOUS'
 holds=sum(row_disposition(r) in {'PROVIDER_NO_RUN','PROVIDER_QUEUED','PROVIDER_CANCELLED_BEFORE_EXECUTION'} for r in rows)
 if disp in {'SOURCE_EXECUTED_GREEN','SOURCE_EXECUTED_RED'}: advice='NO_PROVIDER_RERUN_ADVICE_SOURCE_EXECUTED'
 elif disp=='HOLD_AMBIGUOUS': advice='DO_NOT_RERUN_AMBIGUOUS'
 elif disp=='PROVIDER_QUEUED': advice='WAIT_FOR_PROVIDER_QUEUE'
 elif holds>=2: advice='BACKOFF_PROVIDER_STORM'
 else: advice='BACKOFF_UNTIL_PROVIDER_HEALTH_CONFIRMED'
 mini=lambda r:{'run_id':r['run_id'],'run_attempt':r['run_attempt'],'classification':r['classification'],'operational_disposition':row_disposition(r),'run_status':r['run_status'],'run_conclusion':r['run_conclusion'],'executed_step_count':r['executed_step_count'],'capture_projection_sha256':r['capture_projection_sha256']}
 short=lambda r:{'run_id':r['run_id'],'run_attempt':r['run_attempt'],'classification':r['classification'],'operational_disposition':row_disposition(r),'capture_projection_sha256':r['capture_projection_sha256']}
 return {'name':w['name'],'disposition':disp,'latest_attempts':[mini(r) for r in latest],'replaced_attempts':[short(r) for r in replaced],'all_attempt_count':len(rows),'provider_hold_attempt_count':holds,'rerun_advice':advice,'source_regression_proven':False,'merge_authorized':False}

