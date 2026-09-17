#!/usr/bin/env python3
"""Fail-closed outreach qualification firewall. Never performs transport."""
from __future__ import annotations
import argparse, hashlib, json, os, re, stat, time, unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import urlsplit, urlunsplit

SCHEMA="tjlabs-outreach-qualification/v2"
SOURCE_INDEX_SCHEMA="tjlabs-retained-source-index/v1"
AUTHORITY_INDEX_SCHEMA="tjlabs-authority-index/v1"
OWNER_RECEIPT_SCHEMA="tjlabs-owner-approval-receipt/v1"
MUSE_RECEIPT_SCHEMA="tjlabs-muse-writer-lease-receipt/v1"
OWNER_PROVIDER,OWNER_ROOT="TJLabsOwnerApproval","tjlabs-owner-root-v1"
MUSE_PROVIDER,MUSE_ROOT="SlackMuse","tjlabs-muse-root-v1"
TRUSTED_SOURCE_INDEX_SHA256="d010736c0d1f89ecd96a014547d8d2b1bb7c477ce3e7d4db260280a732f40a7d"
TRUSTED_AUTHORITY_INDEX_SHA256="899738b3f3301a0678e0c9596ed380dd612e1dac57d29b6a5d45b435718f2c3a"
HERE=Path(__file__).absolute().parent
SOURCE_ROOT=HERE/"retained_sources"; AUTHORITY_ROOT=HERE/"retained_authority"
MAX_RETAINED_BYTES=1_000_000
ROUTE_KINDS={"EMAIL","GITHUB_PR","PORTAL","FORM","SLACK_CONNECT","OTHER"}
OPEN_REL={"OPEN","WARM","INBOUND","REFERRED"}; BLOCK_REL={"DNR","BOUNCE","BLOCKED","CLOSED"}
PASS={"PROVEN","NOT_REQUIRED"}; COMP={"FIXED_FEE","HOURLY","BOUNTY"}
PRIOR_BLOCK={"PENDING","SENT","DELIVERED","ACCEPTED","PAID"}
SHA=re.compile(r"^[0-9a-f]{64}$"); ID=re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
CUR=re.compile(r"^[A-Z]{3}$"); EMAIL=re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PACKET_KEYS={"schema","source","opportunity","submission","eligibility","economics","target","action","prior_actions","owner_review_receipt_id","writer_lease_receipt_id"}

class PacketError(ValueError): pass

@dataclass(frozen=True)
class Decision:
    mode:str; evaluated_at_utc:str; qualified_for_owner_review:bool; authorized_to_send:bool
    blockers:tuple[str,...]; warnings:tuple[str,...]; qualification_digest:str; action_digest:str
    dedupe_key:str; runway_seconds:int; source_sha256:str; owner_receipt_sha256:str|None; writer_lease_receipt_sha256:str|None
    def as_dict(self):
        return {"schema":"tjlabs-outreach-qualification-decision/v2",**self.__dict__,"blockers":list(self.blockers),"warnings":list(self.warnings)}

def canon(v):
    try:return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()
    except (TypeError,ValueError) as e:raise PacketError("value is not canonical JSON") from e
def sha256(b):return hashlib.sha256(b).hexdigest()
def digest(v):return sha256(canon(v))
def mp(v,n):
    if not isinstance(v,Mapping):raise PacketError(f"{n} must be an object")
    return v
def li(v,n):
    if not isinstance(v,list):raise PacketError(f"{n} must be a list")
    return v
def text(v,n):
    if not isinstance(v,str) or not v.strip():raise PacketError(f"{n} must be a non-empty string")
    return v.strip()
def ident(v,n):
    v=text(v,n)
    if not ID.fullmatch(v):raise PacketError(f"{n} must be a simple retained identifier")
    return v
def enum(v,n,a):
    v=text(v,n)
    if v not in a:raise PacketError(f"{n} must be one of {sorted(a)}")
    return v
def utc(v,n):
    v=text(v,n)
    if not v.endswith("Z"):raise PacketError(f"{n} must use UTC Z form")
    try:d=datetime.fromisoformat(v[:-1]+"+00:00").astimezone(timezone.utc)
    except ValueError as e:raise PacketError(f"{n} invalid") from e
    if v!=d.isoformat(timespec="seconds").replace("+00:00","Z"):raise PacketError(f"{n} must use whole seconds")
    return d
