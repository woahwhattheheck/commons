#!/usr/bin/env python3
"""Replay ZIP/TAR deliverables in a private fresh directory and verify a manifest."""
from __future__ import annotations
import argparse, errno, hashlib, json, os, stat, tarfile, tempfile, zipfile
from pathlib import Path, PurePosixPath
from typing import Any, Iterable
MANIFEST_SCHEMA="commons-deliverable-manifest/v1"; REPLAY_SCHEMA="commons-clean-extraction-replay/v1"
MAX_FILES,MAX_BYTES,MAX_ARCHIVE,MAX_MANIFEST=10_000,1<<30,512<<20,8<<20
HEX=frozenset("0123456789abcdef")
class ReplayError(ValueError): pass
def sha(data:bytes)->str:return hashlib.sha256(data).hexdigest()
def canon(v:Any)->bytes:
    try:return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()
    except(TypeError,ValueError)as e:raise ReplayError(f"non-canonical JSON: {e}")from e
def strict_obj(pairs):
    out={}
    for k,v in pairs:
        if k in out:raise ReplayError(f"duplicate JSON key {k!r}")
        out[k]=v
    return out
def load_json(raw:bytes):
    try:text=raw.decode("utf-8")
    except UnicodeDecodeError as e:raise ReplayError("manifest is not UTF-8")from e
    def bad(v):raise ReplayError(f"non-finite JSON constant: {v}")
    try:return json.loads(text,object_pairs_hook=strict_obj,parse_constant=bad)
    except ReplayError:raise
    except(json.JSONDecodeError,ValueError)as e:raise ReplayError(f"invalid manifest JSON: {e}")from e
def norm(raw:str,directory=False)->str:
    if not isinstance(raw,str)or not raw or "\\" in raw:raise ReplayError(f"invalid archive path: {raw!r}")
    c=raw[:-1]if directory and raw.endswith("/")else raw;p=PurePosixPath(c)
    if not c or p.is_absolute()or any(x in("",".","..")for x in p.parts):raise ReplayError(f"non-canonical archive path: {raw!r}")
    if p.as_posix()+("/"if directory else"")!=raw or "//"in raw:raise ReplayError(f"non-canonical archive path: {raw!r}")
    return p.as_posix()
def valid_hex(v):return isinstance(v,str)and len(v)==64 and all(c in HEX for c in v)
def validate_manifest(raw:bytes):
    d=load_json(raw)
    if not isinstance(d,dict)or set(d)!={"schema","files","acceptance","manifest_sha256"}:raise ReplayError("invalid manifest top-level schema")
    if d["schema"]!=MANIFEST_SCHEMA or not valid_hex(d["manifest_sha256"]):raise ReplayError("invalid manifest schema or digest")
    payload={k:d[k]for k in("schema","files","acceptance")}
    if sha(canon(payload))!=d["manifest_sha256"]:raise ReplayError("manifest payload digest mismatch")
    rows=d["files"]
    if not isinstance(rows,list)or not rows:raise ReplayError("manifest files must be non-empty")
    seen,folded,out=set(),{},[]
    for r in rows:
        if not isinstance(r,dict)or set(r)!={"path","bytes","sha256"}:raise ReplayError("invalid manifest file row")
        rel=norm(r["path"]);f=rel.casefold()
        if rel in seen:raise ReplayError(f"duplicate manifest file path: {rel}")
        if f in folded and folded[f]!=rel:raise ReplayError("case-fold ambiguous manifest paths")
        n,digest=r["bytes"],r["sha256"]
        if isinstance(n,bool)or not isinstance(n,int)or n<0 or not valid_hex(digest):raise ReplayError(f"invalid manifest file metadata: {rel}")
        seen.add(rel);folded[f]=rel;out.append({"path":rel,"bytes":n,"sha256":digest})
    if out!=sorted(out,key=lambda r:r["path"]):raise ReplayError("manifest file rows are not canonical")
    acc=d["acceptance"]
    if not isinstance(acc,list)or not acc:raise ReplayError("manifest acceptance must be non-empty")
    ids,norm_acc=set(),[]
    for item in acc:
        if not isinstance(item,dict)or set(item)!={"id","description","paths"}:raise ReplayError("invalid manifest acceptance row")
        cid,desc,paths=item["id"],item["description"],item["paths"]
        if not isinstance(cid,str)or not cid.strip()or cid!=cid.strip()or cid in ids:raise ReplayError("invalid or duplicate manifest acceptance id")
        if not isinstance(desc,str)or not desc.strip()or desc!=desc.strip():raise ReplayError("invalid manifest acceptance description")
        if not isinstance(paths,list)or not paths:raise ReplayError("manifest acceptance paths must be non-empty")
        ids.add(cid);local=set();clean=[]
        for p in paths:
            rel=norm(p)
            if rel in local:raise ReplayError("manifest acceptance repeats path")
            if rel not in seen:raise ReplayError("manifest acceptance references absent file")
            local.add(rel);clean.append(rel)
        if clean!=sorted(clean):raise ReplayError("manifest acceptance paths are not canonical")
        norm_acc.append({"id":cid,"description":desc,"paths":clean})
    if norm_acc!=sorted(norm_acc,key=lambda x:x["id"]):raise ReplayError("manifest acceptance rows are not canonical")
    return d,out
