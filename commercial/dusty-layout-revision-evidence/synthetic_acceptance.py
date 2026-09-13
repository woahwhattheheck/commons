#!/usr/bin/env python3
"""Generate the frozen 120-job / 24-fault Dusty acceptance corpus."""
from __future__ import annotations
import argparse, json
from pathlib import Path

FAULT_CLASSES = (
    "design_source",
    "trade_signoffs",
    "unit_scale_metadata",
    "control_point_survey",
    "station_verification",
    "portal_preview_qr",
    "printer_app_version",
    "final_job_report",
)


def clean_job(i: int) -> dict:
    n=i+1; rev=f"R{(n%7)+1:02d}"; survey=f"CP-{(n%5)+1:02d}"; digest=f"{n:064x}"[-64:]
    preview=hashlib_hex(f"preview-{n}")
    return {
      "record_id": f"SYN-{n:03d}", "job_id": f"LAYOUT-{n:03d}",
      "design": {"file_sha256": digest, "revision": rev, "released_revision": rev},
      "trade_signoffs": [
        {"trade":"ARCH","signer":"Synthetic Architect","status":"SIGNED","revision":rev},
        {"trade":"MEP","signer":"Synthetic MEP","status":"SIGNED","revision":rev}],
      "unit_scale": {"model_unit":"mm","field_unit":"mm","scale":1.0,"verified":True},
      "control_point_survey": {"version":survey,"released_version":survey,"sha256":hashlib_hex(f"survey-{n}")},
      "station_verification": {"verification_id":f"SV-{n:03d}","result":"PASS","survey_version":survey},
      "portal_preview": {"preview_sha256":preview,"qr_sha256":preview,"design_revision":rev},
      "printer_app": {"printer_version":"FP2-2.6.0","app_version":"IPAD-5.18.0","capture_state":"RECORDED"},
      "final_job_report": {"status":"COMPLETE","job_id":f"LAYOUT-{n:03d}","design_sha256":digest,"design_revision":rev,"station_verification_id":f"SV-{n:03d}","portal_preview_sha256":preview}
    }


def hashlib_hex(s: str) -> str:
    import hashlib
    return hashlib.sha256(s.encode()).hexdigest()


def apply_fault(job: dict, cls: str) -> None:
    if cls=="design_source": job["design"]["released_revision"]="OLD"
    elif cls=="trade_signoffs": job["trade_signoffs"][0]["revision"]="STALE"
    elif cls=="unit_scale_metadata": job["unit_scale"]["verified"]=False
    elif cls=="control_point_survey": job["control_point_survey"]["released_version"]="CP-OLD"
    elif cls=="station_verification": job["station_verification"]["result"]="FAIL"
    elif cls=="portal_preview_qr": job["portal_preview"]["qr_sha256"]=hashlib_hex("mismatch")
    elif cls=="printer_app_version": job["printer_app"]["capture_state"]="MISSING"
    elif cls=="final_job_report": job["final_job_report"]["design_revision"]="OLD"
    else: raise ValueError(cls)


def build_corpus():
    jobs=[clean_job(i) for i in range(120)]
    plan={}; cursor=96
    for cls in FAULT_CLASSES:
        plan[cls]=[]
        for _ in range(3):
            job=jobs[cursor]; apply_fault(job,cls); plan[cls].append(job["record_id"]); cursor+=1
    return jobs, plan


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("output",type=Path,nargs="?",default=Path("synthetic-120.json")); args=ap.parse_args()
    jobs,plan=build_corpus(); args.output.write_text(json.dumps(jobs,sort_keys=True,indent=2)+"\n",encoding="ascii")
    print(json.dumps({"jobs":len(jobs),"fault_plan":plan},sort_keys=True)); return 0

if __name__=="__main__": raise SystemExit(main())
