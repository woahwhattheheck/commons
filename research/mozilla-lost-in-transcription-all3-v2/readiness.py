from __future__ import annotations
import argparse, json
from hashlib import sha256
from pathlib import Path
from core import TRACKS, canonical_json


def aggregate(paths: list[Path], output: Path) -> dict:
    if len(paths)!=3: raise ValueError('exactly three track receipts required')
    receipts=[json.loads(p.read_text(encoding='utf-8')) for p in paths]
    tracks=[r.get('track') for r in receipts]
    reasons=[]
    if set(tracks)!=TRACKS or len(set(tracks))!=3: reasons.append('receipts must cover each track exactly once')
    commits={r.get('runtime_commit') for r in receipts}
    if len(commits)!=1 or None in commits: reasons.append('runtime commit mismatch')
    if any(r.get('accepted') is not True for r in receipts): reasons.append('one or more local bundles not accepted')
    if any(r.get('internet_at_execution') is not False for r in receipts): reasons.append('offline runtime contract not proven')
    state='ALL_THREE_LOCAL_BUNDLES_STRUCTURALLY_READY' if not reasons else 'HOLD'
    canonical=[{"track":r.get('track'),"bundle_sha256":r.get('bundle_sha256'),"runtime_commit":r.get('runtime_commit')} for r in sorted(receipts,key=lambda x:str(x.get('track')))]
    result={"schema_version":1,"state":state,"provider_submission":False,"competition_terms_accepted":False,"score_claimed":False,"prize_claimed":False,
            "reasons":reasons,"receipts":canonical}
    result['receipt_sha256']=sha256(canonical_json(result).encode()).hexdigest()
    output.write_text(canonical_json(result),encoding='utf-8')
    return result

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('receipts',nargs=3,type=Path); ap.add_argument('--output',required=True,type=Path); a=ap.parse_args(); aggregate(a.receipts,a.output)
if __name__=='__main__': main()
