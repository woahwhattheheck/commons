# SPDX-License-Identifier: Apache-2.0
"""Exact-input current-ABI carrier for the H3/S420 SELL micro-stack.

This does not install a second seller or controller. It materializes two
source edits against the canonical current SELL implementation.
"""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

SCHEDULER_GIT_BLOB = "a483b24dd72b580d7d8811636b54d2d44f391575"
FROZEN_GIT_BLOB = "fc7baf5c179818a55037f6a61d92984d81d1a21c"
SCHEDULER_OLD = "HORIZON = 8\n"
SCHEDULER_NEW = "HORIZON = 3\n"
FROZEN_ANCHOR = """            info['baseline_horizon_end']=horizon['baseline_end'];info['horizon_end']=item_end
            self.diagnostics['evaluations'].append(info)
            eligible,rank=seller_choice_rank(info)
            if eligible:
                options.append((item,plan,info,reference))
                if best is None or rank>seller_choice_rank(best[2])[1]:best=(item,plan,info)
"""
FROZEN_REPLACEMENT = """            info['baseline_horizon_end']=horizon['baseline_end'];info['horizon_end']=item_end
            if _h3s420_suppress(now,plan,reference,info):
                info=dict(info)
                plan=tuple(reference)
                info['plan']=list(reference)
                info['accepted']=False
                info['acceptance_score']=0.0
                info['acceptance_rule']='h3s420_no_late_pull_forward'
                info['h3s420_suppressed']=True
            self.diagnostics['evaluations'].append(info)
            eligible,rank=seller_choice_rank(info)
            if eligible:
                options.append((item,plan,info,reference))
                if best is None or rank>seller_choice_rank(best[2])[1]:best=(item,plan,info)
"""
CLASS_ANCHOR = "\n\nclass FrozenSelected(SellScheduler):\n"
GUARD_SOURCE = '''\n\ndef _h3s420_suppress(now,plan,reference,info):
    """Suppress only non-forced late current-step SELL pull-forward."""
    return (int(now)>=420
            and not bool(info.get('forced_feasibility',False))
            and int(dict(plan).get(int(now),0))
                > int(dict(reference).get(int(now),0)))
'''

def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def should_suppress_late_pull_forward(now, plan, reference, info):
    return (int(now) >= 420
            and not bool(info.get("forced_feasibility", False))
            and int(dict(plan).get(int(now), 0)) > int(dict(reference).get(int(now), 0)))

def transform_scheduler(text: str) -> str:
    if text.count(SCHEDULER_OLD) != 1:
        raise ValueError("scheduler HORIZON anchor must occur exactly once")
    return text.replace(SCHEDULER_OLD, SCHEDULER_NEW, 1)

def transform_frozen(text: str) -> str:
    if text.count(FROZEN_ANCHOR) != 1:
        raise ValueError("frozen SELL choice anchor must occur exactly once")
    if text.count(CLASS_ANCHOR) != 1:
        raise ValueError("FrozenSelected class anchor must occur exactly once")
    out = text.replace(CLASS_ANCHOR, GUARD_SOURCE + CLASS_ANCHOR, 1)
    return out.replace(FROZEN_ANCHOR, FROZEN_REPLACEMENT, 1)

def compose_paths(scheduler: Path, frozen: Path, output_dir: Path, receipt: Path | None = None):
    s_raw, f_raw = scheduler.read_bytes(), frozen.read_bytes()
    s_blob, f_blob = git_blob_sha(s_raw), git_blob_sha(f_raw)
    if s_blob != SCHEDULER_GIT_BLOB:
        raise ValueError(f"scheduler Git blob mismatch: {s_blob}")
    if f_blob != FROZEN_GIT_BLOB:
        raise ValueError(f"frozen_selected Git blob mismatch: {f_blob}")
    s_out = transform_scheduler(s_raw.decode()).encode()
    f_out = transform_frozen(f_raw.decode()).encode()
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir/"scheduler.py").write_bytes(s_out)
    (output_dir/"frozen_selected.py").write_bytes(f_out)
    report = {
      "schema":"titan-v4-h3s420-current-abi/v1",
      "production_activation":False,
      "inputs":{"scheduler":{"git_blob":s_blob,"sha256":sha256(s_raw)},"frozen_selected":{"git_blob":f_blob,"sha256":sha256(f_raw)}},
      "outputs":{"scheduler":{"git_blob":git_blob_sha(s_out),"sha256":sha256(s_out)},"frozen_selected":{"git_blob":git_blob_sha(f_out),"sha256":sha256(f_out)}},
      "semantics":{"baseline_sale_horizon":3,"preserve_event_aware_extensions":True,"no_late_pull_forward_step":420,"forced_feasibility_preserved":True,"scope":"current-step SELL quantity only"},
      "evidence":{"historical_microstack_mean_margin_delta":441,"historical_microstack_positive_cells":"16/16","current_abi_economics":"NOT_ASSESSED"}}
    if receipt: receipt.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    return report

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("scheduler",type=Path); p.add_argument("frozen_selected",type=Path); p.add_argument("output_dir",type=Path); p.add_argument("--receipt",type=Path)
    a=p.parse_args(); print(json.dumps(compose_paths(a.scheduler,a.frozen_selected,a.output_dir,a.receipt),indent=2,sort_keys=True))
if __name__ == "__main__": main()
