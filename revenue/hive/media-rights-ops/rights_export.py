"""Deterministic exports into a retained, pre-provisioned directory generation."""
import csv,io,os,stat
from pathlib import Path
from rights_model import *
from rights_store import connect,snapshot,queues

def export_files(path,as_of,horizon_days=30):
    # snapshot() and queues() each use their own read connection. Hold SQLite's
    # single-writer reservation across both reads so no durable placement/revoke
    # generation can commit between them. BEGIN IMMEDIATE waits out any prior
    # writer first; the transaction performs no writes and is rolled back after
    # the two deterministic reads have been captured.
    guard=connect(path)
    try:
        guard.execute('BEGIN IMMEDIATE')
        snap=snapshot(path)
        q=queues(path,as_of,horizon_days)
    finally:
        if guard.in_transaction: guard.execute('ROLLBACK')
        guard.close()
    out={'snapshot.json':canonical_bytes(snap),'queues.json':canonical_bytes(q)}; s=io.StringIO(newline=''); w=csv.writer(s,lineterminator='\n'); cols=('request_id','asset_id','channel','territory','starts_at','ends_at','grant_id','recorded_at'); w.writerow(cols)
    for p in snap['placements']: w.writerow([p[k] for k in cols])
    out['placements.csv']=s.getvalue().encode(); lines=['# Content Rights & Usage-Window Operations Desk','',f"Snapshot SHA-256: `{snap['snapshot_sha256']}`",'',f"Assets: {len(snap['assets'])}",f"Grants: {len(snap['grants'])}",f"Placements: {len(snap['placements'])}",f"Renewal/expiry review rows: {len(q['renewal_review'])}",f"Retraction review rows: {len(q['retraction_review'])}",'','Operational gate only: supplied authority facts are not a legal rights determination.','']; out['summary.md']='\n'.join(lines).encode(); receipt={'schema':RECEIPT_SCHEMA,'snapshot_sha256':snap['snapshot_sha256'],'files':[{'path':n,'bytes':len(b),'sha256':sha256_bytes(b)} for n,b in sorted(out.items())]}; out['receipt.json']=canonical_bytes(receipt); return out

def _same_identity(st,identity):
    return (st.st_dev,st.st_ino)==identity

# Capability is a platform/process property. Capture it before hostile tests (or
# other instrumentation) monkey-patch individual os functions; the publication
# path still invokes the current functions and therefore remains fully testable.
_SECURE_EXPORT_SUPPORTED=(hasattr(os,'O_DIRECTORY') and hasattr(os,'O_NOFOLLOW') and all(fn in os.supports_dir_fd for fn in (os.open,os.stat,os.unlink)) and os.listdir in os.supports_fd)
def _secure_export_supported(): return _SECURE_EXPORT_SUPPORTED

def _entry_stat(name,dir_fd):
    return os.stat(name,dir_fd=dir_fd,follow_symlinks=False)

def _open_retained_output(out_dir):
    # Publication consumes an already-provisioned directory. Snapshot its exact
    # generation before open, refuse a symlink/non-directory, then prove the
    # opened descriptor is the same object. There is no mkdir->open adoption gap.
    try: before=os.stat(out_dir,follow_symlinks=False)
    except FileNotFoundError as e: raise RightsError(f'output directory must already exist: {out_dir}') from e
    require(stat.S_ISDIR(before.st_mode),'output must be a real directory, not a symlink or other file')
    identity=(before.st_dev,before.st_ino); fd=None
    try:
        fd=os.open(out_dir,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        current=os.fstat(fd); require(stat.S_ISDIR(current.st_mode) and _same_identity(current,identity),'output directory identity changed during publication')
        require(os.listdir(fd)==[],'output directory must be empty before publication')
        return fd,identity
    except Exception:
        if fd is not None: os.close(fd)
        raise

def _rollback_created(dir_fd,created):
    # Remove only leaf identities created by this transaction. A replacement leaf
    # or any foreign entry is deliberately preserved rather than followed by name.
    for name,identity in reversed(created):
        try:
            current=_entry_stat(name,dir_fd)
            if stat.S_ISREG(current.st_mode) and _same_identity(current,identity): os.unlink(name,dir_fd=dir_fd)
        except FileNotFoundError: pass
        except OSError: pass
    try: os.fsync(dir_fd)
    except OSError: pass

def publish_export(path,out_dir,as_of,horizon_days=30):
    out_dir=Path(out_dir); require(out_dir.name not in {'','.','..'},'output path must name a directory'); files=export_files(path,as_of,horizon_days)
    require(_secure_export_supported(),'secure export publication requires descriptor-relative no-follow filesystem support')
    dir_fd,dir_identity=_open_retained_output(out_dir); created=[]
    try:
        try:
            for name,raw in sorted(files.items()):
                require('/' not in name and '\\' not in name and name not in {'','.','..'},'export leaf name invalid')
                fd=os.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=dir_fd)
                fst=os.fstat(fd); identity=(fst.st_dev,fst.st_ino); created.append((name,identity))
                with os.fdopen(fd,'wb') as f: f.write(raw); f.flush(); os.fsync(f.fileno())
            os.fsync(dir_fd)
            visible=os.stat(out_dir,follow_symlinks=False)
            require(stat.S_ISDIR(visible.st_mode) and _same_identity(visible,dir_identity),'output directory identity changed during publication')
            expected=sorted(name for name,_ in created); require(sorted(os.listdir(dir_fd))==expected,'output directory entries changed during publication')
            for name,identity in created:
                current=_entry_stat(name,dir_fd)
                require(stat.S_ISREG(current.st_mode) and _same_identity(current,identity),f'export leaf identity changed during publication: {name}')
            return {'status':'EXPORTED','output':str(out_dir),'files':len(files),'receipt_sha256':sha256_bytes(files['receipt.json'])}
        except Exception:
            _rollback_created(dir_fd,created); raise
    finally: os.close(dir_fd)