def fmt(d):return d.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z")
def now():return datetime.fromtimestamp(time.time(),tz=timezone.utc).replace(microsecond=0)
def norm(s):return " ".join(unicodedata.normalize("NFKC",s).strip().casefold().split())
def norm_route(k,r):
    r=unicodededata.normalize("NFKC",r).strip()
    if k=="EMAIL":
        r=r.casefold(); r=r[7:].strip() if r.startswith("mailto:") else r
        if not EMAIL.fullmatch(r):raise PacketError("action.route must be valid email")
        return r
    if k in {"GITHUB_PR","PORTAL","FORM"}:
        p=urlsplit(r)
        if p.scheme.casefold() not in {"http","https"} or not p.netloc:raise PacketError("action.route must be absolute http(s) URL")
        path=re.sub(r"/+","/",p.path or "/"); path=path if path=="/" else path.rstrip("/")
        return urlunsplit((p.scheme.casefold(),p.netloc.casefold(),path,p.query,""))
    return norm(r)
def positive(v,n):
    if isinstance(v,bool):raise PacketError(f"{n} must be positive decimal")
    try:d=Decimal(str(v))
    except (InvalidOperation,ValueError) as e:raise PacketError(f"{n} must be positive decimal") from e
    if not d.is_finite() or d<=0:raise PacketError(f"{n} must be finite and > 0")
    return d

def _open_dir(path:Path,name:str)->int:
    if os.name!="posix" or not hasattr(os,"O_DIRECTORY") or not hasattr(os,"O_NOFOLLOW"):
        raise PacketError(f"{name} requires POSIX descriptor-anchored traversal")
    p=path.absolute(); parts=p.parts
    if not p.is_absolute() or not parts or parts[0]!=os.path.sep:raise PacketError(f"{name} root invalid")
    flags=os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|getattr(os,"O_CLOEXEC",0)
    fd=os.open(os.path.sep,flags)
    try:
        for c in parts[1:]:
            if c in {"",".",".."} or os.path.sep in c:raise PacketError(f"{name} root invalid")
            child=os.open(c,flags,dir_fd=fd)
            try:
                if not stat.S_ISDIR(os.fstat(child).st_mode):raise PacketError(f"{name} root component not directory")
            except Exception:os.close(child);raise
            os.close(fd);fd=child
        return fd
    except Exception:os.close(fd);raise

def _read(base:Path,relative:str,name:str)->bytes:
    if "\0" in relative or relative.startswith(("/","\\")):raise PacketError(f"{name} path invalid")
    parts=relative.replace("\\","/").split("/")
    if not parts or any(c in {"",".",".."} for c in parts):raise PacketError(f"{name} path invalid")
    dfd=_open_dir(base,name)
    try:
        dflags=os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|getattr(os,"O_CLOEXEC",0)
        for c in parts[:-1]:
            child=os.open(c,dflags,dir_fd=dfd)
            try:
                if not stat.S_ISDIR(os.fstat(child).st_mode):raise PacketError(f"{name} parent not directory")
            except Exception:os.close(child);raise
            os.close(dfd);dfd=child
        leaf=parts[-1]
        pre=os.stat(leaf,dir_fd=dfd,follow_symlinks=False)
        if not stat.S_ISREG(pre.st_mode) or stat.S_ISLNK(pre.st_mode) or pre.st_nlink!=1:raise PacketError(f"{name} must have exactly one hard link and be a regular file")
        if pre.st_size>MAX_RETAINED_BYTES:raise PacketError(f"{name} too large")
        try:fd=os.open(leaf,os.O_RDONLY|os.O_NOFOLLOW|getattr(os,"O_CLOEXEC",0),dir_fd=dfd)
        except OSError as e:raise PacketError(f"{name} no-follow open failed") from e
        try:
            opened=os.fstat(fd); sig=lambda s:(s.st_dev,s.st_ino,s.st_nlink,s.st_size,s.st_mtime_ns)
            if not stat.S_ISREG(opened.st_mode) or opened.st_nlink!=1 or sig(opened)!=sig(pre):raise PacketError(f"{name} changed before open")
            out=[]; left=MAX_RETAINED_BYTES+1
            while left:
                b=os.read(fd,min(65536,left))
                if not b:break
                out.append(b);left-=len(b)
            data=b"".join(out)
            if len(data)>MAX_RETAINED_BYTES or sig(os.fstat(fd))!=sig(opened):raise PacketError(f"{name} changed during read")
            return data
        finally:os.close(fd)
    finally:os.close(dfd)

