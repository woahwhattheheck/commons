#!/usr/bin/env python3
"""Deterministic evidence-only acceptance engine for Exeter CA RFP 2026-06."""
from __future__ import annotations
import hashlib, json, os, re, sys
from pathlib import Path
from typing import Any, Iterable

INPUT_SCHEMA="tjlabs.exeter_finance_acceptance/v1"
REPORT_SCHEMA="tjlabs.exeter_finance_acceptance.report/v1"
AUTHORITY="EVIDENCE_ONLY_NO_BUYER_OR_PRODUCTION_ACCEPTANCE"
MAX_INPUT_BYTES=1_048_576
MAX_STRING=512
MAX_ROWS=10_000
SHA256_RE=re.compile(r"^[0-9a-f]{64}$")
TOP_KEYS={"schema","generation","crosswalks","control_totals","subledgers","bank_reconciliation","required_interfaces","interfaces","uat","cutover"}
CROSSWALK_KEYS=("accounts","vendors","customers","employees")
SUBLEDGER_KEYS=("ap","ar","payroll","utility","cashiering")
REQUIRED_UAT=("GL_FUND_ACCOUNTING","AP","AR","PAYROLL","CASHIERING","BANK_RECONCILIATION","UTILITY_BILLING","FINANCIAL_REPORTING","INTEGRATIONS","DATA_CONVERSION")

class PacketError(ValueError):
    def __init__(self,code:str,path:str,detail:str="")->None:
        super().__init__(f"{code}:{path}:{detail}"); self.code=code; self.path=path; self.detail=detail

def _canonical(v:Any)->str: return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":"))
def _sha256_text(v:str)->str: return hashlib.sha256(v.encode("utf-8")).hexdigest()

def _exact_dict(v:Any,keys:Iterable[str],path:str)->dict[str,Any]:
    if type(v) is not dict: raise PacketError("TYPE_OBJECT_REQUIRED",path)
    expected=set(keys); actual=set(v)
    if actual!=expected:
        raise PacketError("OBJECT_KEYS_INVALID",path,f"missing={','.join(sorted(expected-actual))};extra={','.join(sorted(actual-expected))}")
    return v

def _string(v:Any,path:str)->str:
    if type(v) is not str: raise PacketError("TYPE_STRING_REQUIRED",path)
    if not v or len(v)>MAX_STRING: raise PacketError("STRING_BOUNDS_INVALID",path)
    if "\x00" in v: raise PacketError("STRING_NUL_FORBIDDEN",path)
    return v

def _digest(v:Any,path:str,allow_none:bool=False)->str|None:
    if allow_none and v is None: return None
    s=_string(v,path)
    if not SHA256_RE.fullmatch(s): raise PacketError("SHA256_INVALID",path)
    return s

def _integer(v:Any,path:str,minimum:int|None=None)->int:
    if type(v) is not int: raise PacketError("TYPE_INTEGER_REQUIRED",path)
    if minimum is not None and v<minimum: raise PacketError("INTEGER_RANGE_INVALID",path)
    return v

def _bool(v:Any,path:str)->bool:
    if type(v) is not bool: raise PacketError("TYPE_BOOLEAN_REQUIRED",path)
    return v

def _list(v:Any,path:str,nonempty:bool=False)->list[Any]:
    if type(v) is not list: raise PacketError("TYPE_ARRAY_REQUIRED",path)
    if len(v)>MAX_ROWS or (nonempty and not v): raise PacketError("ARRAY_BOUNDS_INVALID",path)
    return v

def _unique(rows:list[dict[str,Any]],path:str,key:str="id")->None:
    seen=set()
    for i,row in enumerate(rows):
        ident=_string(row[key],f"{path}[{i}].{key}")
        if ident in seen: raise PacketError("DUPLICATE_ID",f"{path}[{i}].{key}",ident)
        seen.add(ident)

def _exception(code:str,path:str,detail:str)->dict[str,str]:
    ident={"code":code,"path":path,"detail":detail}
    return {"id":_sha256_text(_canonical(ident))[:20],**ident}

