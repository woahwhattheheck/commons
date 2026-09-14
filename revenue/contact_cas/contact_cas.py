#!/usr/bin/env python3
"""Offline state engine for a remote compare-and-swap contact mutex.

The module never sends messages or performs network I/O. Callers publish its
candidate JSON through a conditional remote update (for example GitHub
update_file with the exact previously-read blob SHA).
"""
from __future__ import annotations
import argparse, hashlib, json, re, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "contact-cas/v1"
MAX_CLAIM_SECONDS = 3600
DEFAULT_CLAIM_SECONDS = 900
OWNER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:@/+\-]{0,127}$")
NONCE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:\-]{7,127}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

class ContactCasError(ValueError): pass

def _plain_int(v: Any, name: str) -> int:
    if isinstance(v, bool) or not isinstance(v, int):
        raise ContactCasError(f"{name} must be an integer")
    return v

def _parse_utc(v: str) -> datetime:
    if not isinstance(v, str) or not v.endswith("Z"):
        raise ContactCasError("time must be RFC3339 UTC ending in Z")
    try: dt = datetime.fromisoformat(v[:-1] + "+00:00")
    except ValueError as e: raise ContactCasError("invalid RFC3339 UTC time") from e
    if dt.tzinfo != timezone.utc or dt.microsecond:
        raise ContactCasError("time must use whole UTC seconds")
    return dt

def _fmt_utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")

def canonical_email(raw: str) -> str:
    if not isinstance(raw, str): raise ContactCasError("email must be text")
    text=raw.strip()
    if text.count("@") != 1: raise ContactCasError("email must contain one @")
    local, domain = text.rsplit("@",1)
    local, domain = local.strip(), domain.strip().lower().rstrip(".")
    if not local or not domain or any(ch.isspace() for ch in local+domain):
        raise ContactCasError("invalid email")
    try: domain=domain.encode("idna").decode("ascii")
    except UnicodeError as e: raise ContactCasError("invalid email domain") from e
    return f"{local.casefold()}@{domain}"

def target_digest_for_email(raw: str) -> str:
    return hashlib.sha256(("email\0"+canonical_email(raw)).encode()).hexdigest()

def target_digest_for_public_id(raw: str) -> str:
    if not isinstance(raw,str): raise ContactCasError("public target id must be text")
    canon=" ".join(raw.strip().casefold().split())
    if not canon or len(canon)>512: raise ContactCasError("invalid public target id")
    return hashlib.sha256(("public-id\0"+canon).encode()).hexdigest()

def message_digest(subject: str, body: str) -> str:
    if not isinstance(subject,str) or not isinstance(body,str):
        raise ContactCasError("subject/body must be text")
    norm=lambda s:s.replace("\r\n","\n").replace("\r","\n")
    return hashlib.sha256((norm(subject)+"\0"+norm(body)).encode()).hexdigest()

def empty_state() -> dict[str,Any]:
    return {"schema":SCHEMA,"revision":0,"targets":{}}

def _validate_entry(e: Any) -> None:
    if not isinstance(e,dict): raise ContactCasError("target entry must be object")
    status=e.get("status")
    common={"status","owner","nonce","claim_at"}
    expected={
        "claimed": common|{"lease_until"},
        "armed": common|{"armed_at","message_sha256"},
        "sent": common|{"armed_at","message_sha256","sent_at","provider_receipt_sha256"},
    }.get(status)
    if expected is None or set(e)!=expected: raise ContactCasError(f"invalid {status!r} entry")
    if not isinstance(e["owner"],str) or not OWNER_RE.fullmatch(e["owner"]): raise ContactCasError("invalid owner")
    if not isinstance(e["nonce"],str) or not NONCE_RE.fullmatch(e["nonce"]): raise ContactCasError("invalid nonce")
    claim=_parse_utc(e["claim_at"])
    if status=="claimed":
        end=_parse_utc(e["lease_until"]); secs=int((end-claim).total_seconds())
        if secs<1 or secs>MAX_CLAIM_SECONDS: raise ContactCasError("claim lease out of bounds")
    else:
        armed=_parse_utc(e["armed_at"])
        if armed<claim: raise ContactCasError("armed_at precedes claim")
        if not isinstance(e["message_sha256"],str) or not SHA256_RE.fullmatch(e["message_sha256"]):
            raise ContactCasError("invalid message sha256")
        if status=="sent":
            sent=_parse_utc(e["sent_at"])
            if sent<armed: raise ContactCasError("sent_at precedes armed_at")
            r=e["provider_receipt_sha256"]
            if not isinstance(r,str) or not SHA256_RE.fullmatch(r): raise ContactCasError("invalid provider receipt sha256")

