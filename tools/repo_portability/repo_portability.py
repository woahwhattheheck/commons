#!/usr/bin/env python3
"""Offline verified Git snapshots and non-authorizing migration plans."""
from __future__ import annotations
import argparse, hashlib, json, os, re, stat, subprocess, sys, tempfile
from pathlib import Path, PurePath
from urllib.parse import urlsplit

SNAPSHOT_SCHEMA='commons-repo-portability-snapshot/v1'
INVENTORY_SCHEMA='commons-repo-portability-inventory/v1'
PLAN_SCHEMA='commons-repo-portability-plan/v1'
ACTIONS={'KEEP_PRIVATE','COLD_ARCHIVE','MIRROR_PRIVATE','PUBLIC_REVIEW'}
OID=re.compile(r'^[0-9a-f]{40,64}$'); REPO=re.compile(r'^[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}$')
SHA256=re.compile(r'^[0-9a-f]{64}$'); CONTROL=re.compile(r'[\x00-\x1f\x7f]')
AUTHORITY={'delete_authorized':False,'visibility_change_authorized':False,'provider_push_authorized':False,'billing_mutation_authorized':False}

class PortabilityError(RuntimeError): pass

def _pairs(items):
    out={}
    for k,v in items:
        if k in out: raise PortabilityError(f'duplicate JSON key: {k}')
        out[k]=v
    return out

def loads(raw:bytes):
    if type(raw) is not bytes: raise PortabilityError('JSON bytes required')
    try:
        return json.loads(raw.decode('utf-8'),object_pairs_hook=_pairs,
                          parse_constant=lambda x:(_ for _ in ()).throw(PortabilityError(f'non-finite JSON: {x}')))
    except (UnicodeDecodeError,json.JSONDecodeError) as e: raise PortabilityError('invalid UTF-8 JSON') from e

def canon(v):
    try: return (json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)+'\n').encode()
    except (TypeError,ValueError) as e: raise PortabilityError('non-canonical JSON value') from e

def git(args,cwd=None,check=True):
    env=dict(os.environ); env['GIT_TERMINAL_PROMPT']='0'
    p=subprocess.run(['git',*args],cwd=cwd,text=True,capture_output=True,env=env)
    if check and p.returncode:
        raise PortabilityError(f"git {args[0]} failed: {(p.stderr or p.stdout).strip()[:400]}")
    return p

def regular(path:Path,label):
    try: s=path.lstat()
    except OSError as e: raise PortabilityError(f'{label} unavailable') from e
    if stat.S_ISLNK(s.st_mode) or not stat.S_ISREG(s.st_mode): raise PortabilityError(f'{label} must be a regular non-symlink file')
    return s

def read_json(path:Path,label,limit=2*1024*1024):
    a=regular(path,label)
    if a.st_size>limit: raise PortabilityError(f'{label} too large')
    try: raw=path.read_bytes()
    except OSError as e: raise PortabilityError(f'{label} unreadable') from e
    b=regular(path,label); ident=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
    if ident(a)!=ident(b): raise PortabilityError(f'{label} changed during read')
    return loads(raw)

def write_new(path:Path,raw:bytes):
    if type(raw) is not bytes or not path.parent.is_dir() or path.parent.is_symlink(): raise PortabilityError('invalid output parent/bytes')
    flags=os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,'O_NOFOLLOW',0)|getattr(os,'O_BINARY',0)
    try: fd=os.open(path,flags,0o600)
    except OSError as e: raise PortabilityError('refusing to overwrite output') from e
    try:
        view=memoryview(raw)
        while view:
            n=os.write(fd,view)
            if n<=0: raise PortabilityError('output write made no progress')
            view=view[n:]
        os.fsync(fd)
    finally: os.close(fd)