def _validate(packet:Any)->dict[str,Any]:
    b=_exact_dict(packet,TOP_KEYS,"$")
    if b["schema"]!=INPUT_SCHEMA: raise PacketError("SCHEMA_INVALID","$.schema")
    g=_exact_dict(b["generation"],("source_sha256","target_sha256"),"$.generation")
    _digest(g["source_sha256"],"$.generation.source_sha256"); _digest(g["target_sha256"],"$.generation.target_sha256")
    cw=_exact_dict(b["crosswalks"],CROSSWALK_KEYS,"$.crosswalks")
    for category in CROSSWALK_KEYS:
        rows=_list(cw[category],f"$.crosswalks.{category}",True); seen=set()
        for i,value in enumerate(rows):
            row=_exact_dict(value,("source_id","target_id"),f"$.crosswalks.{category}[{i}]")
            source=_string(row["source_id"],f"$.crosswalks.{category}[{i}].source_id")
            _string(row["target_id"],f"$.crosswalks.{category}[{i}].target_id")
            if source in seen: raise PacketError("DUPLICATE_SOURCE_ID",f"$.crosswalks.{category}[{i}].source_id",source)
            seen.add(source)
    controls=_list(b["control_totals"],"$.control_totals",True); normalized=[]
    for i,value in enumerate(controls):
        row=_exact_dict(value,("id","source_cents","target_cents"),f"$.control_totals[{i}]")
        _string(row["id"],f"$.control_totals[{i}].id"); _integer(row["source_cents"],f"$.control_totals[{i}].source_cents"); _integer(row["target_cents"],f"$.control_totals[{i}].target_cents"); normalized.append(row)
    _unique(normalized,"$.control_totals")
    sl=_exact_dict(b["subledgers"],SUBLEDGER_KEYS,"$.subledgers")
    ledger_keys=("source_count","target_count","approved_count_delta","source_cents","target_cents","approved_amount_delta_cents","adjustment_sha256","exceptions")
    for name in SUBLEDGER_KEYS:
        row=_exact_dict(sl[name],ledger_keys,f"$.subledgers.{name}")
        _integer(row["source_count"],f"$.subledgers.{name}.source_count",0); _integer(row["target_count"],f"$.subledgers.{name}.target_count",0)
        _integer(row["approved_count_delta"],f"$.subledgers.{name}.approved_count_delta"); _integer(row["source_cents"],f"$.subledgers.{name}.source_cents"); _integer(row["target_cents"],f"$.subledgers.{name}.target_cents"); _integer(row["approved_amount_delta_cents"],f"$.subledgers.{name}.approved_amount_delta_cents")
        _digest(row["adjustment_sha256"],f"$.subledgers.{name}.adjustment_sha256",True)
        excs=_list(row["exceptions"],f"$.subledgers.{name}.exceptions"); seen=set()
        for i,v in enumerate(excs):
            ident=_string(v,f"$.subledgers.{name}.exceptions[{i}]")
            if ident in seen: raise PacketError("DUPLICATE_EXCEPTION_ID",f"$.subledgers.{name}.exceptions[{i}]",ident)
            seen.add(ident)
    bank=_exact_dict(b["bank_reconciliation"],("statement_ending_cents","statement_additions_cents","statement_deductions_cents","book_ending_cents","book_additions_cents","book_deductions_cents","reconciled_cents"),"$.bank_reconciliation")
    for key in bank: _integer(bank[key],f"$.bank_reconciliation.{key}")
    required=_list(b["required_interfaces"],"$.required_interfaces",True); seen=set()
    for i,v in enumerate(required):
        ident=_string(v,f"$.required_interfaces[{i}]")
        if ident in seen: raise PacketError("DUPLICATE_REQUIRED_INTERFACE",f"$.required_interfaces[{i}]",ident)
        seen.add(ident)
    interfaces=_list(b["interfaces"],"$.interfaces"); normalized=[]
    for i,v in enumerate(interfaces):
        row=_exact_dict(v,("id","source","target","manifest_sha256","status"),f"$.interfaces[{i}]")
        for key in ("id","source","target","status"): _string(row[key],f"$.interfaces[{i}].{key}")
        _digest(row["manifest_sha256"],f"$.interfaces[{i}].manifest_sha256"); normalized.append(row)
    _unique(normalized,"$.interfaces")
    uat=_list(b["uat"],"$.uat"); normalized=[]
    for i,v in enumerate(uat):
        row=_exact_dict(v,("id","mandatory","status","evidence_sha256"),f"$.uat[{i}]")
        _string(row["id"],f"$.uat[{i}].id"); _bool(row["mandatory"],f"$.uat[{i}].mandatory"); _string(row["status"],f"$.uat[{i}].status"); _digest(row["evidence_sha256"],f"$.uat[{i}].evidence_sha256"); normalized.append(row)
    _unique(normalized,"$.uat")
    cut=_exact_dict(b["cutover"],("source_freeze_sha256","rollback_receipt_sha256","replay_receipt_sha256","unresolved_exceptions"),"$.cutover")
    for key in ("source_freeze_sha256","rollback_receipt_sha256","replay_receipt_sha256"): _digest(cut[key],f"$.cutover.{key}")
    seen=set()
    for i,v in enumerate(_list(cut["unresolved_exceptions"],"$.cutover.unresolved_exceptions")):
        ident=_string(v,f"$.cutover.unresolved_exceptions[{i}]")
        if ident in seen: raise PacketError("DUPLICATE_EXCEPTION_ID",f"$.cutover.unresolved_exceptions[{i}]",ident)
        seen.add(ident)
    return b