def validate_state(s: Any) -> dict[str,Any]:
    if not isinstance(s,dict) or set(s)!={"schema","revision","targets"}: raise ContactCasError("state keys are invalid")
    if s["schema"]!=SCHEMA: raise ContactCasError("unsupported schema")
    r=_plain_int(s["revision"],"revision")
    if r<0: raise ContactCasError("revision must be nonnegative")
    if not isinstance(s["targets"],dict): raise ContactCasError("targets must be object")
    for k,e in s["targets"].items():
        if not isinstance(k,str) or not SHA256_RE.fullmatch(k): raise ContactCasError("target key must be lowercase sha256")
        _validate_entry(e)
    return json.loads(json.dumps(s,sort_keys=True,separators=(",",":")))

def _bump(s: Mapping[str,Any]) -> dict[str,Any]:
    out=validate_state(s); out["revision"]+=1; return out

def claim(s: Mapping[str,Any], *, target_digest:str, owner:str, nonce:str, now:str,
          lease_seconds:int=DEFAULT_CLAIM_SECONDS) -> dict[str,Any]:
    out=_bump(s)
    if not SHA256_RE.fullmatch(target_digest): raise ContactCasError("invalid target digest")
    if not OWNER_RE.fullmatch(owner): raise ContactCasError("invalid owner")
    if not NONCE_RE.fullmatch(nonce): raise ContactCasError("invalid nonce")
    lease_seconds=_plain_int(lease_seconds,"lease_seconds")
    if not 1<=lease_seconds<=MAX_CLAIM_SECONDS: raise ContactCasError("lease_seconds out of bounds")
    nowdt=_parse_utc(now); old=out["targets"].get(target_digest)
    if old:
        if old["status"] in {"armed","sent"}: raise ContactCasError(f"target is {old['status']}; do not send")
        if nowdt < _parse_utc(old["lease_until"]):
            if old["owner"]==owner and old["nonce"]==nonce: return out
            raise ContactCasError("target has an active claim")
    out["targets"][target_digest]={"status":"claimed","owner":owner,"nonce":nonce,"claim_at":now,
        "lease_until":_fmt_utc(nowdt+timedelta(seconds=lease_seconds))}
    return validate_state(out)

def arm(s: Mapping[str,Any], *, target_digest:str, owner:str, nonce:str, now:str,
        message_sha256:str) -> dict[str,Any]:
    out=_bump(s); nowdt=_parse_utc(now)
    if not SHA256_RE.fullmatch(message_sha256): raise ContactCasError("invalid message sha256")
    e=out["targets"].get(target_digest)
    if not e or e["status"]!="claimed": raise ContactCasError("target must have a live claim before arming")
    if (e["owner"],e["nonce"])!=(owner,nonce): raise ContactCasError("claim owner/nonce mismatch")
    if nowdt >= _parse_utc(e["lease_until"]): raise ContactCasError("claim expired before arming")
    out["targets"][target_digest]={"status":"armed","owner":owner,"nonce":nonce,"claim_at":e["claim_at"],
        "armed_at":now,"message_sha256":message_sha256}
    return validate_state(out)

def gate(s: Mapping[str,Any], *, target_digest:str, owner:str, nonce:str, message_sha256:str) -> bool:
    e=validate_state(s)["targets"].get(target_digest)
    return bool(e and e["status"]=="armed" and e["owner"]==owner and e["nonce"]==nonce
                and e["message_sha256"]==message_sha256)

def record_sent(s: Mapping[str,Any], *, target_digest:str, owner:str, nonce:str, now:str,
                message_sha256:str, provider_receipt_sha256:str) -> dict[str,Any]:
    out=_bump(s); _parse_utc(now)
    if not SHA256_RE.fullmatch(message_sha256) or not SHA256_RE.fullmatch(provider_receipt_sha256):
        raise ContactCasError("invalid sha256")
    e=out["targets"].get(target_digest)
    if not e or e["status"]!="armed": raise ContactCasError("target is not armed")
    if (e["owner"],e["nonce"],e["message_sha256"])!=(owner,nonce,message_sha256):
        raise ContactCasError("armed send identity mismatch")
    out["targets"][target_digest]={**e,"status":"sent","sent_at":now,
        "provider_receipt_sha256":provider_receipt_sha256}
    return validate_state(out)

