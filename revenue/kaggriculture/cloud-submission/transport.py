"""Single designated direct-file submission via the official Kaggle client.

Credentials belong in the already-configured caller runtime, never arguments or
receipts. Provider readback and a stable operation description prevent blind
retry after an uncertain upload/create result. No notebook commit prerequisite.
"""
from __future__ import annotations
import argparse,contextlib,datetime,hashlib,io,json,os
from pathlib import Path

OPERATION_ID='titan-kaggriculture-frontier-20260907-01'
COMPETITION='kaggriculture'


def plain(value):
    if hasattr(value,'to_dict'):return value.to_dict()
    if isinstance(value,list):return [plain(v) for v in value]
    return value


def matching(rows, operation_id):
    return [plain(row) for row in (rows or []) if operation_id in (getattr(row,'description',None) or (row.get('description','') if isinstance(row,dict) else ''))]


def snapshot(api, operation_id=OPERATION_ID):
    submissions=api.competition_submissions(COMPETITION,page_size=100)
    limits=api.competition_get_submission_limits(COMPETITION)
    return {'limits':plain(limits),'matching_submissions':matching(submissions,operation_id),
            'recent_submissions':plain(submissions)}


def execute(api, artifact, expected_sha256, state_dir, operation_id=OPERATION_ID, description=None):
    artifact=Path(artifact);state_dir=Path(state_dir);state_dir.mkdir(parents=True,exist_ok=True)
    actual=hashlib.sha256(artifact.read_bytes()).hexdigest()
    if actual!=expected_sha256:raise ValueError('Designated artifact SHA256 mismatch')
    marker=description or f'{operation_id} sha256:{actual}'
    if operation_id not in marker:raise ValueError('Description must contain stable operation ID')
    journal=state_dir/(operation_id+'.json')
    # Read provider BEFORE local retry decision: a previous create may have
    # succeeded even if the requesting process lost its response.
    before=snapshot(api,operation_id)
    if before['matching_submissions']:
        return {'status':'ALREADY_PRESENT','artifact_sha256':actual,'readback':before}
    if journal.exists():
        previous=json.loads(journal.read_text())
        return {'status':'RECONCILE_REQUIRED','previous':previous,'readback':before}
    if before['limits'].get('numAllowedNow',before['limits'].get('num_allowed_now',0))<1:
        return {'status':'NO_CURRENT_ALLOWANCE','readback':before}
    record={'operation_id':operation_id,'competition':COMPETITION,'artifact_sha256':actual,
            'artifact_name':artifact.name,'artifact_bytes':artifact.stat().st_size,
            'description':marker,'status':'DISPATCH_STARTED',
            'started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'before':before}
    # Exclusive create coordinates this runtime. No server idempotency claim.
    with journal.open('x') as stream:json.dump(record,stream,indent=2,default=str)
    try:
        with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
            response=api.competition_submit(str(artifact),marker,COMPETITION,quiet=True)
        record['provider_response']=plain(response)
        record['status']='PROVIDER_RESPONSE_RECEIVED'
    except Exception as exc:
        record['status']='OUTCOME_UNKNOWN';record['exception_type']=type(exc).__name__
    journal.write_text(json.dumps(record,indent=2,default=str)+'\n')
    try:
        record['after']=snapshot(api,operation_id)
        record['status']='SUBMISSION_FOUND' if record['after']['matching_submissions'] else 'AWAITING_PROVIDER_READBACK'
    except Exception as exc:
        record['readback_exception_type']=type(exc).__name__
    journal.write_text(json.dumps(record,indent=2,default=str)+'\n')
    return record

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifact',type=Path,required=True)
    parser.add_argument('--sha256',required=True,help='Exact archive hash designated by root')
    parser.add_argument('--state-dir',type=Path,required=True)
    args=parser.parse_args()
    from kaggle.api.kaggle_api_extended import KaggleApi
    api=KaggleApi();api.authenticate()
    result=execute(api,args.artifact,args.sha256,args.state_dir)
    print(json.dumps(result,default=str))