def evaluate(packet:Any)->dict[str,Any]:
    b=_validate(packet); failures=[]
    for i,row in enumerate(b["control_totals"]):
        if row["source_cents"]!=row["target_cents"]: failures.append(_exception("CONTROL_TOTAL_MISMATCH",f"$.control_totals[{i}]",row["id"]))
    for name in SUBLEDGER_KEYS:
        row=b["subledgers"][name]; count_delta=row["target_count"]-row["source_count"]; amount_delta=row["target_cents"]-row["source_cents"]
        if count_delta!=row["approved_count_delta"]: failures.append(_exception("SUBLEDGER_COUNT_DELTA_MISMATCH",f"$.subledgers.{name}",name))
        if amount_delta!=row["approved_amount_delta_cents"]: failures.append(_exception("SUBLEDGER_AMOUNT_DELTA_MISMATCH",f"$.subledgers.{name}",name))
        approved=row["approved_count_delta"]!=0 or row["approved_amount_delta_cents"]!=0
        if approved and row["adjustment_sha256"] is None: failures.append(_exception("ADJUSTMENT_EVIDENCE_MISSING",f"$.subledgers.{name}",name))
        if not approved and row["adjustment_sha256"] is not None: failures.append(_exception("UNNEEDED_ADJUSTMENT_EVIDENCE",f"$.subledgers.{name}",name))
        for exc in row["exceptions"]: failures.append(_exception("SUBLEDGER_EXCEPTION_OPEN",f"$.subledgers.{name}.exceptions",exc))
    bank=b["bank_reconciliation"]; statement=bank["statement_ending_cents"]+bank["statement_additions_cents"]-bank["statement_deductions_cents"]; book=bank["book_ending_cents"]+bank["book_additions_cents"]-bank["book_deductions_cents"]; rec=bank["reconciled_cents"]
    if statement!=rec: failures.append(_exception("BANK_STATEMENT_RECON_MISMATCH","$.bank_reconciliation",str(statement)))
    if book!=rec: failures.append(_exception("BANK_BOOK_RECON_MISMATCH","$.bank_reconciliation",str(book)))
    by_interface={row["id"]:row for row in b["interfaces"]}
    for required in b["required_interfaces"]:
        row=by_interface.get(required)
        if row is None: failures.append(_exception("REQUIRED_INTERFACE_MISSING","$.interfaces",required))
        elif row["status"]!="verified": failures.append(_exception("INTERFACE_NOT_VERIFIED",f"$.interfaces[{required}]",row["status"]))
    by_uat={row["id"]:row for row in b["uat"]}
    for required in REQUIRED_UAT:
        row=by_uat.get(required)
        if row is None: failures.append(_exception("REQUIRED_UAT_MISSING","$.uat",required)); continue
        if row["mandatory"] is not True: failures.append(_exception("REQUIRED_UAT_NOT_MANDATORY",f"$.uat[{required}]",required))
        if row["status"]!="pass": failures.append(_exception("MANDATORY_UAT_NOT_PASS",f"$.uat[{required}]",row["status"]))
    for row in b["uat"]:
        if row["mandatory"] and row["status"]!="pass" and row["id"] not in REQUIRED_UAT: failures.append(_exception("MANDATORY_UAT_NOT_PASS",f"$.uat[{row['id']}]",row["status"]))
    for exc in b["cutover"]["unresolved_exceptions"]: failures.append(_exception("CUTOVER_EXCEPTION_OPEN","$.cutover.unresolved_exceptions",exc))
    failures.sort(key=lambda x:(x["code"],x["path"],x["detail"],x["id"])); ready=not failures
    return {"schema":REPORT_SCHEMA,"authority":AUTHORITY,"packet_sha256":_sha256_text(_canonical(b)),"status":"READY" if ready else "HOLD","ready":ready,"exception_count":len(failures),"exceptions":failures}

def _strict_pairs(pairs:list[tuple[str,Any]])->dict[str,Any]:
    out={}
    for key,value in pairs:
        if key in out: raise PacketError("DUPLICATE_JSON_KEY","$",key)
        out[key]=value
    return out

def load_packet(path:str|os.PathLike[str])->dict[str,Any]:
    try: raw=Path(path).read_bytes()
    except OSError as exc: raise PacketError("INPUT_UNREADABLE","$",type(exc).__name__) from exc
    if len(raw)>MAX_INPUT_BYTES: raise PacketError("INPUT_TOO_LARGE","$",str(len(raw)))
    try: text=raw.decode("utf-8",errors="strict")
    except UnicodeDecodeError as exc: raise PacketError("INPUT_UTF8_INVALID","$") from exc
    try: value=json.loads(text,object_pairs_hook=_strict_pairs)
    except PacketError: raise
    except (json.JSONDecodeError,RecursionError) as exc: raise PacketError("INPUT_JSON_INVALID","$") from exc
    if type(value) is not dict: raise PacketError("TYPE_OBJECT_REQUIRED","$")
    return value

def _error_receipt(error:PacketError)->str:
    return _canonical({"schema":"tjlabs.exeter_finance_acceptance.error/v1","authority":AUTHORITY,"code":error.code,"path":error.path})

def main(argv:list[str]|None=None)->int:
    args=sys.argv[1:] if argv is None else argv
    if len(args)!=1:
        sys.stderr.write(_canonical({"schema":"tjlabs.exeter_finance_acceptance.error/v1","authority":AUTHORITY,"code":"USAGE","path":"$"})+"\n"); return 64
    try: report=evaluate(load_packet(args[0]))
    except PacketError as error:
        sys.stderr.write(_error_receipt(error)+"\n"); return 64
    sys.stdout.write(_canonical(report)+"\n"); return 0 if report["ready"] else 2

if __name__=="__main__": raise SystemExit(main())
