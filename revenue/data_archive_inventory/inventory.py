from __future__ import annotations
import csv, hashlib, io, json, math, re
from datetime import datetime, timezone
from typing import Any, Mapping

SCHEMA="commons-data-archive-inventory/v1"
RECEIPT_SCHEMA="commons-data-archive-inventory-receipt/v1"
ELIGIBLE="ELIGIBLE_FOR_DATA_LICENSE_DESK"
HOLD="HOLD"
RIGHTS={"OWNED","LICENSED_FOR_REDISTRIBUTION","PUBLIC_DOMAIN"}
GRANTS={"EVALUATION","INTERNAL_USE","COMMERCIAL_USE"}
HEX64=re.compile(r"^[0-9a-f]{64}$")
ID=re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")

class InventoryError(ValueError): pass

def canonical_json(v: Any)->bytes:
    return (json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False)+"\n").encode()

def sha256(b:bytes)->str: return hashlib.sha256(b).hexdigest()

def _time(v:Any, field:str)->datetime:
    if not isinstance(v,str) or not v.endswith("Z"): raise InventoryError(f"{field} must be UTC RFC3339 Z time")
    try: d=datetime.fromisoformat(v[:-1]+"+00:00")
    except ValueError as e: raise InventoryError(f"{field} invalid timestamp") from e
    return d.astimezone(timezone.utc)

def _sha(v:Any, field:str)->str:
    if not isinstance(v,str) or not HEX64.fullmatch(v): raise InventoryError(f"{field} must be lowercase sha256")
    return v

def _id(v:Any, field:str)->str:
    if not isinstance(v,str) or not ID.fullmatch(v): raise InventoryError(f"{field} invalid")
    return v

def _path(v:Any)->str:
    if not isinstance(v,str) or not v or len(v)>512: raise InventoryError("repo_path invalid")
    if v.startswith(("/","\\")) or "\\" in v or "\x00" in v: raise InventoryError("repo_path must be relative POSIX path")
    parts=v.split("/")
    if any(p in ("",".","..") for p in parts): raise InventoryError("repo_path contains unsafe segment")
    return v

def _validate_json(v:Any, path:str="$")->None:
    if v is None or isinstance(v,(str,bool,int)): return
    if isinstance(v,float):
        if not math.isfinite(v): raise InventoryError(f"{path} non-finite")
        return
    if isinstance(v,list):
        for i,x in enumerate(v): _validate_json(x,f"{path}[{i}]")
        return
    if isinstance(v,dict):
        for k,x in v.items():
            if not isinstance(k,str): raise InventoryError(f"{path} non-string key")
            _validate_json(x,f"{path}.{k}")
        return
    raise InventoryError(f"{path} unsupported value")

def _one(a:Mapping[str,Any], now:datetime)->dict[str,Any]:
    reasons=[]
    try:
        asset_id=_id(a.get("asset_id"),"asset_id")
        repo_path=_path(a.get("repo_path"))
        version=_id(a.get("version"),"version")
        asset_sha=_sha(a.get("asset_sha256"),"asset_sha256")
        prov_sha=_sha(a.get("provenance_sha256"),"provenance_sha256")
        if a.get("source_kind")!="REGULAR_FILE": reasons.append("SOURCE_NOT_RECORDED_REGULAR_FILE")
        rights=a.get("rights")
        if not isinstance(rights,dict): raise InventoryError("rights must be object")
        basis=rights.get("basis")
        if basis not in RIGHTS: reasons.append("RIGHTS_UNKNOWN_OR_NOT_REDISTRIBUTABLE")
        license_id=_id(rights.get("license_id"),"rights.license_id")
        license_evidence=_sha(rights.get("license_evidence_sha256"),"rights.license_evidence_sha256")
        grants=rights.get("permitted_grants")
        if not isinstance(grants,list) or not grants or any(not isinstance(g,str) or g not in GRANTS for g in grants) or len(set(grants))!=len(grants): raise InventoryError("rights.permitted_grants invalid")
        transfer=rights.get("transfer_allowed") is True
        publish=rights.get("publication_allowed") is True
        if not transfer: reasons.append("TRANSFER_NOT_RECORDED_ALLOWED")
        if not publish: reasons.append("PUBLICATION_NOT_RECORDED_ALLOWED")
        sensitive=a.get("sensitive_class")
        if sensitive not in {"PUBLIC","REDACTED"}: reasons.append("SENSITIVE_CLASS_NOT_PUBLIC_OR_REDACTED")
        red=a.get("redaction")
        if not isinstance(red,dict): raise InventoryError("redaction must be object")
        if sensitive=="REDACTED":
            if red.get("status")!="VERIFIED": reasons.append("REDACTION_NOT_VERIFIED")
            _sha(red.get("policy_sha256"),"redaction.policy_sha256")
            _sha(red.get("review_evidence_sha256"),"redaction.review_evidence_sha256")
            if _time(red.get("reviewed_at"),"redaction.reviewed_at")>now: reasons.append("REDACTION_REVIEW_IN_FUTURE")
        elif sensitive=="PUBLIC" and red.get("status")!="NOT_REQUIRED": reasons.append("PUBLIC_REDACTION_STATE_INVALID")
        valid_until=a.get("evidence_valid_until")
        if valid_until is not None and _time(valid_until,"evidence_valid_until")<=now: reasons.append("EVIDENCE_STALE")
        _validate_json(a.get("provenance",{}),"provenance")
        status=ELIGIBLE if not reasons else HOLD
        row={
            "asset_id":asset_id,"repo_path":repo_path,"version":version,"status":status,"reasons":sorted(set(reasons)),
            "asset_sha256":asset_sha,"provenance_sha256":prov_sha,
            "rights":{"basis":basis,"license_id":license_id,"license_evidence_sha256":license_evidence,"permitted_grants":grants,"transfer_allowed":transfer,"publication_allowed":publish},
            "sensitive_class":sensitive,"redaction":red,"evidence_valid_until":valid_until,
            "license_desk_seed": None,
        }
        if status==ELIGIBLE:
            row["license_desk_seed"]={
                "dataset_id":asset_id,"version":version,"source_sha256":asset_sha,"provenance_sha256":prov_sha,
                "rights":{"basis":basis,"license_id":license_id,"license_evidence_sha256":license_evidence,"permitted_grants":grants,"transfer_allowed":transfer},
                "sensitive_class":sensitive,"redaction":red,
                "remaining_requirements":["schema_fields","sample_rows","offer"],
            }
        return row
    except InventoryError as e:
        return {"asset_id":a.get("asset_id") if isinstance(a.get("asset_id"),str) else "<invalid>","repo_path":a.get("repo_path") if isinstance(a.get("repo_path"),str) else "<invalid>","version":a.get("version") if isinstance(a.get("version"),str) else "<invalid>","status":HOLD,"reasons":[f"MALFORMED:{e}"],"license_desk_seed":None}

