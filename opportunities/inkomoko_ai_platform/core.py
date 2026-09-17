from __future__ import annotations
import hashlib,json,os,re,stat
from datetime import datetime,timedelta,timezone
from pathlib import Path
from typing import Any

ROOT={"schema_version","opportunity","requirements","authority_ceiling"}
OPP={"id","buyer","title","submission_deadline_date","submission_deadline_time_known","submission_route","mandatory_subject_template","source_authority","source_url","observed_at"}
REQ={"id","category","description","mandatory","partner_curable","source_coordinate"}
CAND={"schema_version","candidate_id","generation","vendor_name","evidence","specialist_capabilities"}
EVID={"requirement_id","state","authority","evidence_ref","source_url","source_sha256","observed_at"}
CAP={"id","description","evidence_ref"}
AUTH={"buyer_contact","proposal_submission","signature","contract_acceptance","price_commitment","award_claim","payment_claim","revenue_claim","production_data_access"}
CAPS={"AI_EVALUATION_ACCEPTANCE","INTEGRATION_CONTRACT_TESTING","REPLAY_IDEMPOTENCY","AUDIT_EVIDENCE","MIGRATION_RECONCILIATION","MULTILINGUAL_EVALUATION","HUMAN_ESCALATION_EVALUATION"}
HEX=re.compile(r"^[0-9a-f]{64}$"); IDENT=re.compile(r"^[A-Z0-9][A-Z0-9._:/-]{0,127}$")
REF=re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/#-]{0,255}$")
URL=re.compile(r"^https://[A-Za-z0-9.-]+(?::[0-9]{1,5})?(?:/[^\s]*)?$")
MAIL=re.compile(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")

class CarrierError(ValueError):pass
def _constant(v):raise CarrierError(f"non-finite JSON constant rejected: {v}")
def _pairs(items):
    d={}
    for k,v in items:
        if k in d:raise CarrierError(f"duplicate JSON key: {k}")
        d[k]=v
    return d
def loads_strict(text):
    try:return json.loads(text,object_pairs_hook=_pairs,parse_constant=_constant)
    except CarrierError:raise
    except (json.JSONDecodeError,UnicodeError) as e:raise CarrierError(f"invalid JSON: {e}") from e
def load_json_file(path,max_bytes=2_000_000):
    p=Path(path);s=os.lstat(p)
    if stat.S_ISLNK(s.st_mode):raise CarrierError("symlink input refused")
    if not stat.S_ISREG(s.st_mode):raise CarrierError("input must be a regular file")
    if s.st_size>max_bytes:raise CarrierError("input exceeds byte limit")
    b=p.read_bytes()
    if len(b)>max_bytes:raise CarrierError("input exceeds byte limit")
    try:return loads_strict(b.decode())
    except UnicodeDecodeError as e:raise CarrierError("input must be UTF-8") from e
def keys(o,w,label):
    if type(o) is not dict or set(o)!=w:
        got=set(o) if type(o) is dict else set()
        raise CarrierError(f"{label} keys mismatch; missing={sorted(w-got)} extra={sorted(got-w)}")
def text(v,label,n=1000):
    if type(v) is not str or not v or len(v)>n:raise CarrierError(f"{label} must be non-empty text <= {n}")
    return v
def integer(v,label,lo=0,hi=1_000_000):
    if type(v) is not int or not lo<=v<=hi:raise CarrierError(f"{label} must be integer in [{lo}, {hi}]")
    return v
def boolean(v,label):
    if type(v) is not bool:raise CarrierError(f"{label} must be boolean")
    return v
def timestamp(v,label):
    s=text(v,label,64)
    if not s.endswith("Z"):raise CarrierError(f"{label} must be UTC Z timestamp")
    try:d=datetime.fromisoformat(s[:-1]+"+00:00")
    except ValueError as e:raise CarrierError(f"{label} invalid timestamp") from e
    if d.utcoffset()!=timedelta(0):raise CarrierError(f"{label} must be UTC")
    return d
def url(v,label):
    s=text(v,label,500)
    if not URL.fullmatch(s):raise CarrierError(f"{label} must be an https URL")
    return s
def canonical(o):return json.dumps(o,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()
def digest(o):return hashlib.sha256(canonical(o)).hexdigest()

def validate_reference(r):
    keys(r,ROOT,"reference");integer(r["schema_version"],"reference.schema_version",1,1)
    o=r["opportunity"];keys(o,OPP,"reference.opportunity")
    for k,n in (("id",128),("buyer",128),("title",300),("mandatory_subject_template",300)):text(o[k],k,n)
    try:datetime.strptime(text(o["submission_deadline_date"],"deadline",10),"%Y-%m-%d")
    except ValueError as e:raise CarrierError("submission_deadline_date must be YYYY-MM-DD") from e
    boolean(o["submission_deadline_time_known"],"deadline_time_known")
    if not MAIL.fullmatch(text(o["submission_route"],"submission_route",254)):raise CarrierError("submission_route must be an email address")
    if o["source_authority"] not in {"BUYER_FIRST_PARTY","PUBLIC_REPRODUCTION_NOT_BUYER_DOMAIN"}:raise CarrierError("unknown source_authority")
    url(o["source_url"],"source_url");timestamp(o["observed_at"],"observed_at")
    if type(r["requirements"]) is not list or not r["requirements"] or len(r["requirements"])>200:raise CarrierError("requirements must be a non-empty bounded list")
    seen=set()
    for i,q in enumerate(r["requirements"]):
        keys(q,REQ,f"requirement[{i}]");rid=text(q["id"],"requirement.id",128)
        if not IDENT.fullmatch(rid) or rid in seen:raise CarrierError(f"duplicate or invalid requirement id: {rid}")
        seen.add(rid)
        if q["category"] not in {"TECHNICAL","QUALIFICATION","SUBMISSION","COMMERCIAL"}:raise CarrierError("invalid requirement category")
        text(q["description"],"requirement.description");boolean(q["mandatory"],"mandatory");boolean(q["partner_curable"],"partner_curable");text(q["source_coordinate"],"source_coordinate",120)
    keys(r["authority_ceiling"],AUTH,"authority_ceiling")
    if any(boolean(v,k) for k,v in r["authority_ceiling"].items()):raise CarrierError("authority ceiling must remain false")
    return r