def stable_read(path:Path,limit:int,label:str)->bytes:
    flags=os.O_RDONLY|getattr(os,"O_NOFOLLOW",0)
    try:fd=os.open(path,flags)
    except OSError as e:raise ReplayError(f"cannot open {label} safely: {e}")from e
    try:
        b=os.fstat(fd)
        if not stat.S_ISREG(b.st_mode)or b.st_size>limit:raise ReplayError(f"invalid or oversized {label}")
        parts=[];total=0
        while True:
            chunk=os.read(fd,min(1<<20,limit-total+1))
            if not chunk:break
            total+=len(chunk)
            if total>limit:raise ReplayError(f"{label} exceeds byte limit")
            parts.append(chunk)
        a=os.fstat(fd)
    finally:os.close(fd)
    ident=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns)
    if ident(b)!=ident(a)or total!=a.st_size:raise ReplayError(f"{label} changed while reading")
    return b"".join(parts)
def register(rel,seen,folded):
    if rel in seen:raise ReplayError(f"duplicate archive member path: {rel}")
    f=rel.casefold()
    if f in folded and folded[f]!=rel:raise ReplayError("case-fold ambiguous archive paths")
    seen.add(rel);folded[f]=rel
def copy_stream(src,dst,expected,total,limit):
    n=0
    while True:
        chunk=src.read(1<<20)
        if not chunk:break
        n+=len(chunk)
        if n>expected or total+n>limit:raise ReplayError("archive expands beyond declared/allowed bytes")
        dst.write(chunk)
    if n!=expected:raise ReplayError("archive member size mismatch")
    return n
def extract_zip(archive,root,max_files,max_bytes):
    seen,folded,files,declared,actual=set(),{},0,0,0
    try:zf=zipfile.ZipFile(archive)
    except(OSError,zipfile.BadZipFile)as e:raise ReplayError(f"invalid ZIP: {e}")from e
    with zf:
        infos=zf.infolist()
        if len(infos)>max_files:raise ReplayError("archive member count exceeds limit")
        for i in infos:
            isdir=i.is_dir();rel=norm(i.filename,isdir);register(rel,seen,folded)
            if i.flag_bits&1:raise ReplayError("encrypted ZIP member is not allowed")
            if i.create_system==3:
                kind=stat.S_IFMT((i.external_attr>>16)&0xFFFF)
                if kind==stat.S_IFLNK:raise ReplayError("ZIP symlink is not allowed")
                if kind not in(0,stat.S_IFREG,stat.S_IFDIR):raise ReplayError("ZIP special member is not allowed")
                if(kind==stat.S_IFDIR and not isdir)or(kind==stat.S_IFREG and isdir):raise ReplayError("ZIP type metadata conflicts with member name")
            target=root/rel
            if isdir:target.mkdir(parents=True,exist_ok=True);continue
            files+=1;declared+=i.file_size
            if files>max_files or i.file_size<0 or declared>max_bytes:raise ReplayError("archive declared file/byte limits exceeded")
            target.parent.mkdir(parents=True,exist_ok=True)
            try:
                with zf.open(i)as src,target.open("xb")as dst:actual+=copy_stream(src,dst,i.file_size,actual,max_bytes)
            except FileExistsError as e:raise ReplayError("archive extraction path collision")from e
    return files,actual
def extract_tar(archive,root,max_files,max_bytes):
    seen,folded,files,declared,actual=set(),{},0,0,0
    try:tf=tarfile.open(archive,"r:*")
    except(OSError,tarfile.TarError)as e:raise ReplayError(f"invalid TAR: {e}")from e
    with tf:
        members=tf.getmembers()
        if len(members)>max_files:raise ReplayError("archive member count exceeds limit")
        for m in members:
            isdir=m.isdir();rel=norm(m.name,isdir and m.name.endswith("/"));register(rel,seen,folded)
            if m.issym():raise ReplayError("TAR symlink is not allowed")
            if m.islnk():raise ReplayError("TAR hardlink is not allowed")
            target=root/rel
            if isdir:target.mkdir(parents=True,exist_ok=True);continue
            if not m.isfile():raise ReplayError("TAR special member is not allowed")
            files+=1;declared+=m.size
            if files>max_files or m.size<0 or declared>max_bytes:raise ReplayError("archive declared file/byte limits exceeded")
            target.parent.mkdir(parents=True,exist_ok=True);src=tf.extractfile(m)
            if src is None:raise ReplayError("TAR member has no data stream")
            try:
                with src,target.open("xb")as dst:actual+=copy_stream(src,dst,m.size,actual,max_bytes)
            except FileExistsError as e:raise ReplayError("archive extraction path collision")from e
    return files,actual
