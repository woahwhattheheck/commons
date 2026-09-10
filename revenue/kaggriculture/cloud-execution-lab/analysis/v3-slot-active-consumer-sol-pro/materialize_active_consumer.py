#!/usr/bin/env python3
"""Materialize the shared SELL-slot reservation into TITAN's active frozen consumer."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import tempfile

OPERATION = "TITAN-V3-CROSS-PRODUCT-SLOT-ACTIVE-CONSUMER-CLOSURE-20260910-01"
EXPECTED_BLOBS = {
    "frozen_selected.py": "fc7baf5c179818a55037f6a61d92984d81d1a21c",
    "scheduler.py": "a483b24dd72b580d7d8811636b54d2d44f391575",
    "selected_sell_core.py": "f23d3a8b5ee5e82029026e7f8f44eb36c143a5a3",
    "titan_runtime.py": "b952c9c228ecbde592bf3d2df01638677abb0d24",
}

CLASS_ANCHOR = "\n\nclass FrozenSelected(SellScheduler):\n"
HELPERS = r'''


def _strict_slot_int(value):
    if isinstance(value,bool) or not isinstance(value,int) or value<0:return None
    return value


def _inherited_sell_quantity(orders,item):
    if not isinstance(orders,(list,tuple)):return None
    total=0
    for order in orders:
        if not order:continue
        if not isinstance(order,(list,tuple)) or not order:return None
        if order[0]!='SELL' or len(order)<2 or order[1]!=item:continue
        if len(order)<3:return None
        quantity=_strict_slot_int(order[2])
        if quantity is None:return None
        total+=quantity
    return total


def _planned_slot_reservations(planned,current,item,now,step,orders):
    """Other-product excess rows already entitled to this shared queue."""
    if (not isinstance(planned,dict) or not isinstance(current,dict)
            or not isinstance(item,str) or not item):return None
    now=_strict_slot_int(now);step=_strict_slot_int(step)
    if now is None or step is None or step<now:return None
    reserved=0
    for other,rows in planned.items():
        if not isinstance(other,str) or not other or not isinstance(rows,(list,tuple)):return None
        if other==item:continue
        active=False
        for row in rows:
            if not isinstance(row,(list,tuple)) or len(row)!=2:return None
            due=_strict_slot_int(row[0]);quantity=_strict_slot_int(row[1])
            if due is None or quantity is None:return None
            if quantity<=0:continue
            if step==now and due<=now:
                if other not in current:continue
                desired=_strict_slot_int(current[other])
                offered=_inherited_sell_quantity(orders,other)
                if desired is None or offered is None:return None
                if desired>offered:active=True
            elif step!=now and due<=step:
                # Retained overdue/future rows can execute after replenishment.
                active=True
        if active:reserved+=1
    return reserved


def _selected_emission_report(selected_plans,market,now):
    """Bind diagnostics/state to due-now SELL quantities in the final action."""
    if not isinstance(selected_plans,dict) or not isinstance(market,(list,tuple)):return None
    now=_strict_slot_int(now)
    if now is None:return None
    expected={}
    for item,plan in selected_plans.items():
        if not isinstance(item,str) or not item or not isinstance(plan,(list,tuple)):return None
        due_now=0
        for row in plan:
            if not isinstance(row,(list,tuple)) or len(row)!=2:return None
            due=_strict_slot_int(row[0]);quantity=_strict_slot_int(row[1])
            if due is None or quantity is None:return None
            if due==now:due_now+=quantity
        if due_now>0:expected[item]=due_now
    actual={}
    for order in market:
        if not order:continue
        if not isinstance(order,(list,tuple)) or not order:return None
        if order[0]!='SELL':continue
        if len(order)<3 or not isinstance(order[1],str) or not order[1]:return None
        quantity=_strict_slot_int(order[2])
        if quantity is None:return None
        actual[order[1]]=actual.get(order[1],0)+quantity
    missing={item:quantity-actual.get(item,0)
             for item,quantity in expected.items() if actual.get(item,0)<quantity}
    return {'valid':not missing,'expected_due_now':expected,
            'actual_emitted':{item:actual.get(item,0) for item in expected},
            'missing':missing}
'''

OLD_FEASIBLE = """                    if len(orders)>=int(config.get('maxMarketOrdersPerTurn',10)):\n                        offered=sum(max(0,int(o[2])) for o in orders if o and o[0]=='SELL' and o[1]==item)\n                        if q>offered:return False"""
NEW_FEASIBLE = """                    offered=_inherited_sell_quantity(orders,item)\n                    reserved=_planned_slot_reservations(self.planned,current,item,now,t,orders)\n                    if offered is None or reserved is None:return False\n                    if q>offered and len(orders)+reserved>=int(config.get('maxMarketOrdersPerTurn',10)):return False"""

OLD_SELECTION = """        if best:\n            item,plan,info=best\n            selected_plans=plan if item=='__joint__' else {item:plan}\n            for selected_item,selected_plan in selected_plans.items():\n                current[selected_item]=dict(selected_plan).get(now,0)\n                self.planned[selected_item]=[(t,q) for t,q in selected_plan if t>now and q>0]\n            self.diagnostics['chosen']=info\n        out=copy.deepcopy(base)\n        # Preserve every original order index, including withheld SELL positions.\n        # Extra stock is offered only after inherited orders unless moving an\n        # already-selected sale earlier is required to fund a fixed acquisition.\n        out['market']=materialize_sales(out['market'],current,shed,targets,\n                                        int(config.get('maxMarketOrdersPerTurn',10)))\n        out['market'],funding=fund_same_turn_acquisition(\n            out['market'],farm,private,obs['market'],shops,config,now,targets,\n            lambda product:self.rival_supply(obs,product))\n        if funding is not None:self.diagnostics['same_turn_funding']=funding"""

