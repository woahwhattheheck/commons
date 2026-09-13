"""Deterministic offline AI performance-evaluation proof for DAF26TZ06-NV006.

This module intentionally operates on synthetic/research-owned, already-observed scenario
results. It does not run models, simulators, operational systems, or external services.
"""
from __future__ import annotations
import hashlib, json, os, re, stat
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

SCENARIO_SCHEMA="daf-ai-eval-scenario-set/v1"; POLICY_SCHEMA="daf-ai-eval-policy/v1"; REPORT_SCHEMA="daf-ai-eval-report/v1"; ADAPTER_SCHEMA="daf-ai-eval-adapter-record/v1"
MAX_SCENARIOS=10000; MAX_FACTORS=32; SAFE_INT=2**53-1
ID_RE=re.compile(r"^[a-z0-9][a-z0-9._:-]{0,79}$"); HEX_RE=re.compile(r"^[0-9a-f]{64}$"); UTC_RE=re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
SCENARIO_KEYS={"scenario_id","family_id","condition","expected_label","observed_label","completed","latency_ms","explanation_factors","explanation_sha256"}
SET_KEYS={"schema","suite_id","captured_at","source_sha256","scenarios"}
POLICY_KEYS={"schema","policy_id","min_accuracy_bp","min_reliability_bp","min_robustness_bp","max_drift_drop_bp","min_explainability_bp","max_p95_latency_ms"}
ADAPTER_KEYS={"schema","adapter_id","provider_class","source_ref","source_sha256","synthetic_or_research_owned","claims_government_simulator_access"}
ALLOWED_CONDITIONS={"BASELINE","PERTURBATION","DRIFT"}; ALLOWED_PROVIDER_CLASSES={"SYNTHETIC","RESEARCH_OWNED_SIMULATOR","RECORDED_BENCH"}
REASON_ORDER=("ACCURACY_BELOW_MINIMUM","RELIABILITY_BELOW_MINIMUM","ROBUSTNESS_BELOW_MINIMUM","DRIFT_DROP_EXCEEDS_MAXIMUM","EXPLAINABILITY_BELOW_MINIMUM","P95_LATENCY_EXCEEDS_MAXIMUM")

class ContractError(ValueError): pass

def _pairs_no_duplicates(pairs: Iterable[tuple[str,Any]]) -> dict[str,Any]:
    out={}
    for k,v in pairs:
        if k in out: raise ContractError(f"duplicate JSON key: {k}")
        out[k]=v
    return out

def loads_strict(text:str)->Any:
    try:
        return json.loads(text, object_pairs_hook=_pairs_no_duplicates, parse_constant=lambda t: (_ for _ in ()).throw(ContractError(f"non-finite JSON constant: {t}")))
    except ContractError: raise
    except (json.JSONDecodeError,TypeError) as exc: raise ContractError(f"invalid JSON: {exc}") from exc

def canonical_bytes(value:Any)->bytes: return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=True,allow_nan=False).encode()
def sha256_hex(data:bytes)->str: return hashlib.sha256(data).hexdigest()
def _exact_keys(obj,keys,where):
    if set(obj)!=keys: raise ContractError(f"{where} keys mismatch; missing={sorted(keys-set(obj))}, extra={sorted(set(obj)-keys)}")
def _plain_int(v,where,minimum=0,maximum=SAFE_INT):
    if type(v) is not int: raise ContractError(f"{where} must be an integer")
    if v<minimum or v>maximum: raise ContractError(f"{where} out of range")
    return v
def _plain_bool(v,where):
    if type(v) is not bool: raise ContractError(f"{where} must be boolean")
    return v
def _id(v,where):
    if not isinstance(v,str) or not ID_RE.fullmatch(v): raise ContractError(f"{where} must be a bounded lowercase opaque id")
    return v
def _digest(v,where):
    if not isinstance(v,str) or not HEX_RE.fullmatch(v): raise ContractError(f"{where} must be lowercase sha256")
    return v
