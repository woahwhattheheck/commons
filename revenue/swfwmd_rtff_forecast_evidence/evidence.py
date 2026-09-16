from __future__ import annotations
import hashlib, json
from datetime import datetime, timezone
from typing import Any, Iterable

SOURCES = {"district_gage", "usgs_gage", "noaa_rainfall", "noaa_coastal", "operator", "model"}
MODELS = {"StormWise", "SWMM", "HEC-RAS"}

def stable_json(v: Any) -> str:
    return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)

def sha(v: Any) -> str:
    return hashlib.sha256((v if isinstance(v, str) else stable_json(v)).encode()).hexdigest()

def text(v: Any, name: str, max_len: int = 256) -> str:
    if not isinstance(v, str) or not v.strip() or len(v.strip()) > max_len: raise ValueError(f"{name} invalid")
    return v.strip()

def instant(v: Any, name: str) -> str:
    s=text(v,name,64)
    try: d=datetime.fromisoformat(s.replace("Z","+00:00"))
    except ValueError as e: raise ValueError(f"{name} must be ISO-8601") from e
    if d.tzinfo is None: raise ValueError(f"{name} needs timezone")
    return d.astimezone(timezone.utc).isoformat().replace("+00:00","Z")

def normalize_input(raw: dict[str, Any]) -> dict[str, Any]:
    source=text(raw.get("source"),"source",32)
    if source not in SOURCES: raise ValueError("unsupported source")
    observed=instant(raw.get("observed_at"),"observed_at")
    fetched=instant(raw.get("fetched_at"),"fetched_at")
    if datetime.fromisoformat(fetched.replace("Z","+00:00")) < datetime.fromisoformat(observed.replace("Z","+00:00")): raise ValueError("fetched_at precedes observed_at")
    payload_hash=text(raw.get("payload_hash"),"payload_hash",64).lower()
    if len(payload_hash)!=64 or any(c not in "0123456789abcdef" for c in payload_hash): raise ValueError("payload_hash must be sha256 hex")
    out={"source":source,"source_id":text(raw.get("source_id"),"source_id",160),"observed_at":observed,"fetched_at":fetched,"payload_hash":payload_hash}
    out["input_id"]=sha(out); return out

def assess_freshness(inputs: Iterable[dict[str, Any]], *, as_of: str, max_age_minutes: dict[str,int]) -> dict[str,Any]:
    now=datetime.fromisoformat(instant(as_of,"as_of").replace("Z","+00:00")); rows=[normalize_input(x) for x in inputs]
    stale=[]
    for r in rows:
        age=(now-datetime.fromisoformat(r["observed_at"].replace("Z","+00:00"))).total_seconds()/60
        limit=max_age_minutes.get(r["source"])
        if limit is None or age < 0 or age > limit: stale.append({"input_id":r["input_id"],"source":r["source"],"age_minutes":age,"limit_minutes":limit})
    result={"inputs":rows,"stale":stale,"status":"pass" if not stale else "review_required"}; result["evidence_hash"]=sha(result); return result

def build_scenario(raw: dict[str,Any]) -> dict[str,Any]:
    kind=text(raw.get("kind"),"kind",40)
    if kind not in {"baseline","rainfall_override","structure_operation","temporary_pump"}: raise ValueError("unsupported scenario")
    params=raw.get("parameters",{})
    if not isinstance(params,dict): raise ValueError("parameters must be object")
    json.loads(stable_json(params))
    out={"scenario_id":text(raw.get("scenario_id"),"scenario_id",120),"kind":kind,"parameters":params,"created_at":instant(raw.get("created_at"),"created_at"),"authority":"analytical_scenario_only"}
    out["scenario_hash"]=sha(out); return out

def build_run_manifest(*, run_id:str, model_name:str, model_hash:str, horizon_hours:int, interval_minutes:int, inputs:list[dict[str,Any]], scenario:dict[str,Any], output_hash:str, started_at:str, completed_at:str) -> dict[str,Any]:
    if model_name not in MODELS: raise ValueError("unsupported model family")
    if horizon_hours < 72: raise ValueError("horizon must cover at least 72 hours")
    if interval_minutes < 1 or interval_minutes > 60: raise ValueError("interval must be 1..60 minutes")
    for h in (model_hash,output_hash):
        if len(h)!=64 or any(c not in "0123456789abcdef" for c in h.lower()): raise ValueError("hash must be sha256 hex")
    start=instant(started_at,"started_at"); end=instant(completed_at,"completed_at")
    if end < start: raise ValueError("completion before start")
    normalized_inputs=sorted((normalize_input(x) for x in inputs),key=lambda x:x["input_id"])
    scen=build_scenario(scenario)
    manifest={"run_id":text(run_id,"run_id",160),"model_name":model_name,"model_hash":model_hash.lower(),"horizon_hours":horizon_hours,"interval_minutes":interval_minutes,"inputs":[x["input_id"] for x in normalized_inputs],"scenario_hash":scen["scenario_hash"],"output_hash":output_hash.lower(),"started_at":start,"completed_at":end,"authority":"forecast_evidence_only"}
    manifest["manifest_hash"]=sha(manifest); return manifest

def compare_replay(a:dict[str,Any], b:dict[str,Any]) -> dict[str,Any]:
    comparable=("model_name","model_hash","horizon_hours","interval_minutes","inputs","scenario_hash")
    same_inputs=all(a.get(k)==b.get(k) for k in comparable)
    same_output=a.get("output_hash")==b.get("output_hash")
    result={"same_inputs":same_inputs,"same_output":same_output,"status":"pass" if same_inputs and same_output else "review_required","forecast_accuracy_claim":False,"safety_decision_authority":False}
    result["evidence_hash"]=sha(result); return result

def acceptance_gate(freshness:dict[str,Any], replay:dict[str,Any]) -> dict[str,Any]:
    gate={"freshness_hash":text(freshness.get("evidence_hash"),"freshness_hash",64),"replay_hash":text(replay.get("evidence_hash"),"replay_hash",64),"ready_for_owner_review":freshness.get("status")=="pass" and replay.get("status")=="pass","release_authority":"owner_review_required","forecast_accuracy_authority":False,"emergency_action_authority":False,"production_release_authority":False}
    gate["gate_hash"]=sha(gate); return gate
