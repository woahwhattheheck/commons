# SPDX-License-Identifier: Apache-2.0
"""Exact-source transform from canonical scalar SELL choice to safe portfolio choice."""
from __future__ import annotations

import hashlib
from pathlib import Path

EXPECTED_SCHEDULER_GIT_BLOB = "a483b24dd72b580d7d8811636b54d2d44f391575"
PATCH_SCHEMA_VERSION = 1

IMPORT_ANCHOR = "import mechanics as m\nfrom observed_clone import detached_json_value\n"
IMPORT_REPLACEMENT = (
    "import mechanics as m\n"
    "from observed_clone import detached_json_value\n"
    "from multi_lot_portfolio import PortfolioError, select_portfolio\n"
)

BEST_ANCHOR = "        best=None\n        for item,quantity in targets.items():\n"
BEST_REPLACEMENT = "        best=None\n        admitted=[]\n        for item,quantity in targets.items():\n"

ELIGIBLE_ANCHOR = (
    "            eligible=info['worst_relative_gain']>0 or info.get('forced_feasibility',False)\n"
    "            rank=(info.get('forced_feasibility',False),info['worst_relative_gain'])\n"
    "            if eligible and (best is None or rank>(best[2].get('forced_feasibility',False),best[2]['worst_relative_gain'])):best=(item,plan,info)\n"
)
ELIGIBLE_REPLACEMENT = (
    "            eligible=info['worst_relative_gain']>0 or info.get('forced_feasibility',False)\n"
    "            rank=(info.get('forced_feasibility',False),info['worst_relative_gain'])\n"
    "            if eligible:\n"
    "                admitted.append({'item':item,'plan':plan,'info':info,'rank':rank})\n"
    "                if best is None or rank>(best[2].get('forced_feasibility',False),best[2]['worst_relative_gain']):best=(item,plan,info)\n"
)

APPLY_ANCHOR = (
    "        if best:\n"
    "            item,plan,info=best;current[item]=dict(plan).get(now,0)\n"
    "            self.planned[item]=[(t,q) for t,q in plan if t>now and q>0]\n"
    "            self.diagnostics['chosen']=info\n"
)
APPLY_REPLACEMENT = (
    "        if best:\n"
    "            item,plan,info=best\n"
    "            selected=[{'item':item,'plan':plan,'info':info,'rank':(info.get('forced_feasibility',False),info['worst_relative_gain'])}]\n"
    "            portfolio={'schema_version':1,'fallback':'naive-mode' if self.mode=='naive' else None,'selected_items':[item]}\n"
    "            if self.mode!='naive':\n"
    "                try:\n"
    "                    decision=select_portfolio(candidates=admitted,anchor_item=item,current=current,market=base['market'],now=now,max_orders=int(config.get('maxMarketOrdersPerTurn',10)))\n"
    "                    selected=list(decision.selected);portfolio=decision.diagnostics();portfolio['fallback']=None\n"
    "                except (PortfolioError,TypeError,ValueError) as exc:\n"
    "                    portfolio={'schema_version':1,'fallback':type(exc).__name__,'selected_items':[item]}\n"
    "            for choice in selected:\n"
    "                chosen_item=choice['item'];chosen_plan=choice['plan']\n"
    "                current[chosen_item]=dict(chosen_plan).get(now,0)\n"
    "                self.planned[chosen_item]=[(t,q) for t,q in chosen_plan if t>now and q>0]\n"
    "            self.diagnostics['chosen']=info\n"
    "            self.diagnostics['portfolio']=portfolio\n"
)


def git_blob_sha(data: bytes) -> str:
    header = b"blob " + str(len(data)).encode("ascii") + b"\0"
    return hashlib.sha1(header + data).hexdigest()


def _replace_once(source: str, anchor: str, replacement: str, *, name: str) -> str:
    count = source.count(anchor)
    if count != 1:
        raise RuntimeError(f"{name} seam count is {count}, expected exactly 1")
    return source.replace(anchor, replacement, 1)


def patch_scheduler_bytes(data: bytes) -> bytes:
    actual = git_blob_sha(data)
    if actual != EXPECTED_SCHEDULER_GIT_BLOB:
        raise RuntimeError(
            f"scheduler Git blob drift: expected {EXPECTED_SCHEDULER_GIT_BLOB}, got {actual}"
        )
    source = data.decode("utf-8")
    source = _replace_once(source, IMPORT_ANCHOR, IMPORT_REPLACEMENT, name="import")
    source = _replace_once(source, BEST_ANCHOR, BEST_REPLACEMENT, name="best-init")
    source = _replace_once(source, ELIGIBLE_ANCHOR, ELIGIBLE_REPLACEMENT, name="eligibility")
    source = _replace_once(source, APPLY_ANCHOR, APPLY_REPLACEMENT, name="application")
    marker = f"# TITAN multi-lot portfolio patch schema {PATCH_SCHEMA_VERSION}\n"
    return (marker + source).encode("utf-8")


def patch_scheduler_path(path: Path) -> bytes:
    return patch_scheduler_bytes(Path(path).read_bytes())