NEW_SELECTION = """        selected_plans={}\n        incumbent_current=dict(current)\n        incumbent_planned=copy.deepcopy(self.planned)\n        if best:\n            item,plan,info=best\n            selected_plans=plan if item=='__joint__' else {item:plan}\n            for selected_item,selected_plan in selected_plans.items():\n                current[selected_item]=dict(selected_plan).get(now,0)\n                self.planned[selected_item]=[(t,q) for t,q in selected_plan if t>now and q>0]\n            self.diagnostics['chosen']=info\n        out=copy.deepcopy(base)\n        # Preserve every original order index, including withheld SELL positions.\n        # Extra stock is offered only after inherited orders unless moving an\n        # already-selected sale earlier is required to fund a fixed acquisition.\n        out['market']=materialize_sales(out['market'],current,shed,targets,\n                                        int(config.get('maxMarketOrdersPerTurn',10)))\n        out['market'],funding=fund_same_turn_acquisition(\n            out['market'],farm,private,obs['market'],shops,config,now,targets,\n            lambda product:self.rival_supply(obs,product))\n        if selected_plans:\n            emission=_selected_emission_report(selected_plans,out['market'],now)\n            if emission is None or not emission['valid']:\n                self.planned=incumbent_planned\n                current=incumbent_current\n                self.diagnostics.pop('chosen',None)\n                out=copy.deepcopy(base)\n                out['market']=materialize_sales(out['market'],current,shed,targets,\n                                                int(config.get('maxMarketOrdersPerTurn',10)))\n                out['market'],funding=fund_same_turn_acquisition(\n                    out['market'],farm,private,obs['market'],shops,config,now,targets,\n                    lambda product:self.rival_supply(obs,product))\n                emission=({'valid':False,'expected_due_now':{},\n                           'actual_emitted':{},'missing':{'malformed':1}}\n                          if emission is None else dict(emission))\n                emission['fallback']=True\n                emission['reason']='chosen-plan-not-emitted'\n            else:\n                emission=dict(emission)\n                emission['fallback']=False\n                emission['reason']='chosen-plan-emitted'\n            self.diagnostics['selection_emission']=emission\n        if funding is not None:self.diagnostics['same_turn_funding']=funding"""


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def patch_source(source: str, *, expected_blob: str | None = EXPECTED_BLOBS["frozen_selected.py"]) -> str:
    raw=source.encode("utf-8")
    if expected_blob is not None and git_blob_sha(raw)!=expected_blob:
        raise ValueError("frozen_selected.py Git blob does not match the reviewed active source")
    for marker in ("def _planned_slot_reservations(","def _selected_emission_report("):
        if marker in source:raise ValueError("active-consumer helper already present")
    if source.count(CLASS_ANCHOR)!=1:raise ValueError("FrozenSelected class anchor is missing or ambiguous")
    if source.count(OLD_FEASIBLE)!=1:raise ValueError("product-local feasibility preimage is missing or ambiguous")
    if source.count(OLD_SELECTION)!=1:raise ValueError("selection/emission preimage is missing or ambiguous")
    patched=source.replace(CLASS_ANCHOR,HELPERS+CLASS_ANCHOR,1)
    patched=patched.replace(OLD_FEASIBLE,NEW_FEASIBLE,1)
    patched=patched.replace(OLD_SELECTION,NEW_SELECTION,1)
    ast.parse(patched)
    if OLD_FEASIBLE in patched or OLD_SELECTION in patched:raise ValueError("predecessor survived materialization")
    if patched.count("def _planned_slot_reservations(")!=1:raise ValueError("reservation helper cardinality is not one")
    if patched.count("def _selected_emission_report(")!=1:raise ValueError("emission helper cardinality is not one")
    if patched.count(NEW_FEASIBLE)!=1 or patched.count(NEW_SELECTION)!=1:
        raise ValueError("successor cardinality is invalid")
    return patched


