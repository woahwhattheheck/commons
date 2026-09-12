# SPDX-License-Identifier: Apache-2.0
"""Exact submitted-V4 E08 event-horizon behavioral ablation.

This is evidence tooling, not a runtime policy.  It authenticates the exact
submitted-V4 ``frozen_selected.py`` Git blob and rewrites only the E08 horizon /
date-selection behavior back to the submitted-V3.1 fixed-window semantics.
Later V4 seller mechanics (funding policy, joint SELL composition, acceptance
rules, materialization, etc.) are deliberately left in place.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Iterable

SOURCE_PATH = "revenue/kaggriculture/cloud-execution-lab/frozen_selected.py"
V31_SOURCE_COMMIT = "a90d888f03987ef0b35cfd20ec3519c6144db08a"
V4_SOURCE_COMMIT = "4af1113154e78c662780e6658cd920daac7902e3"
V31_FROZEN_GIT_BLOB = "1f18a35c2993aa971fc80183ee42fb7026a01428"
V4_FROZEN_GIT_BLOB = "fc7baf5c179818a55037f6a61d92984d81d1a21c"
SCHEMA = "titan-v5-v31-e08-event-horizon-ablation-v1"
HORIZON = 8


class SourceAuthorityError(ValueError):
    """The caller did not supply the exact submitted-V4 seller source."""


def git_blob_sha1(raw: bytes) -> str:
    header = f"blob {len(raw)}\0".encode("ascii")
    return hashlib.sha1(header + raw).hexdigest()


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


_E08_HORIZON_BLOCK = """        route=self.controller.R[self.controller.cur]\n        shops=obs.get('town',{}).get('unlocked_shops',[])\n        end,horizon=event_aware_horizon(now,last,route,targets,shops,config)\n        unit_event=(represented_shed_event(\n            now,horizon['baseline_end'],horizon['hard_end'],route,farm,private,config,\n            base.get('market',[]))\n                    if targets else None)\n        if unit_event is not None:\n            end=max(end,unit_event)\n        horizon['unit_event']=unit_event\n        horizon['extended']=end>horizon['baseline_end']\n        self.diagnostics['horizon']=horizon\n"""

_V31_FIXED_HORIZON_BLOCK = """        route=self.controller.R[self.controller.cur]\n        shops=obs.get('town',{}).get('unlocked_shops',[])\n        end=min(now+HORIZON,last,(now//24+1)*24-1)\n        # Future controller branch changes are not predicted.\n        for checkpoint,*_ in parent.DECISIONS:\n            if now<checkpoint<=end:end=checkpoint-1\n        dates=[now]+[t for t in range(now+1,end+1) if any(absorption(p,t-1,shops,config) for p in PRODUCTS)]\n        if len(dates)>3:dates=dates[:2]+dates[-1:]\n        if dates[-1]!=end:dates.append(end)\n        dates=sorted(set(dates))\n        horizon={'baseline_end':end,'hard_end':end,'service_dates':{},\n                 'unit_event':None,'extended':False,'ablation':'submitted-v31-fixed'}\n        self.diagnostics['horizon']=horizon\n"""

_E08_ITEM_WINDOW_BLOCK = """            item_end=max(horizon['baseline_end'],\n                         horizon['service_dates'].get(item,horizon['baseline_end']),\n                         horizon['unit_event'] or horizon['baseline_end'])\n            dates=product_event_dates(item,now,item_end,shops,config)\n"""

_FIXED_ITEM_WINDOW_BLOCK = """            item_end=end\n"""


def _replace_exact_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SourceAuthorityError(f"{label}: expected exactly one source match, found {count}")
    return text.replace(old, new, 1)


def rewrite_e08_text(text: str) -> str:
    """Reverse only E08 transform wiring; leave all later V4 helpers/mechanics intact."""
    text = _replace_exact_once(
        text, _E08_HORIZON_BLOCK, _V31_FIXED_HORIZON_BLOCK, "E08 horizon block"
    )
    text = _replace_exact_once(
        text, _E08_ITEM_WINDOW_BLOCK, _FIXED_ITEM_WINDOW_BLOCK, "E08 per-item window block"
    )
    return text


def ablate_submitted_v4(raw: bytes) -> tuple[bytes, dict[str, object]]:
    """Authenticate exact submitted V4 source and return deterministic treatment bytes."""
    observed_blob = git_blob_sha1(raw)
    if observed_blob != V4_FROZEN_GIT_BLOB:
        raise SourceAuthorityError(
            f"submitted V4 source blob mismatch: {observed_blob} != {V4_FROZEN_GIT_BLOB}"
        )
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SourceAuthorityError("submitted V4 source is not UTF-8") from exc
    if "\r\n" in text:
        raise SourceAuthorityError("submitted V4 source unexpectedly contains CRLF bytes")

    patched = rewrite_e08_text(text)
    out = patched.encode("utf-8")
    compile(out, f"{SOURCE_PATH}:e08-ablated", "exec")
    if out == raw:
        raise AssertionError("E08 ablation produced no source change")

    receipt: dict[str, object] = {
        "schema": SCHEMA,
        "source_path": SOURCE_PATH,
        "control_source_commit": V4_SOURCE_COMMIT,
        "control_source_git_blob": V4_FROZEN_GIT_BLOB,
        "control_source_sha256": sha256(raw),
        "treatment_source_git_blob": git_blob_sha1(out),
        "treatment_source_sha256": sha256(out),
        "reference_v31_source_commit": V31_SOURCE_COMMIT,
        "reference_v31_source_git_blob": V31_FROZEN_GIT_BLOB,
        "behavioral_change": "revert E08 horizon/date selection only",
        "preserved_v4_mechanics": [
            "funded_minimum_now",
            "fund_same_turn_acquisition",
            "joint_plan_metrics",
            "seller_choice_rank",
            "materialize_sales",
        ],
    }
    return out, receipt


def legacy_horizon_and_dates(
    *,
    now: int,
    last: int,
    decisions: Iterable[int],
    absorption_dates: Iterable[int],
) -> tuple[int, tuple[int, ...]]:
    """Pure model of submitted-V3.1's fixed horizon/date construction for tests."""
    end = min(now + HORIZON, last, (now // 24 + 1) * 24 - 1)
    for checkpoint in decisions:
        if now < checkpoint <= end:
            end = checkpoint - 1
    dates = [now] + [t for t in range(now + 1, end + 1) if t in set(absorption_dates)]
    if len(dates) > 3:
        dates = dates[:2] + dates[-1:]
    if dates[-1] != end:
        dates.append(end)
    return end, tuple(sorted(set(dates)))


def _main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="exact submitted-V4 frozen_selected.py")
    parser.add_argument("output", type=Path, help="write E08-ablated seller source here")
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()

    raw = args.input.read_bytes()
    out, receipt = ablate_submitted_v4(raw)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(out)
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