def pinned(path:Path,expected:str,schema:str,name:str):
    b=_read(path.parent,path.name,name); actual=sha256(b)
    if actual!=expected:raise PacketError(f"{name} root digest mismatch")
    try:v=json.loads(b.decode())
    except (UnicodeDecodeError,json.JSONDecodeError) as e:raise PacketError(f"{name} invalid JSON") from e
    v=mp(v,name)
    if v.get("schema")!=schema:raise PacketError(f"{name} schema mismatch")
    return v

_read_retained_file = _read
_load_pinned_index = pinned

def load_source(packet):
    s=mp(packet.get("source"),"source")
    if set(s)!={"source_id"}:raise PacketError("source may contain only source_id")
    sid=ident(s.get("source_id"),"source.source_id")
    idx=pinned(SOURCE_ROOT/"index.json",TRUSTED_SOURCE_INDEX_SHA256,SOURCE_INDEX_SCHEMA,"retained source index")
    raw=mp(idx.get("sources"),"source index.sources").get(sid)
    if raw is None: raise PacketError("source.source_id is not present in trusted retained-source index")
    e=mp(raw,f"source {sid}")
    fn=ident(e.get("file"),"source.file"); expected=text(e.get("sha256"),"source.sha256")
    if not SHA.fullmatch(expected):raise PacketError("source index sha invalid")
    b=_read(SOURCE_ROOT/"files",fn,"retained source"); actual=sha256(b)
    if actual!=expected:raise PacketError("retained source digest mismatch")
    return {"source_id":sid,"sha256":actual},actual

def load_auth(kind,rid):
    idx=pinned(AUTHORITY_ROOT/"index.json",TRUSTED_AUTHORITY_INDEX_SHA256,AUTHORITY_INDEX_SCHEMA,"retained authority index")
    e=mp(mp(idx.get(kind),f"authority.{kind}").get(rid),f"authority {kind}.{rid}")
    fn=ident(e.get("file"),"receipt.file"); expected=text(e.get("sha256"),"receipt.sha256")
    if not SHA.fullmatch(expected):raise PacketError("receipt sha invalid")
    b=_read(AUTHORITY_ROOT/kind,fn,f"retained {kind} receipt"); actual=sha256(b)
    if actual!=expected:raise PacketError(f"retained {kind} receipt digest mismatch")
    try:r=mp(json.loads(b.decode()),f"retained {kind} receipt")
    except (UnicodeDecodeError,json.JSONDecodeError) as e:raise PacketError("receipt invalid JSON") from e
    return r,actual