def verify_lab(lab: Path) -> dict[str,str]:
    if not lab.is_dir():raise ValueError("lab path is not a directory")
    observed={}
    for name,expected in EXPECTED_BLOBS.items():
        path=lab/name
        if not path.is_file() or path.is_symlink():raise ValueError(f"{name} must be a regular file")
        data=path.read_bytes();actual=git_blob_sha(data)
        if actual!=expected:raise ValueError(f"{name} Git blob drift: {actual}")
        observed[name]=actual
    runtime=(lab/"titan_runtime.py").read_text(encoding="utf-8")
    required=("consumer: str = 'frozen'", "from frozen_selected import FrozenSelected",
              "self.consumer = FrozenSelected()")
    for anchor in required:
        if runtime.count(anchor)!=1:raise ValueError(f"runtime active-consumer anchor drift: {anchor}")
    return observed


def _atomic_write(path: Path,data: bytes) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix=path.name+".",dir=path.parent)
    try:
        with os.fdopen(fd,"wb") as handle:
            handle.write(data);handle.flush();os.fsync(handle.fileno())
        os.replace(name,path)
    except Exception:
        try:os.unlink(name)
        except FileNotFoundError:pass
        raise


def materialize(lab: Path, output: Path, receipt_path: Path) -> dict:
    resolved={lab.resolve(),output.resolve(),receipt_path.resolve()}
    if len(resolved)!=3:raise ValueError("lab, output, and receipt paths must be distinct")
    inputs=verify_lab(lab)
    source_path=lab/"frozen_selected.py"
    source_bytes=source_path.read_bytes()
    source=source_bytes.decode("utf-8")
    patched=patch_source(source)
    patched_bytes=patched.encode("utf-8")
    receipt={
        "schema":"titan-v3-cross-product-slot-active-consumer-v1",
        "operation":OPERATION,
        "inputs":inputs,
        "source_sha256":sha256(source_bytes),
        "patched_git_blob":git_blob_sha(patched_bytes),
        "patched_sha256":sha256(patched_bytes),
        "source_bytes":len(source_bytes),
        "patched_bytes":len(patched_bytes),
        "runtime_binding":"Features.consumer=frozen -> root frozen_selected.FrozenSelected",
        "closures":[
            "reserve retained other-product excess rows before product-local admission",
            "reject malformed shared ledgers fail-closed",
            "bind chosen due-now quantities to final emitted action",
            "restore incumbent plans and action when emission custody fails",
        ],
    }
    _atomic_write(output,patched_bytes)
    _atomic_write(receipt_path,(json.dumps(receipt,sort_keys=True,indent=2)+"\n").encode("utf-8"))
    if output.read_bytes()!=patched_bytes:raise ValueError("patched output readback mismatch")
    return receipt


def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--lab",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--receipt",type=Path,required=True)
    args=parser.parse_args()
    materialize(args.lab,args.output,args.receipt)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