def hash_fresh(root):
    rows,folded=[],{}
    def walkerr(e):raise ReplayError(f"fresh extraction enumeration failed: {e}")from e
    for current,dirs,files in os.walk(root,topdown=True,followlinks=False,onerror=walkerr):
        cur=Path(current)
        for name in dirs:
            p=cur/name;mode=p.lstat().st_mode
            if stat.S_ISLNK(mode)or not stat.S_ISDIR(mode):raise ReplayError("unsafe extracted directory")
        for name in files:
            p=cur/name;st=p.lstat();rel=p.relative_to(root).as_posix();f=rel.casefold()
            if stat.S_ISLNK(st.st_mode)or not stat.S_ISREG(st.st_mode):raise ReplayError("unsafe extracted file")
            if f in folded and folded[f]!=rel:raise ReplayError,"case-fold ambiguous extracted paths")
            folded[f]=rel;data=stable_read(p,1<<62,"extracted file");rows.append({"path":rel,"bytes":len(data),"sha256":sha(data)})
    return sorted(rows,key=lambda r:r["path"])
def replay_archive(archive:Path,manifest_raw:bytes,*,max_files=MAX_FILES,max_uncompressed_bytes=MAX_BYTES,max_archive_bytes=MAX_ARCHIVE):
    if isinstance(max_files,bool)or not isinstance(max_files,int)or max_files<=0:raise ReplayError("max_files must be positive")
    if any(isinstance(v,bool)or not isinstance(v,int)or v<=0 for v in(max_uncompressed_bytes,max_archive_bytes)):raise ReplayError("byte limits must be positive integers")
    manifest,expected=validate_manifest(manifest_raw)
    if len(expected)>max_files:raise ReplayError("manifest file count exceeds replay limit")
    if sum(r["bytes"]for r in expected)>max_uncompressed_bytes:raise ReplayError,"manifest bytes exceed replay limit")
    with tempfile.TemporaryDirectory(prefix="clean-extraction-replay-")as td:
        box=Path(td);staged=box/"input.archive";data=stable_read(archive,max_archive_bytes,"archive");staged.write_bytes(data);digest=sha(data);fresh=box/"fresh";fresh.mkdir()
        if zipfile.is_zipfile(staged):fmt="zip";count,nbytes=extract_zip(staged,fresh,max_files,max_uncompressed_bytes)
        elif tarfile.is_tarfile(staged):fmt="tar";count,nbytes=extract_tar(staged,fresh,max_files,max_uncompressed_bytes)
        else:raise ReplayError("unsupported archive format")
        actual=hash_fresh(fresh)
        if actual!=expected:
            e,a={r["path"]:r for r in expected},{r["path"]:r for r in actual};missing,extra=sorted(set(e)-set(a)),sorted(set(a)-set(e));changed=sorted(p for p in set(e)&set(a)if e[p]!=a[p])
            raise ReplayError(f"fresh extraction mismatch: missing={missing}, extra={extra}, changed={changed}")
        if count!=len(actual)or nbytes!=sum(r["bytes"]for r in actual):raise ReplayError("extraction accounting mismatch")
    return{"schema":REPLAY_SCHEMA,"archive_sha256":digest,"archive_format":fmt,"manifest_sha256":manifest["manifest_sha256"],"files_verified":len(expected),"bytes_verified":sum(r["bytes"]for r in expected),"fresh_extraction":True,"verified":True}
def write_new(path:Path,data:bytes):
    path.parent.mkdir(parents=True,exist_ok=True);fd,name=tempfile.mkstemp(prefix=f".{path.name}.",dir=str(path.parent));tmp=Path(name)
    try:
        with os.fdopen(fd,"wb")as f:f.write(data);f.flush();os.fsync(f.fileno())
        try:os.link(tmp,path)
        except OSError as e:
            if e.errno==errno.EEXIST:raise ReplayError("receipt output already exists")from e
            raise ReplayError(f"cannot publish receipt: {e}")from e
    finally:
        try:tmp.unlink()
        except FileNotFoundError:pass
def parser():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("archive",type=Path);p.add_argument("--manifest",required=True,type=Path);p.add_argument("--output",required=True,type=Path);p.add_argument("--max-files",type=int,default=MAX_FILES);p.add_argument("--max-uncompressed-bytes",type=int,default=MAX_BYTES);p.add_argument("--max-archive-bytes",type=int,default=MAX_ARCHIVE);return p
def main(argv:Iterable[str]|None=None)->int:
    a=parser().parse_args(arv);archive,manifest,output=a.archive.absolute(),a.manifest.absolute(),a.output.absolute()
    if output.resolve()in{archive.resolve(),manifest.resolve()}:raise ReplayError("receipt output must not alias archive or manifest input")
    receipt=replay_archive(archive,stable_read(manifest,MAX_MANIFEST,"manifest"),max_files=a.max_files,max_uncompressed_bytes=a.max_uncompressed_bytes,max_archive_bytes=a.max_archive_bytes)
    write_new(output,(json.dumps(receipt,sort_keys=True,indent=2)+"\n").encode());print(receipt["archive_sha256"]);return 0
if __name__=="__main__":raise SystemExit(main())