def material(packet,source,at):
    if packet.get("schema")!=SCHEMA:raise PacketError(f"schema must be {SCHEMA}")
    extra=set(packet)-PACKET_KEYS
    if extra:raise PacketError(f"candidate packet contains forbidden/unknown fields: {sorted(extra)}")
    blockers=[]; warnings=[]
    o=mp(packet.get("opportunity"),"opportunity"); oid=text(o.get("id"),"opportunity.id"); deadline=utc(o.get("deadline_utc"),"opportunity.deadline_utc")
    mh=o.get("min_runway_hours")
    if isinstance(mh,bool) or not isinstance(mh,int) or mh<0:raise PacketError("min_runway_hours must be integer >= 0")
    runway=int((deadline-at).total_seconds()); req=mh*3600
    if runway<req:blockers.append("RUNWAY_BELOW_MINIMUM")
    if runway<0:blockers.append("DEADLINE_PASSED")
    if runway==req:warnings.append("RUNWAY_EXACTLY_AT_MINIMUM")
    sub=mp(packet.get("submission"),"submission"); sk=enum(sub.get("kind"),"submission.kind",ROUTE_KINDS); sl=text(sub.get("locator"),"submission.locator")
    rs=enum(sub.get("route_state"),"submission.route_state",{"PROVEN","UNKNOWN","FAILED"}); rr=sub.get("registration_required")
    if not isinstance(rr,bool):raise PacketError("registration_required must be boolean")
    rg=enum(sub.get("registration_state"),"registration_state",{"PROVEN","NOT_REQUIRED","UNKNOWN","FAILED"})
    if rs!="PROVEN":blockers.append("SUBMISSION_ROUTE_NOT_PROVEN")
    if rr and rg!="PROVEN":blockers.append("REGISTRATION_NOT_PROVEN")
    if not rr and rg not in PASS:blockers.append("REGISTRATION_STATE_INCONSISTENT")
    gates=[]; seen=set()
    for i,g0 in enumerate(li(mp(packet.get("eligibility"),"eligibility").get("gates"),"eligibility.gates")):
        g=mp(g0,f"gate[{i}]"); n=text(g.get("name"),"gate.name"); key=norm(n)
        if key in seen:raise PacketError("duplicate eligibility gate")
        seen.add(key); st=enum(g.get("state"),"gate.state",{"PROVEN","NOT_REQUIRED","UNKNOWN","FAILED"}); refs=[text(x,"evidence_ref") for x in li(g.get("evidence_refs"),"evidence_refs")]
        if st=="PROVEN" and not refs:raise PacketError("PROVEN gate needs evidence_refs")
        if st not in PASS:blockers.append(f"ELIGIBILITY_{st}:{n}")
        gates.append({"name":n,"state":st,"evidence_refs":refs})
    if not gates:raise PacketError("eligibility.gates must not be empty")
    ec=mp(packet.get("economics"),"economics"); basis=enum(ec.get("basis"),"economics.basis",COMP); amount=positive(ec.get("amount"),"economics.amount")
    currency=text(ec.get("currency"),"economics.currency"); scope=text(ec.get("bounded_scope"),"economics.bounded_scope"); pay=enum(ec.get("payment_path_state"),"payment_path_state",{"PROVEN","UNKNOWN","FAILED"})
    if not CUR.fullmatch(currency):raise PacketError("currency invalid")
    if pay!="PROVEN":blockers.append("PAYMENT_PATH_NOT_PROVEN")
    t=mp(packet.get("target"),"target"); org=text(t.get("organization"),"target.organization"); contact=text(t.get("contact"),"target.contact"); rel=enum(t.get("relationship_state"),"relationship_state",OPEN_REL|BLOCK_REL)
    if rel in BLOCK_REL:blockers.append(f"RELATIONSHIP_{rel}")
    a=mp(packet.get("action"),"action"); ak=enum(a.get("kind"),"action.kind",ROUTE_KINDS); route=norm_route(ak,text(a.get("route"),"action.route")); purpose=text(a.get("purpose"),"action.purpose"); csha=text(a.get("content_sha256"),"action.content_sha256")
    if not SHA.fullmatch(csha):raise PacketError("action.content_sha256 invalid")
    if ak=="EMAIL" and norm_route("EMAIL",contact)!=route:blockers.append("ACTION_ROUTE_CONTACT_MISMATCH")
    dkey=digest({"opportunity_id":norm(oid),"organization":norm(org),"contact":norm(contact),"action_kind":ak,"route":route,"purpose":norm(purpose)})
    prior=[]
    for i,p0 in enumerate(li(packet.get("prior_actions"),"prior_actions")):
        p=mp(p0,f"prior[{i}]"); k=text(p.get("dedupe_key"),"prior.dedupe_key"); st=enum(p.get("state"),"prior.state",PRIOR_BLOCK|{"FAILED","VOID"})
        if not SHA.fullmatch(k):raise PacketError("prior dedupe key invalid")
        if k==dkey and st in PRIOR_BLOCK:blockers.append(f"DUPLICATE_PRIOR_ACTION:{st}")
        prior.append({"dedupe_key":k,"state":st})
    m={"schema":SCHEMA,"source":dict(source),"opportunity":{"id":oid,"deadline_utc":o["deadline_utc"],"min_runway_hours":mh},"submission":{"kind":sk,"locator":sl,"route_state":rs,"registration_required":rr,"registration_state":rg},"eligibility":{"gates":gates},"economics":{"basis":basis,"amount":format(amount,"f"),"currency":currency,"bounded_scope":scope,"payment_path_state":pay},"target":{"organization":org,"contact":contact,"relationship_state":rel},"action":{"kind":ak,"route":route,"purpose":purpose,"content_sha256":csha},"dedupe_key":dkey,"prior_actions":prior}
    return m,blockers,warnings,runway,dkey

def check_owner(r,q,at):
    b=[]
    if r.get("schema")!=OWNER_RECEIPT_SCHEMA or r.get("provider")!=OWNER_PROVIDER or r.get("root_id")!=OWNER_ROOT:raise PacketError("owner receipt trust root mismatch")
    ident(r.get("generation"),"owner.generation"); text(r.get("source_ref"),"owner.source_ref")
    if enum(r.get("status"),"owner.status",{"APPROVED","REJECTED"})!="APPROVED":b.append("OWNER_REVIEW_REJECTED")
    bound=text(r.get("qualification_digest"),"owner.qualification_digest")
    if not SHA.fullmatch(bound) or bound!=q:b.append("OWNER_REVIEW_STALE_OR_FOREIGN")
    issued,expires=utc(r.get("issued_at_utc"),"owner.issued_at"),utc(r.get("expires_at_utc"),"owner.expires_at")
    if issued>at or expires<at or expires<issued:b.append("OWNER_REVIEW_TIME_INVALID")
    text(r.get("reviewer"),"owner.reviewer"); return b

