#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from datetime import datetime,timezone
from evaluator import ContractError,evaluate,load_json_file,publish_json_exclusive,verify_report

def _now(v):
    if v is None:return None
    try:return datetime.strptime(v,"%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc: raise SystemExit("--trusted-now must be YYYY-MM-DDTHH:MM:SSZ") from exc
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("mode",choices=("compile","verify")); ap.add_argument("--scenarios",required=True); ap.add_argument("--policy",required=True); ap.add_argument("--adapter",required=True); ap.add_argument("--report",required=True); ap.add_argument("--trusted-now"); a=ap.parse_args()
    try:
        s=load_json_file(a.scenarios); p=load_json_file(a.policy); ad=load_json_file(a.adapter); now=_now(a.trusted_now)
        if a.mode=="compile":
            r=evaluate(s,p,ad,trusted_now=now); publish_json_exclusive(a.report,r); print(json.dumps({"state":r["state"],"report_sha256":r["report_sha256"]},sort_keys=True))
        else:
            r=load_json_file(a.report); verify_report(s,p,ad,r,trusted_now=now); print(json.dumps({"verified":True,"report_sha256":r["report_sha256"]},sort_keys=True))
        return 0
    except ContractError as exc: print(f"HOLD: {exc}"); return 2
if __name__=="__main__": raise SystemExit(main())
