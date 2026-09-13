#!/usr/bin/env python3
"""Rank reproducible candidate disparity patterns outside the fixed bias scorecard."""
from __future__ import annotations
import argparse,csv,json,math
from pathlib import Path
from statistics import fmean
from typing import Optional
DEFAULT_EXCLUDED_PREFIXES=("svi_","cvi_","ruca_","rucc_","nchs_","tribal_","usdm_","usfs_","mtbs_","heat_","wildfire_","drought_")
def numeric(value: str)->Optional[float]:
    if value is None or value.strip()=="": return None
    try: number=float(value)
    except ValueError: return None
    return number if math.isfinite(number) else None
def load_scores(path: Path)->dict[str,float]:
    out={}
    with path.open(newline="",encoding="utf-8") as h:
        for row in csv.DictReader(h):
            geoid=row.get("GEOID","").strip(); score=numeric(row.get("coverage_gap_score",""))
            if len(geoid)==11 and geoid.isdigit() and score is not None: out[geoid]=score
    if not out: raise ValueError("no usable scores")
    return out
def quantile_cut(values:list[float],fraction:float)->float:
    ordered=sorted(values)
    if len(ordered)<4: raise ValueError("at least four numeric rows required")
    return ordered[int(round((len(ordered)-1)*fraction))]
def analyze(scores:dict[str,float],strata_path:Path,min_rows:int,prefixes:tuple[str,...]):
    with strata_path.open(newline="",encoding="utf-8") as h: rows=list(csv.DictReader(h))
    if not rows: raise ValueError("empty strata CSV")
    fields=[f for f in rows[0].keys() if f and f!="GEOID"]; results=[]
    for field in fields:
        if field.startswith(prefixes): continue
        paired=[]
        for row in rows:
            geoid=(row.get("GEOID") or "").strip()
            if geoid not in scores: continue
            value=numeric(row.get(field,""))
            if value is not None: paired.append((value,scores[geoid],geoid))
        if len(paired)<min_rows or len({x[0] for x in paired})<4: continue
        q1=quantile_cut([x[0] for x in paired],.25); q3=quantile_cut([x[0] for x in paired],.75)
        low=[x for x in paired if x[0]<=q1]; high=[x for x in paired if x[0]>=q3]
        if not low or not high: continue
        low_gap=fmean(x[1] for x in low); high_gap=fmean(x[1] for x in high); delta=high_gap-low_gap
        results.append({"field":field,"rows":len(paired),"q1":q1,"q3":q3,"low_mean_gap":low_gap,"high_mean_gap":high_gap,"absolute_delta":abs(delta),"signed_delta":delta,"high_examples":[x[2] for x in sorted(high,key=lambda x:x[1],reverse=True)[:5]],"low_examples":[x[2] for x in sorted(low,key=lambda x:x[1])[:5]]})
    return sorted(results,key=lambda x:x["absolute_delta"],reverse=True)
def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__); p.add_argument("components_csv",type=Path); p.add_argument("strata_csv",type=Path); p.add_argument("output_json",type=Path); p.add_argument("--min-rows",type=int,default=100); p.add_argument("--include-fixed-scorecard-families",action="store_true"); a=p.parse_args(argv)
    prefixes=() if a.include_fixed_scorecard_families else DEFAULT_EXCLUDED_PREFIXES; results=analyze(load_scores(a.components_csv),a.strata_csv,a.min_rows,prefixes); a.output_json.parent.mkdir(parents=True,exist_ok=True); a.output_json.write_text(json.dumps(results,indent=2,sort_keys=True)+"\n",encoding="utf-8"); return 0
if __name__=="__main__": raise SystemExit(main())
