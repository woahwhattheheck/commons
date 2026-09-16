#!/usr/bin/env python3
from __future__ import annotations
import os, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
MODULES=("revenue.opportunity_identity_alias.test_resolution","revenue.opportunity_identity_alias.test_transition","revenue.opportunity_identity_alias.test_io","revenue.opportunity_identity_alias.test_recovery")
def run(optimized: bool)->int:
    argv=[sys.executable];
    if optimized: argv.append("-O")
    argv.extend(["-m","unittest","-v",*MODULES]); env=dict(os.environ); env["PYTHONDONTWRITEBYTECODE"]="1"; return subprocess.run(argv,cwd=ROOT,env=env).returncode
def main()->int:
    ordinary=run(False); optimized=run(True)
    if ordinary or optimized:
        print(f"opportunity identity hostiles failed: normal={ordinary} optimized={optimized}",file=sys.stderr); return 1
    print("opportunity identity hostiles passed: normal + python -O"); return 0
if __name__=="__main__": raise SystemExit(main())
