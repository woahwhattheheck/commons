from __future__ import annotations
import argparse,json
from pathlib import Path
from .core import ReferenceProfile
from .lerobot_v21 import fit_dataset_reference,scan_dataset

def main(argv=None)->int:
    p=argparse.ArgumentParser(description="LeRobot v2.1 trajectory quality detector for the Wuhu embodied-data challenge"); sub=p.add_subparsers(dest="cmd",required=True)
    prof=sub.add_parser("profile"); prof.add_argument("dataset",type=Path); prof.add_argument("--out",type=Path,default=Path("reference.json")); prof.add_argument("--episodes",type=int,nargs="*")
    scan=sub.add_parser("scan"); scan.add_argument("dataset",type=Path); scan.add_argument("--out",type=Path,default=Path("wuhu-qc-report")); scan.add_argument("--episodes",type=int,nargs="*"); scan.add_argument("--reference",type=Path)
    a=p.parse_args(argv)
    if a.cmd=="profile":
        ref=fit_dataset_reference(a.dataset,episodes=a.episodes); a.out.write_text(json.dumps(ref.as_dict(),indent=2)+"\n",encoding="utf-8"); print(f"reference_features={len(ref.features)} output={a.out}"); return 0
    ref=None
    if a.reference: ref=ReferenceProfile.from_dict(json.loads(a.reference.read_text(encoding="utf-8")))
    reports=scan_dataset(a.dataset,a.out,episodes=a.episodes,reference=ref); holds=sum(r.quality_score<70 for r in reports); print(f"episodes={len(reports)} quality_lt_70={holds} report={a.out}"); return 0
if __name__=="__main__": raise SystemExit(main())
