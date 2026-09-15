"""Canonical receipt, verification, and matched-comparison rules."""
from __future__ import annotations
import importlib.metadata, math, os, platform
from typing import Any
from evidence_contract import (AUTHORITY,EVIDENCE_CLASS,EXPECTED_CANDIDATES,SCHEMA,
    EvidenceError,canonical_sha256,candidate_spec)

def _ver(name:str):
    try:return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:return None
def runner_fingerprint()->dict[str,Any]:
    return {"python":platform.python_version(),"platform":platform.platform(),"machine":platform.machine(),
      "githubRunId":os.environ.get("GITHUB_RUN_ID"),"githubRunAttempt":os.environ.get("GITHUB_RUN_ATTEMPT"),
      "githubJob":os.environ.get("GITHUB_JOB"),"runnerOs":os.environ.get("RUNNER_OS"),"runnerArch":os.environ.get("RUNNER_ARCH")}
def environment_record()->dict[str,Any]:
    return {"runner":runner_fingerprint(),"packages":{n:_ver(n) for n in ("dfbench","jax","learn2design","optax")}}
def sign(p:dict[str,Any])->dict[str,Any]:
    u=dict(p);u.pop("receiptSha256",None);return {**u,"receiptSha256":canonical_sha256(u)}
def base_receipt(m,label,status,source_ok,organizer_ok,measurement,pending,env=None):
    s=candidate_spec(m,label)
    return sign({"schemaVersion":SCHEMA,"evidenceClass":EVIDENCE_CLASS,"status":status,
      "candidate":{"label":label,**s},"organizer":dict(m["organizer"]),"cell":dict(m["cell"]),
      "sourceVerified":source_ok,"organizerSourceVerified":organizer_ok,
      "environment":environment_record() if env is None else env,"measurement":measurement,
      "pendingReason":pending,"authority":dict(AUTHORITY)})
def verify_receipt(r:dict[str,Any],m:dict[str,Any])->None:
    d=r.get("receiptSha256");u=dict(r);u.pop("receiptSha256",None)
    if not isinstance(d,str) or d!=canonical_sha256(u):raise EvidenceError("receipt digest mismatch")
    if r.get("schemaVersion")!=SCHEMA or r.get("evidenceClass")!=EVIDENCE_CLASS:raise EvidenceError("receipt class mismatch")
    if r.get("authority")!=AUTHORITY:raise EvidenceError("authority ceiling changed")
    label=r.get("candidate",{}).get("label")
    if label not in EXPECTED_CANDIDATES or r.get("candidate")!={"label":label,**EXPECTED_CANDIDATES[label]}:raise EvidenceError("candidate identity drift")
    if r.get("organizer")!=m["organizer"] or r.get("cell")!=m["cell"]:raise EvidenceError("organizer/cell mismatch")
    if r.get("status")=="MEASURED":
        if r.get("sourceVerified") is not True or r.get("organizerSourceVerified") is not True:raise EvidenceError("measured source verification missing")
        x=r.get("measurement");loss=x.get("bestLoss") if isinstance(x,dict) else None;count=x.get("evalCount") if isinstance(x,dict) else None
        if isinstance(loss,bool) or not isinstance(loss,(int,float)) or not math.isfinite(float(loss)):raise EvidenceError("bestLoss must be finite")
        if isinstance(count,bool) or not isinstance(count,int) or count<=0:raise EvidenceError("evalCount must be positive int")
    elif r.get("status")=="MEASUREMENT_PENDING":
        if r.get("measurement") is not None or not r.get("pendingReason"):raise EvidenceError("pending receipt malformed")
    else:raise EvidenceError("unsupported receipt status")
def make_measured_for_test(m,label,best_loss,eval_count,runner):
    env=environment_record();env["runner"]=runner
    return base_receipt(m,label,"MEASURED",True,True,{"bestLoss":float(best_loss),"evalCount":int(eval_count),"budgetExceeded":True,"elapsedSeconds":30.0},None,env)
def compare_receipts(a,b,m):
    verify_receipt(a,m);verify_receipt(b,m);d={a["candidate"]["label"]:a,b["candidate"]["label"]:b}
    if set(d)!=set(EXPECTED_CANDIDATES):raise EvidenceError("comparison requires serial_v1 and vectorized_v2")
    s,v=d["serial_v1"],d["vectorized_v2"]
    if s["status"]!="MEASURED" or v["status"]!="MEASURED":raise EvidenceError("comparison requires measured receipts")
    if s["environment"]["runner"]!=v["environment"]["runner"]:raise EvidenceError("runner fingerprints differ")
    sm,vm=s["measurement"],v["measurement"]
    w="serial_v1" if sm["bestLoss"]<vm["bestLoss"] else "vectorized_v2" if vm["bestLoss"]<sm["bestLoss"] else "tie"
    return sign({"schemaVersion":SCHEMA,"evidenceClass":EVIDENCE_CLASS,"status":"MATCHED_PUBLIC_DEVELOPMENT_COMPARISON",
      "organizer":dict(m["organizer"]),"cell":dict(m["cell"]),"runner":s["environment"]["runner"],
      "candidates":{"serial_v1":s["receiptSha256"],"vectorized_v2":v["receiptSha256"]},
      "result":{"lowerBestLoss":w,"serialBestLoss":sm["bestLoss"],"vectorizedBestLoss":vm["bestLoss"],
        "bestLossDeltaVectorMinusSerial":vm["bestLoss"]-sm["bestLoss"],"serialEvalCount":sm["evalCount"],
        "vectorizedEvalCount":vm["evalCount"],"evalCountDeltaVectorMinusSerial":vm["evalCount"]-sm["evalCount"]},
      "interpretation":"Public ConstrainedVoyager development evidence only; not hidden-topology/H100/official competition performance.",
      "authority":dict(AUTHORITY)})
