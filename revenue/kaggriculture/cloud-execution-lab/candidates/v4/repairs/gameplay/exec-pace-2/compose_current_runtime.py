# SPDX-License-Identifier: Apache-2.0
"""Source-bound current-ABI composer for the default-OFF EXEC-PACE-2 experiment.

The composer refuses source drift by requiring exact, unique anchors in the
current production sources.  It does not execute legacy V4 materializers and it
does not enable the feature in TITAN-CONFIG.json.
"""
from __future__ import annotations

import json
from pathlib import Path

FEATURE_ANCHOR = "    early_capital: bool = False\n"
FEATURE_INSERT = FEATURE_ANCHOR + "    exec_pace: bool = False\n"

CONSUMER_ANCHOR = "            self.consumer = FrozenSelected()\n"
CONSUMER_INSERT = CONSUMER_ANCHOR + (
    "            if f.exec_pace is True:\n"
    "                pace = load('_titan_exec_pace_runtime', HERE/'exec_pace_runtime.py')\n"
    "                exec_pace_state = getattr(self, '_exec_pace_state', None)\n"
    "                if exec_pace_state is None:\n"
    "                    exec_pace_state = pace.PriceTrendState()\n"
    "                    self._exec_pace_state = exec_pace_state\n"
    "                self.consumer.exec_pace_state = exec_pace_state\n"
    "                self.consumer.exec_pace_apply = pace.apply_candidate\n"
)

TRANSFORM_ANCHOR = (
    "        self.observe(obs)\n"
    "        farm,private=post_units(obs,base,config)\n"
)
TRANSFORM_INSERT = (
    "        self.observe(obs)\n"
    "        exec_pace_state=getattr(self,'exec_pace_state',None)\n"
    "        if exec_pace_state is not None:exec_pace_state.note_prices(obs)\n"
    "        farm,private=post_units(obs,base,config)\n"
)

PLAN_ANCHOR = (
    "            info['baseline_horizon_end']=horizon['baseline_end'];info['horizon_end']=item_end\n"
    "            self.diagnostics['evaluations'].append(info)\n"
    "            eligible,rank=seller_choice_rank(info)\n"
)
PLAN_INSERT = (
    "            info['baseline_horizon_end']=horizon['baseline_end'];info['horizon_end']=item_end\n"
    "            exec_pace_apply=getattr(self,'exec_pace_apply',None)\n"
    "            if exec_pace_apply is not None:\n"
    "                plan,info=exec_pace_apply(exec_pace_state,item,reference,plan,info)\n"
    "            self.diagnostics['evaluations'].append(info)\n"
    "            eligible,rank=seller_choice_rank(info)\n"
)


def _replace_once(source, anchor, replacement, label):
    count = source.count(anchor)
    if count != 1:
        raise ValueError(f"{label} source drift: expected one anchor, found {count}")
    return source.replace(anchor, replacement, 1)


def compose_sources(titan_runtime_source, frozen_selected_source):
    titan = _replace_once(titan_runtime_source, FEATURE_ANCHOR, FEATURE_INSERT, "Features")
    titan = _replace_once(titan, CONSUMER_ANCHOR, CONSUMER_INSERT, "FrozenSelected construction")
    frozen = _replace_once(frozen_selected_source, TRANSFORM_ANCHOR, TRANSFORM_INSERT,
                           "FrozenSelected transform observer")
    frozen = _replace_once(frozen, PLAN_ANCHOR, PLAN_INSERT, "FrozenSelected plan gate")
    compile(titan, "titan_runtime.py", "exec")
    compile(frozen, "frozen_selected.py", "exec")
    return titan, frozen


def compose_config(config_source):
    config = json.loads(config_source)
    if "exec_pace" in config:
        raise ValueError("exec_pace already present; refuse ambiguous source")
    config["exec_pace"] = False
    return json.dumps(config, indent=2, sort_keys=False) + "\n"


def materialize(source_root, target_root, runtime_module_source):
    source_root = Path(source_root)
    target_root = Path(target_root)
    if target_root.exists():
        raise FileExistsError(target_root)
    titan_src = (source_root / "titan_runtime.py").read_text()
    frozen_src = (source_root / "frozen_selected.py").read_text()
    config_src = (source_root / "TITAN-CONFIG.json").read_text()
    titan, frozen = compose_sources(titan_src, frozen_src)
    config = compose_config(config_src)
    target_root.mkdir(parents=True)
    (target_root / "titan_runtime.py").write_text(titan)
    (target_root / "frozen_selected.py").write_text(frozen)
    (target_root / "TITAN-CONFIG.json").write_text(config)
    (target_root / "exec_pace_runtime.py").write_text(runtime_module_source)
    return {
        "titan_runtime.py": len(titan),
        "frozen_selected.py": len(frozen),
        "TITAN-CONFIG.json": len(config),
        "exec_pace_runtime.py": len(runtime_module_source),
    }