def release_claimed(s: Mapping[str,Any], *, target_digest:str, owner:str, nonce:str) -> dict[str,Any]:
    out=_bump(s); e=out["targets"].get(target_digest)
    if not e or e["status"]!="claimed": raise ContactCasError("only a claimed target may be released automatically")
    if (e["owner"],e["nonce"])!=(owner,nonce): raise ContactCasError("claim owner/nonce mismatch")
    del out["targets"][target_digest]; return validate_state(out)

def reconcile_armed_not_sent(s: Mapping[str,Any], *, target_digest:str, owner:str, nonce:str,
                             sent_history_checked:bool) -> dict[str,Any]:
    if sent_history_checked is not True:
        raise ContactCasError("armed recovery requires affirmative Sent-history verification")
    out=_bump(s); e=out["targets"].get(target_digest)
    if not e or e["status"]!="armed": raise ContactCasError("target is not armed")
    if (e["owner"],e["nonce"])!=(owner,nonce): raise ContactCasError("armed owner/nonce mismatch")
    del out["targets"][target_digest]; return validate_state(out)

def _reject_duplicate_pairs(pairs):
    out={}
    for k,v in pairs:
        if k in out: raise ContactCasError(f"duplicate JSON key: {k}")
        out[k]=v
    return out

def _load(path:Path):
    try: return validate_state(json.loads(path.read_text(),object_pairs_hook=_reject_duplicate_pairs))
    except json.JSONDecodeError as e: raise ContactCasError(f"invalid JSON: {e.msg}") from e

def _dump(s): return json.dumps(validate_state(s),sort_keys=True,indent=2)+"\n"
def _target(a):
    if bool(a.email)==bool(a.public_target): raise ContactCasError("provide exactly one target")
    return target_digest_for_email(a.email) if a.email else target_digest_for_public_id(a.public_target)
def _target_args(p): p.add_argument("--email"); p.add_argument("--public-target")

def parser():
    p=argparse.ArgumentParser(); sub=p.add_subparsers(dest="cmd",required=True)
    q=sub.add_parser("init"); q.add_argument("state")
    q=sub.add_parser("digest"); _target_args(q)
    q=sub.add_parser("message-digest"); q.add_argument("--subject",required=True); q.add_argument("--body-file",required=True)
    for name in ("claim","arm","gate","sent","release","reconcile-not-sent"):
        q=sub.add_parser(name); q.add_argument("state"); _target_args(q)
        q.add_argument("--owner",required=True); q.add_argument("--nonce",required=True)
        if name in {"claim","arm","sent"}: q.add_argument("--now",required=True)
        if name=="claim": q.add_argument("--lease-seconds",type=int,default=DEFAULT_CLAIM_SECONDS)
        if name in {"arm","gate","sent"}: q.add_argument("--message-sha256",required=True)
        if name=="sent": q.add_argument("--provider-receipt-sha256",required=True)
        if name=="reconcile-not-sent": q.add_argument("--sent-history-checked",action="store_true")
    return p

def main(argv=None):
    a=parser().parse_args(argv)
    try:
        if a.cmd=="init": Path(a.state).write_text(_dump(empty_state())); return 0
        if a.cmd=="digest": print(_target(a)); return 0
        if a.cmd=="message-digest": print(message_digest(a.subject,Path(a.body_file).read_text())); return 0
        s=_load(Path(a.state)); td=_target(a)
        if a.cmd=="claim": out=claim(s,target_digest=td,owner=a.owner,nonce=a.nonce,now=a.now,lease_seconds=a.lease_seconds)
        elif a.cmd=="arm": out=arm(s,target_digest=td,owner=a.owner,nonce=a.nonce,now=a.now,message_sha256=a.message_sha256)
        elif a.cmd=="gate":
            ok=gate(s,target_digest=td,owner=a.owner,nonce=a.nonce,message_sha256=a.message_sha256)
            print("ALLOW" if ok else "DENY"); return 0 if ok else 3
        elif a.cmd=="sent": out=record_sent(s,target_digest=td,owner=a.owner,nonce=a.nonce,now=a.now,
            message_sha256=a.message_sha256,provider_receipt_sha256=a.provider_receipt_sha256)
        elif a.cmd=="release": out=release_claimed(s,target_digest=td,owner=a.owner,nonce=a.nonce)
        else: out=reconcile_armed_not_sent(s,target_digest=td,owner=a.owner,nonce=a.nonce,
            sent_history_checked=a.sent_history_checked)
        sys.stdout.write(_dump(out)); return 0
    except (ContactCasError,OSError) as e:
        print(f"ERROR: {e}",file=sys.stderr); return 2

if __name__=="__main__": raise SystemExit(main())