def sha256(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def refs_from(lines):
    rows=[]
    for line in lines.splitlines():
        oid,sep,ref=line.partition(' '); ref=ref.strip()
        if not sep or not OID.fullmatch(oid) or not ref: raise PortabilityError('invalid ref inventory')
        rows.append({'ref':ref,'oid':oid})
    if not rows: raise PortabilityError('empty ref inventory')
    return sorted(rows,key=lambda x:(x['ref'],x['oid']))

def repo_refs(repo): return refs_from(git(['show-ref','--head'],repo).stdout)
def bundle_refs(bundle): return refs_from(git(['bundle','list-heads',str(bundle)]).stdout)
def head_ref(repo):
    p=git(['symbolic-ref','--quiet','--no-recurse','HEAD'],repo,False)
    if p.returncode==1:return None
    if p.returncode:raise PortabilityError('cannot resolve symbolic HEAD')
    v=p.stdout.strip()
    if not v.startswith('refs/') or CONTROL.search(v):raise PortabilityError('invalid symbolic HEAD')
    return v

def validate_manifest(d):
    keys={'schema','bundle','bundle_bytes','bundle_sha256','head_oid','head_ref','refs','authority'}
    if type(d) is not dict or set(d)!=keys or d.get('schema')!=SNAPSHOT_SCHEMA: raise PortabilityError('manifest fields/schema drifted')
    if d['bundle']!='repo.bundle' or type(d['bundle_bytes']) is not int or type(d['bundle_bytes']) is bool or d['bundle_bytes']<=0: raise PortabilityError('invalid bundle metadata')
    if not SHA256.fullmatch(str(d['bundle_sha256'])) or not OID.fullmatch(str(d['head_oid'])): raise PortabilityError('invalid digest/OID')
    if d['head_ref'] is not None and (type(d['head_ref']) is not str or not d['head_ref'].startswith('refs/') or CONTROL.search(d['head_ref'])): raise PortabilityError('invalid head_ref')
    if type(d['refs']) is not list or not d['refs']: raise PortabilityError('invalid refs')
    normalized=[]
    for r in d['refs']:
        if type(r) is not dict or set(r)!={'ref','oid'} or type(r['ref']) is not str or not r['ref'] or CONTROL.search(r['ref']) or not OID.fullmatch(str(r['oid'])): raise PortabilityError('invalid manifest ref')
        normalized.append({'ref':r['ref'],'oid':r['oid']})
    if normalized!=sorted(normalized,key=lambda x:(x['ref'],x['oid'])): raise PortabilityError('refs not canonical')
    if d['authority']!=AUTHORITY: raise PortabilityError('manifest authority must remain false')
    return d

def snapshot(source:Path,out:Path):
    try:s=source.lstat()
    except OSError as e:raise PortabilityError('source unavailable') from e
    if stat.S_ISLNK(s.st_mode) or not stat.S_ISDIR(s.st_mode):raise PortabilityError('source must be ordinary directory')
    source=source.absolute()
    if git(['rev-parse','--is-inside-work-tree'],source).stdout.strip()!='true':raise PortabilityError('source is not work tree')
    head=git(['rev-parse','--verify','HEAD'],source).stdout.strip()
    if not OID.fullmatch(head):raise PortabilityError('invalid HEAD')
    href=head_ref(source); before=repo_refs(source)
    if os.path.lexists(out):raise PortabilityError('refusing reused output directory')
    out.mkdir(mode=0o700)
    staged=out/'.repo.bundle.staged'; bundle=out/'repo.bundle'; manifest=out/'manifest.json'
    try:
        git(['bundle','create',str(staged),'--all'],source); regular(staged,'staged bundle')
        if bundle_refs(staged)!=before:raise PortabilityError('bundle/source refs differ')
        if repo_refs(source)!=before or head_ref(source)!=href or git(['rev-parse','HEAD'],source).stdout.strip()!=head:raise PortabilityError('source changed during snapshot')
        os.link(staged,bundle,follow_symlinks=False); staged.unlink(); info=regular(bundle,'bundle')
        doc={'schema':SNAPSHOT_SCHEMA,'bundle':'repo.bundle','bundle_bytes':info.st_size,'bundle_sha256':sha256(bundle),'head_oid':head,'head_ref':href,'refs':before,'authority':dict(AUTHORITY)}
        write_new(manifest,canon(doc)); return verify_snapshot(manifest)
    except Exception:
        try: staged.unlink(missing_ok=True)
        except OSError: pass
        raise

def verify_snapshot(manifest:Path):
    d=validate_manifest(read_json(manifest,'manifest')); bundle=manifest.parent/d['bundle']; info=regular(bundle,'bundle')
    if info.st_size!=d['bundle_bytes']:raise PortabilityError('bundle byte count mismatch')
    if sha256(bundle)!=d['bundle_sha256']:raise PortabilityError('bundle SHA-256 mismatch')
    if bundle_refs(bundle)!=d['refs']:raise PortabilityError('bundle refs differ')
    with tempfile.TemporaryDirectory(prefix='repo-portability-verify-') as td:
        restored=Path(td)/'restore.git'; git(['init','--bare',str(restored)])
        git(['fetch','--quiet',str(bundle),'+refs/*:refs/*'],restored)
        if d['head_ref'] is None:git(['update-ref','--no-deref','HEAD',d['head_oid']],restored)
        else:git(['symbolic-ref','HEAD',d['head_ref']],restored)
        if git(['rev-parse','HEAD'],restored).stdout.strip()!=d['head_oid'] or repo_refs(restored)!=d['refs']:raise PortabilityError('restore identity mismatch')
        git(['fsck','--full'],restored)
    return {'schema':SNAPSHOT_SCHEMA,'state':'VERIFIED_RESTORABLE','bundle_sha256':d['bundle_sha256'],'head_oid':d['head_oid'],'head_ref':d['head_ref'],'ref_count':len(d['refs']),'fsck':'PASS','authority':dict(AUTHORITY)}

def text(v,label,n=2048):
    if type(v) is not str or not v or len(v)>n or CONTROL.search(v):raise PortabilityError(f'invalid {label}')
    return v

def local_path(v):
    v=text(v,'local_path',1024); p=PurePath(v)
    if not p.is_absolute() or '..' in p.parts:raise PortabilityError('local_path must be absolute/traversal-free')
    return v

def https(v,label):
    v=text(v,label); p=urlsplit(v)
    if p.scheme!='https' or not p.hostname or p.username or p.password or p.query or p.fragment or not p.path or p.path=='/' or any(c.isspace() for c in v):raise PortabilityError(f'{label} must be credential-free HTTPS')
    return v

def compile_plan(d):
    if type(d) is not dict or set(d)!={'schema','repositories'} or d.get('schema')!=INVENTORY_SCHEMA:raise PortabilityError('inventory fields/schema drifted')
    rows=d['repositories']
    if type(rows) is not list or not 1<=len(rows)<=500:raise PortabilityError('repositories must contain 1..500 rows')
    seen=set(); output=[]
    for i,r in enumerate(rows):
        if type(r) is not dict or set(r)!={'repository','action','local_path','source_url','destination_url'}:raise PortabilityError(f'row {i} fields drifted')
        repo=text(r['repository'],'repository',201)
        if not REPO.fullmatch(repo) or repo in seen:raise PortabilityError('invalid/duplicate repository')
        seen.add(repo); action=text(r['action'],'action',32)
        if action not in ACTIONS:raise PortabilityError('unsupported action')
        lp=None if r['local_path'] is None else local_path(r['local_path']); su=None if r['source_url'] is None else https(r['source_url'],'source_url'); du=None if r['destination_url'] is None else https(r['destination_url'],'destination_url')
        commands=[]; notes=[]; slug=repo.replace('/','__')
        if action in {'KEEP_PRIVATE','PUBLIC_REVIEW'}:
            if any(x is not None for x in (lp,su,du)):raise PortabilityError(f'{action} does not accept path/URLs')
            notes=[('No migration action; keep current visibility until a separate owner decision.' if action=='KEEP_PRIVATE' else 'Review secret history, licenses, confidential material, and public-release intent; this plan never authorizes visibility changes.')]
        elif action=='COLD_ARCHIVE':
            if lp is None or su is not None or du is not None:raise PortabilityError('COLD_ARCHIVE requires only local_path')
            dest=f'{slug}.portable'; commands=[{'purpose':'create verified cold snapshot','argv':[sys.executable,'tools/repo_portability/repo_portability.py','snapshot','--source',lp,'--output-dir',dest]},{'purpose':'replay restore verification','argv':[sys.executable,'tools/repo_portability/repo_portability.py','verify','--manifest',f'{dest}/manifest.json']}]; notes=['Retain bundle+manifest before any separate decommission decision.']
        else:
            if lp is not None or su is None or du is None or su==du:raise PortabilityError('MIRROR_PRIVATE requires distinct source/destination URLs')
            mirror=f'{slug}.mirror.git'; commands=[{'purpose':'create local mirror','argv':['git','clone','--mirror',su,mirror]},{'purpose':'verify local mirror','argv':['git','-C',mirror,'fsck','--full']},{'purpose':'push all refs to explicit destination','argv':['git','-C',mirror,'push','--mirror',du]},{'purpose':'read destination refs','argv':['git','ls-remote','--refs',du]}]; notes=['Credentials must be supplied out-of-band, never embedded in URLs/receipts.']
        output.append({'repository':repo,'action':action,'commands':commands,'notes':notes,'authority':dict(AUTHORITY)})
    return {'schema':PLAN_SCHEMA,'repositories':sorted(output,key=lambda x:x['repository']),'authority':dict(AUTHORITY)}

def compile_plan_file(src:Path,dst:Path):
    plan=compile_plan(read_json(src,'inventory')); write_new(dst,canon(plan)); return plan

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__); sub=p.add_subparsers(dest='cmd',required=True)
    s=sub.add_parser('snapshot');s.add_argument('--source',type=Path,required=True);s.add_argument('--output-dir',type=Path,required=True)
    v=sub.add_parser('verify');v.add_argument('--manifest',type=Path,required=True)
    m=sub.add_parser('plan');m.add_argument('--inventory',type=Path,required=True);m.add_argument('--output',type=Path,required=True)
    a=p.parse_args(argv)
    try:
        result=snapshot(a.source,a.output_dir) if a.cmd=='snapshot' else verify_snapshot(a.manifest) if a.cmd=='verify' else compile_plan_file(a.inventory,a.output)
        sys.stdout.buffer.write(canon(result));return 0
    except PortabilityError as e:print(f'PORTABILITY_ERROR: {e}',file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())