def _csv(rows:list[dict[str,Any]])->bytes:
    out=io.StringIO(newline="")
    w=csv.writer(out,lineterminator="\n")
    w.writerow(["asset_id","repo_path","version","status","reasons","asset_sha256","provenance_sha256","rights_basis","license_id","sensitive_class"])
    for r in sorted(rows,key=lambda x:(x.get("asset_id",""),x.get("repo_path",""))):
        rights=r.get("rights") or {}
        w.writerow([r.get("asset_id",""),r.get("repo_path",""),r.get("version",""),r.get("status",""),";".join(r.get("reasons",[])),r.get("asset_sha256","") or "",r.get("provenance_sha256","") or "",rights.get("basis","") or "",rights.get("license_id","") or "",r.get("sensitive_class","") or ""])
    return out.getvalue().encode()

def compile_inventory(doc:Mapping[str,Any], trusted_at:str)->tuple[dict[str,Any],bytes]:
    if not isinstance(doc,dict) or doc.get("schema")!=SCHEMA: raise InventoryError(f"schema must be {SCHEMA}")
    now=_time(trusted_at,"trusted_at")
    assets=doc.get("assets")
    if not isinstance(assets,list) or not assets: raise InventoryError("assets must be nonempty list")
    ids=[]; paths=[]
    for a in assets:
        if not isinstance(a,dict): raise InventoryError("asset must be object")
        ids.append(a.get("asset_id")); paths.append(a.get("repo_path"))
    valid_ids=[x for x in ids if isinstance(x,str)]
    valid_paths=[x for x in paths if isinstance(x,str)]
    if len(set(valid_ids))!=len(valid_ids): raise InventoryError("duplicate asset_id")
    if len(set(valid_paths))!=len(valid_paths): raise InventoryError("duplicate repo_path")
    rows=[_one(a,now) for a in assets]
    csv_bytes=_csv(rows)
    eligible=sum(r["status"]==ELIGIBLE for r in rows)
    receipt={"schema":RECEIPT_SCHEMA,"evaluated_at":trusted_at,"decision":ELIGIBLE if eligible==len(rows) else HOLD,"counts":{"total":len(rows),"eligible":eligible,"hold":len(rows)-eligible},"assets":sorted(rows,key=lambda r:r["asset_id"]),"csv_sha256":sha256(csv_bytes),"authority":{"inventory_complete_for_declared_assets":True,"archive_scanned":False,"rights_invented":False,"publication_authorized":False,"transfer_authorized":False,"license_executed":False,"revenue_recognized":False}}
    receipt["receipt_sha256"]=sha256(canonical_json(receipt))
    return receipt,csv_bytes

def verify_inventory(doc:Mapping[str,Any],receipt:Mapping[str,Any],csv_bytes:bytes,trusted_at:str)->bool:
    expected,exp_csv=compile_inventory(doc,trusted_at)
    return canonical_json(expected)==canonical_json(receipt) and exp_csv==csv_bytes
