from __future__ import annotations
import argparse, json
from pathlib import Path
from .engine import GateError, evaluate, loads_strict, verify_transition

def _write(path: Path, obj: dict) -> None:
    path.write_text(json.dumps(obj, sort_keys=True, separators=(",", ":")) + "\n", encoding="ascii")

def main() -> int:
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest="cmd", required=True)
    e=sub.add_parser("evaluate"); e.add_argument("policy",type=Path); e.add_argument("request",type=Path); e.add_argument("ledger",type=Path); e.add_argument("--receipt",type=Path,required=True); e.add_argument("--next-ledger",type=Path,required=True)
    v=sub.add_parser("verify"); v.add_argument("policy",type=Path); v.add_argument("request",type=Path); v.add_argument("prior_ledger",type=Path); v.add_argument("receipt",type=Path); v.add_argument("next_ledger",type=Path)
    a=ap.parse_args()
    try:
        policy=loads_strict(a.policy.read_bytes()); request=loads_strict(a.request.read_bytes())
        if a.cmd=="evaluate":
            ledger=loads_strict(a.ledger.read_bytes()); receipt,nxt=evaluate(policy,request,ledger); _write(a.receipt,receipt); _write(a.next_ledger,nxt); print(receipt["decision"],receipt["receipt_sha256"]); return 0 if receipt["decision"]=="EXECUTE_ALLOWED" else 2
        prior=loads_strict(a.prior_ledger.read_bytes()); receipt=loads_strict(a.receipt.read_bytes()); nxt=loads_strict(a.next_ledger.read_bytes())
        ok=verify_transition(policy,request,prior,receipt,nxt); print("PASS" if ok else "HOLD"); return 0 if ok else 2
    except (OSError,GateError,ValueError,TypeError) as exc:
        print(f"HOLD {exc}"); return 2
if __name__=="__main__": raise SystemExit(main())