def _utc(v,where):
    if not isinstance(v,str) or not UTC_RE.fullmatch(v): raise ContractError(f"{where} must be canonical whole-second UTC")
    try: return datetime.strptime(v,"%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc: raise ContractError(f"{where} invalid UTC") from exc
def _bp(n,d): return 0 if d<=0 else (n*10000)//d
def _ceil_percentile(values,percent):
    if not values: return 0
    ordered=sorted(values); rank=(len(ordered)*percent+99)//100
    return ordered[max(0,rank-1)]

@dataclass(frozen=True)
class Scenario:
    scenario_id:str; family_id:str; condition:str; expected_label:str; observed_label:str; completed:bool; latency_ms:int; explanation_factors:tuple[str,...]; explanation_sha256:str
    @property
    def correct(self): return self.completed and self.expected_label==self.observed_label
    @property
    def explained(self): return bool(self.explanation_factors) and self.explanation_sha256!="0"*64

def validate_scenario_set(payload,*,trusted_now=None):
    if not isinstance(payload,dict): raise ContractError("scenario set must be object")
    _exact_keys(payload,SET_KEYS,"scenario set")
    if payload["schema"]!=SCENARIO_SCHEMA: raise ContractError("unsupported scenario schema")
    _id(payload["suite_id"],"suite_id"); captured=_utc(payload["captured_at"],"captured_at")
    now=trusted_now or datetime.now(timezone.utc)
    if captured>now: raise ContractError("captured_at is in the future")
    _digest(payload["source_sha256"],"source_sha256")
    rows=payload["scenarios"]
    if not isinstance(rows,list) or not 1<=len(rows)<=MAX_SCENARIOS: raise ContractError("scenarios must be non-empty bounded array")
    seen_ids=set(); baseline_families=set(); scenarios=[]
    for i,row in enumerate(rows):
        if not isinstance(row,dict): raise ContractError(f"scenario[{i}] must be object")
        _exact_keys(row,SCENARIO_KEYS,f"scenario[{i}]")
        sid=_id(row["scenario_id"],f"scenario[{i}].scenario_id"); family=_id(row["family_id"],f"scenario[{i}].family_id")
        if sid in seen_ids: raise ContractError(f"duplicate scenario_id: {sid}")
        seen_ids.add(sid); condition=row["condition"]
        if condition not in ALLOWED_CONDITIONS: raise ContractError(f"scenario[{i}].condition unsupported")
        for name in ("expected_label","observed_label"):
            if not isinstance(row[name],str) or not ID_RE.fullmatch(row[name]): raise ContractError(f"scenario[{i}].{name} invalid")
        completed=_plain_bool(row["completed"],f"scenario[{i}].completed"); latency=_plain_int(row["latency_ms"],f"scenario[{i}].latency_ms",maximum=86400000)
        factors=row["explanation_factors"]
        if not isinstance(factors,list) or len(factors)>MAX_FACTORS: raise ContractError(f"scenario[{i}].explanation_factors invalid")
        parsed=[]; seen_factor=set()
        for j,f in enumerate(factors):
            fid=_id(f,f"scenario[{i}].explanation_factors[{j}]")
            if fid in seen_factor: raise ContractError(f"scenario[{i}] duplicate explanation factor")
            seen_factor.add(fid); parsed.append(fid)
        ed=_digest(row["explanation_sha256"],f"scenario[{i}].explanation_sha256")
        if condition=="BASELINE":
            if family in baseline_families: raise ContractError(f"family {family} has multiple baselines")
            baseline_families.add(family)
        scenarios.append(Scenario(sid,family,condition,row["expected_label"],row["observed_label"],completed,latency,tuple(parsed),ed))
    family_conditions={}
    for r in scenarios: family_conditions.setdefault(r.family_id,set()).add(r.condition)
    for family,conditions in family_conditions.items():
        if ("PERTURBATION" in conditions or "DRIFT" in conditions) and "BASELINE" not in conditions: raise ContractError(f"family {family} lacks baseline")
    return payload,scenarios

def validate_policy(policy):
    if not isinstance(policy,dict): raise ContractError("policy must be object")
    _exact_keys(policy,POLICY_KEYS,"policy")
    if policy["schema"]!=POLICY_SCHEMA: raise ContractError("unsupported policy schema")
    _id(policy["policy_id"],"policy_id")
    for key in ("min_accuracy_bp","min_reliability_bp","min_robustness_bp","max_drift_drop_bp","min_explainability_bp"): _plain_int(policy[key],key,maximum=10000)
    _plain_int(policy["max_p95_latency_ms"],"max_p95_latency_ms",maximum=86400000)
    return policy

def validate_adapter_record(adapter):
    if not isinstance(adapter,dict): raise ContractError("adapter record must be object")
    _exact_keys(adapter,ADAPTER_KEYS,"adapter record")
    if adapter["schema"]!=ADAPTER_SCHEMA: raise ContractError("unsupported adapter schema")
    _id(adapter["adapter_id"],"adapter_id")
    if adapter["provider_class"] not in ALLOWED_PROVIDER_CLASSES: raise ContractError("provider_class unsupported")
    _id(adapter["source_ref"],"source_ref"); _digest(adapter["source_sha256"],"adapter source_sha256")
    if not _plain_bool(adapter["synthetic_or_research_owned"],"synthetic_or_research_owned"): raise ContractError("proof requires synthetic or research-owned source")
    if _plain_bool(adapter["claims_government_simulator_access"],"claims_government_simulator_access"): raise ContractError("proof may not claim government simulator access")
    return adapter

def evaluate(scenario_set,policy,adapter,*,trusted_now=None):
    source_obj,rows=validate_scenario_set(scenario_set,trusted_now=trusted_now); policy_obj=validate_policy(policy); adapter_obj=validate_adapter_record(adapter)
    completed=[r for r in rows if r.completed]; correct=[r for r in rows if r.correct]; baseline=[r for r in rows if r.condition=="BASELINE"]; perturb=[r for r in rows if r.condition=="PERTURBATION"]; drift=[r for r in rows if r.condition=="DRIFT"]
    baselines={r.family_id:r for r in baseline}; robust_pairs=robust_stable=0
    for r in perturb:
        base=baselines[r.family_id]
        if base.completed and r.completed:
            robust_pairs+=1
            if base.observed_label==r.observed_label==r.expected_label: robust_stable+=1
    baseline_accuracy=_bp(sum(1 for r in baseline if r.correct),len(baseline)); drift_accuracy=_bp(sum(1 for r in drift if r.correct),len(drift)) if drift else baseline_accuracy
    metrics={"scenario_count":len(rows),"completed_count":len(completed),"accuracy_bp":_bp(len(correct),len(rows)),"reliability_bp":_bp(len(completed),len(rows)),"robustness_bp":_bp(robust_stable,robust_pairs) if perturb else 10000,"robustness_pair_count":robust_pairs,"baseline_accuracy_bp":baseline_accuracy,"drift_accuracy_bp":drift_accuracy,"drift_drop_bp":max(0,baseline_accuracy-drift_accuracy),"explainability_bp":_bp(sum(1 for r in rows if r.explained),len(rows)),"p95_latency_ms":_ceil_percentile([r.latency_ms for r in completed],95)}
    reasons=[]
    if metrics["accuracy_bp"]<policy_obj["min_accuracy_bp"]: reasons.append("ACCURACY_BELOW_MINIMUM")
    if metrics["reliability_bp"]<policy_obj["min_reliability_bp"]: reasons.append("RELIABILITY_BELOW_MINIMUM")
    if metrics["robustness_bp"]<policy_obj["min_robustness_bp"]: reasons.append("ROBUSTNESS_BELOW_MINIMUM")
    if metrics["drift_drop_bp"]>policy_obj["max_drift_drop_bp"]: reasons.append("DRIFT_DROP_EXCEEDS_MAXIMUM")
    if metrics["explainability_bp"]<policy_obj["min_explainability_bp"]: reasons.append("EXPLAINABILITY_BELOW_MINIMUM")
    if metrics["p95_latency_ms"]>policy_obj["max_p95_latency_ms"]: reasons.append("P95_LATENCY_EXCEEDS_MAXIMUM")
    core={"schema":REPORT_SCHEMA,"suite_id":source_obj["suite_id"],"policy_id":policy_obj["policy_id"],"adapter_id":adapter_obj["adapter_id"],"scenario_set_sha256":sha256_hex(canonical_bytes(source_obj)),"policy_sha256":sha256_hex(canonical_bytes(policy_obj)),"adapter_sha256":sha256_hex(canonical_bytes(adapter_obj)),"metrics":metrics,"state":"PROOF_PASS" if not reasons else "HOLD","reason_codes":[r for r in REASON_ORDER if r in reasons],"authority":"OFFLINE_SYNTHETIC_OR_RESEARCH_EVALUATION_ONLY"}
    return {**core,"report_sha256":sha256_hex(canonical_bytes(core))}

def verify_report(scenario_set,policy,adapter,report,*,trusted_now=None):
    if report!=evaluate(scenario_set,policy,adapter,trusted_now=trusted_now): raise ContractError("report does not exactly match recomputation")
    return True

def load_json_file(path,*,max_bytes=2000000):
    p=Path(path); st=p.lstat()
    if stat.S_ISLNK(st.st_mode) or not stat.S_ISREG(st.st_mode): raise ContractError("input must be ordinary regular file")
    if st.st_size>max_bytes: raise ContractError("input file too large")
    return loads_strict(p.read_text(encoding="utf-8"))

def publish_json_exclusive(path,value):
    p=Path(path); data=canonical_bytes(value)+b"\n"; flags=os.O_WRONLY|os.O_CREAT|os.O_EXCL
    if hasattr(os,"O_NOFOLLOW"): flags|=os.O_NOFOLLOW
    fd=os.open(p,flags,0o600)
    try: os.write(fd,data); os.fsync(fd)
    finally: os.close(fd)