def check_muse(r,a,writer,at):
    b=[]
    if r.get("schema")!=MUSE_RECEIPT_SCHEMA or r.get("provider")!=MUSE_PROVIDER or r.get("root_id")!=MUSE_ROOT:raise PacketError("Muse receipt trust root mismatch")
    ident(r.get("generation"),"muse.generation"); text(r.get("source_ref"),"muse.source_ref"); text(r.get("key"),"muse.key")
    st=enum(r.get("status"),"muse.status",{"SELECTED","HOLD","COLLISION","VOID"})
    if st!="SELECTED":b.append(f"WRITER_LEASE_{st}")
    if text(r.get("selected_writer"),"muse.selected_writer")!=writer:b.append("WRITER_LEASE_FOREIGN_WRITER")
    bound=text(r.get("action_digest"),"muse.action_digest")
    if not SHA.fullmatch(bound) or bound!=a:b.append("WRITER_LEASE_STALE_OR_FOREIGN_ACTION")
    issued,expires=utc(r.get("issued_at_utc"),"muse.issued_at"),utc(r.get("expires_at_utc"),"muse.expires_at")
    if issued>at or expires<at or expires<issued:b.append("WRITER_LEASE_TIME_INVALID")
    return b

def _evaluate(packet,writer,at,current):
    if not isinstance(packet,Mapping):raise PacketError("packet must be object")
    writer=text(writer,"writer"); source,ssha=load_source(packet); m,b,w,runway,dkey=material(packet,source,at)
    q=digest(m); ad=digest({"qualification_digest":q,"dedupe_key":dkey,"action":m["action"]}); qb=tuple(sorted(set(b))); qualified=not qb
    osha=lsha=None
    if not current:
        w += ["HISTORICAL_REPLAY_NON_CURRENT","OWNER_AND_MUSE_AUTHORITY_NOT_CONSUMED_IN_REPLAY"]
        authorized=False
    else:
        oid=packet.get("owner_review_receipt_id"); lid=packet.get("writer_lease_receipt_id")
        if oid is None:w.append("OWNER_REVIEW_REQUIRED")
        else:
            oid=ident(oid,"owner_review_receipt_id"); r,osha=load_auth("owner",oid); b+=check_owner(r,q,at)
        if lid is None:w.append("WRITER_LEASE_REQUIRED")
        else:
            lid=ident(lid,"writer_lease_receipt_id"); r,lsha=load_auth("muse",lid); b+=check_muse(r,ad,writer,at)
        if qb and oid is not None:b.append("OWNER_REVIEW_CANNOT_OVERRIDE_QUALIFICATION_BLOCKER")
        authorized=qualified and osha is not None and lsha is not None and not b
    return Decision("CURRENT_PROCESS_TIME" if current else "HISTORICAL_REPLAY_NON_CURRENT",fmt(at),qualified,authorized,tuple(sorted(set(b))),tuple(sorted(set(w))),q,ad,dkey,runway,ssha,osha,lsha)

def evaluate_current(packet:Mapping[str,Any],*,writer:str)->Decision:return _evaluate(packet,writer,now(),True)
def evaluate_historical(packet:Mapping[str,Any],*,at_utc:str,writer:str)->Decision:return _evaluate(packet,writer,utc(at_utc,"at_utc"),False)
def load_json(path:Path):
    with path.open(encoding="utf-8") as f:return mp(json.load(f),"packet")
def main(argv:Sequence[str]|None=None)->int:
    p=argparse.ArgumentParser(description="Evaluate outreach readiness; never sends anything")
    p.add_argument("packet",type=Path);p.add_argument("--writer",required=True);p.add_argument("--historical-at");p.add_argument("--out",type=Path);a=p.parse_args(argv)
    d=evaluate_historical(load_json(a.packet),at_utc=a.historical_at,writer=a.writer) if a.historical_at else evaluate_current(load_json(a.packet),writer=a.writer)
    s=json.dumps(d.as_dict(),sort_keys=True,indent=2)+"\n"; a.out.write_text(s,encoding="utf-8") if a.out else print(s,end="")
    return 0 if d.authorized_to_send else 2
if __name__=="__main__":raise SystemExit(main())
