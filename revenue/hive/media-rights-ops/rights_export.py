"""Deterministic create-exclusive exports with retained filesystem custody."""
import csv,io,os,stat
from pathlib import Path
from rights_model import *
from rights_store import snapshot,queues

def export_files(path,as_of,horizon_days=30):
    snap=snapshot(path); q=queues(path,as_of,horizon_days); out={'snapshot.json':canonical_bytes(snap),'queues.json':canonical_bytes(q)}; s=io.StringIO(newline=''); w=csv.writer(s,lineterminator='\n'); cols=('request_id','asset_id','channel','territory','starts_at','ends_at','grant_id','recorded_at'); w.writerow(cols)
    for p in snap['placements']: w.writerow([p[k] for k in cols])
    out['placements.csv']=s.getvalue().encode(); lines=['# Content Rights & Usage-Window Operations Desk','',f"Snapshot SHA-256: `{snap['snapshot_sha256']}`",'',f"Assets: {len(snap['assets'])}",f"Grants: {len(snap['grants'])}",f"Placements: {len(snap['placements'])}",f"Renewal/expiry review rows: {len(q['renewal_review'])}",f"Retraction review rows: {len(q['retraction_review'])}",'','Operational gate only: supplied authority facts are not a legal rights determination.','']; out['summary.md']='\n'.join(lines).encode(); receipt={'schema':RECEIPT_SCHEMA,'snapshot_sha256':snap['snapshot_sha256'],'files':[{'path':n,'bytes':len(b),'sha256':sha256_bytes(b)} for n,b in sorted(out.items())]}; out['receipt.json']=canonical_bytes(receipt); return out

def _same_identity(st,identity):
    return (st.st_dev,st.st_ino)==identity

def _secure_export_supported():
    required=(os.open,os.mkdir,os.stat,os.unlink,os.rmdir)
    return hasattr(os,'O_DIRECTORY') and hasattr(os,'O_NOFOLLOW') and all(fn in os.supports_dir_fd for fn in required)

def _entry_stat(name,dir_fd):
    return os.stat(name,dir_fd=dir_fd,follow_symlinks=False)

def _open_retained_parent(parent):
    # The parent itself is part of the publication transaction boundary. Snapshot
    # its identity before open, refuse symlinks/non-directories, then prove the
    # opened descriptor is the same generation. Replacing the parent between
    # those two observations therefore fails closed.
    try: before=os.stat(parent,follow_symlinks=False)
    except FileNotFoundError as e: raise RightsError(f'output parent must already exist: {parent}') from e
    require(stat.S_ISDIR(before.st_mode),'output parent must be a real directory, not a symlink or other file')
    identity=(before.st_dev,before.st_ino); fd=None
    try:
        fd=os.open(parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        current=os.fstat(fd); require(stat.S_ISDIR(current.st_mode) and _same_identity(current,identity),'output parent identity changed during publication')
        return fd,identity
    except Exception:
        if fd is not None: os.close(fd)
        raise

def _rollback_created(parent_fd,dir_fd,dir_name,dir_identity,created):
    # Every deletion is identity-checked. A renamed/replaced leaf or directory is
    # foreign state and is deliberately preserved rather than followed by name.
    for name,identity in reversed(created):
        try:
            current=_entry_stat(name,dir_fd)
            if stat.S_ISREG(current.st_mode) and _same_identity(current,identity): os.unlink(name,dir_fd=dir_fd)
        except FileNotFoundError: pass
        except OSError: pass
    try: os.fsync(dir_fd)
    except OSError: pass
    try:
        current=_entry_stat(dir_name,parent_fd)
        if stat.S_ISDIR(current.st_mode) and _same_identity(current,dir_identity): os.rmdir(dir_name,dir_fd=parent_fd)
    except FileNotFoundError: pass
    except OSError: pass

def publish_export(path,out_dir,as_of,horizon_days=30):
    out_dir=Path(out_dir); require(out_dir.name not in {'','.','..'},'output path must name a directory'); files=export_files(path,as_of,horizon_days)
    require(_secure_export_supported(),'secure export publication requires descriptor-relative no-follow filesystem support')
    parent_fd,parent_identity=_open_retained_parent(out_dir.parent)
    dir_fd=None; created=[]; dir_identity=None
    try:
        try: os.mkdir(out_dir.name,mode=0o700,dir_fd=parent_fd)
        except FileExistsError as e: raise RightsError(f'refusing to overwrite existing output: {out_dir}') from e
        dir_fd=os.open(out_dir.name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=parent_fd)
        dst=os.fstat(dir_fd); require(stat.S_ISDIR(dst.st_mode),'created output is not a directory'); dir_identity=(dst.st_dev,dst.st_ino)
        try:
            for name,raw in sorted(files.items()):
                require('/' not in name and '\\' not in name and name not in {'','.','..'},'export leaf name invalid')
                fd=os.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=dir_fd)
                fst=os.fstat(fd); identity=(fst.st_dev,fst.st_ino); created.append((name,identity))
                with os.fdopen(fd,'wb') as f: f.write(raw); f.flush(); os.fsync(f.fileno())
            os.fsync(dir_fd)
            # Success requires the caller-visible parent and child paths to still
            # name the exact generations retained by this transaction.
            visible_parent=os.stat(out_dir.parent,follow_symlinks=False)
            require(stat.S_ISDIR(visible_parent.st_mode) and _same_identity(visible_parent,parent_identity),'output parent identity changed during publication')
            visible=os.stat(out_dir,follow_symlinks=False)
            require(stat.S_ISDIR(visible.st_mode) and _same_identity(visible,dir_identity),'output path identity changed during publication')
            for name,identity in created:
                current=_entry_stat(name,dir_fd)
                require(stat.S_ISREG(current.st_mode) and _same_identity(current,identity),f'export leaf identity changed during publication: {name}')
            return {'status':'EXPORTED','output':str(out_dir),'files':len(files),'receipt_sha256':sha256_bytes(files['receipt.json'])}
        except Exception:
            _rollback_created(parent_fd,dir_fd,out_dir.name,dir_identity,created); raise
    finally:
        if dir_fd is not None: os.close(dir_fd)
        os.close(parent_fd)
