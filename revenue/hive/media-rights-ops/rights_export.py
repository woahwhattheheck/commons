"""Deterministic create-exclusive exports."""
import csv,io,os
from pathlib import Path
from rights_model import *
from rights_store import snapshot,queues
def export_files(path,as_of,horizon_days=30):
    snap=snapshot(path); q=queues(path,as_of,horizon_days); out={'snapshot.json':canonical_bytes(snap),'queues.json':canonical_bytes(q)}; s=io.StringIO(newline=''); w=csv.writer(s,lineterminator='\n'); cols=('request_id','asset_id','channel','territory','starts_at','ends_at','grant_id','recorded_at'); w.writerow(cols)
    for p in snap['placements']: w.writerow([p[k] for k in cols])
    out['placements.csv']=s.getvalue().encode(); lines=['# Content Rights & Usage-Window Operations Desk','',f"Snapshot SHA-256: `{snap['snapshot_sha256']}`",'',f"Assets: {len(snap['assets'])}",f"Grants: {len(snap['grants'])}",f"Placements: {len(snap['placements'])}",f"Renewal/expiry review rows: {len(q['renewal_review'])}",f"Retraction review rows: {len(q['retraction_review'])}",'','Operational gate only: supplied authority facts are not a legal rights determination.','']; out['summary.md']='\n'.join(lines).encode(); receipt={'schema':RECEIPT_SCHEMA,'snapshot_sha256':snap['snapshot_sha256'],'files':[{'path':n,'bytes':len(b),'sha256':sha256_bytes(b)} for n,b in sorted(out.items())]}; out['receipt.json']=canonical_bytes(receipt); return out
def publish_export(path,out_dir,as_of,horizon_days=30):
    out_dir=Path(out_dir); out_dir.parent.mkdir(parents=True,exist_ok=True); files=export_files(path,as_of,horizon_days)
    try: out_dir.mkdir(mode=0o700)
    except FileExistsError as e: raise RightsError(f'refusing to overwrite existing output: {out_dir}') from e
    try:
        for name,raw in sorted(files.items()):
            fd=os.open(out_dir/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
            with os.fdopen(fd,'wb') as f: f.write(raw); f.flush(); os.fsync(f.fileno())
        return {'status':'EXPORTED','output':str(out_dir),'files':len(files),'receipt_sha256':sha256_bytes(files['receipt.json'])}
    except Exception:
        for child in out_dir.iterdir(): child.unlink()
        out_dir.rmdir(); raise
